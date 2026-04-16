# Used for modern dependency injection typing
from typing import Annotated

# FastAPI core imports
from fastapi import Depends, FastAPI, HTTPException, Request, status

# Handles validation errors (wrong input types etc.)
from fastapi.exceptions import RequestValidationError

# Used to return JSON responses manually
from fastapi.responses import JSONResponse

# Serve static files like CSS, JS, images
from fastapi.staticfiles import StaticFiles

# Render HTML templates
from fastapi.templating import Jinja2Templates

# SQLAlchemy query builder
from sqlalchemy import select

# Database session
from sqlalchemy.orm import Session

# Catch HTTP errors from Starlette
from starlette.exceptions import HTTPException as StarletteHTTPException

# Import DB models
import models

# Import DB setup
from database import Base, engine, get_db

# Import schemas (input/output validation)
from schemas import (
    PostCreate,
    PostResponse,
    PostUpdate,
    UserCreate,
    UserResponse,
    UserUpdate,
)

# Create DB tables automatically
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI()

# Serve static & media files
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")

# Setup template engine
templates = Jinja2Templates(directory="templates")


# =========================
# 🏠 UI ROUTES (HTML)
# =========================

# Home page → shows all posts
@app.get("/", include_in_schema=False)
@app.get("/posts", include_in_schema=False)
def home(request: Request, db: Annotated[Session, Depends(get_db)]):

    # Fetch all posts from DB
    result = db.execute(select(models.Post))
    posts = result.scalars().all()

    # Render HTML page
    return templates.TemplateResponse(
        request,
        "home.html",
        {"posts": posts, "title": "Home"},
    )


# Single post page
@app.get("/posts/{post_id}", include_in_schema=False)
def post_page(request: Request, post_id: int, db: Annotated[Session, Depends(get_db)]):

    # Fetch post by ID
    result = db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()

    if post:
        title = post.title[:50]

        return templates.TemplateResponse(
            request,
            "post.html",
            {"post": post, "title": title},
        )

    # If not found → 404
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")


# User posts page (HTML)
@app.get("/users/{user_id}/posts", include_in_schema=False)
def user_posts_page(request: Request, user_id: int, db: Annotated[Session, Depends(get_db)]):

    # Check if user exists
    result = db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get posts of that user
    result = db.execute(select(models.Post).where(models.Post.user_id == user_id))
    posts = result.scalars().all()

    return templates.TemplateResponse(
        request,
        "user_posts.html",
        {"posts": posts, "user": user, "title": f"{user.username}'s Posts"},
    )


# =========================
# 👤 USER APIs (CRUD)
# =========================

# Create user
@app.post("/api/users", response_model=UserResponse, status_code=201)
def create_user(user: UserCreate, db: Annotated[Session, Depends(get_db)]):

    # Check username exists
    result = db.execute(select(models.User).where(models.User.username == user.username))
    if result.scalars().first():
        raise HTTPException(400, "Username already exists")

    # Check email exists
    result = db.execute(select(models.User).where(models.User.email == user.email))
    if result.scalars().first():
        raise HTTPException(400, "Email already registered")

    # Create new user
    new_user = models.User(username=user.username, email=user.email)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


# Get user
@app.get("/api/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Annotated[Session, Depends(get_db)]):

    result = db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()

    if user:
        return user

    raise HTTPException(404, "User not found")


# Update user (partial update)
@app.patch("/api/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user_update: UserUpdate, db: Annotated[Session, Depends(get_db)]):

    result = db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(404, "User not found")

    # Update only provided fields
    if user_update.username is not None:
        user.username = user_update.username

    if user_update.email is not None:
        user.email = user_update.email

    if user_update.image_file is not None:
        user.image_file = user_update.image_file

    db.commit()
    db.refresh(user)

    return user


# Delete user
@app.delete("/api/users/{user_id}", status_code=204)
def delete_user(user_id: int, db: Annotated[Session, Depends(get_db)]):

    result = db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(404, "User not found")

    db.delete(user)
    db.commit()


# =========================
# 📝 POST APIs (CRUD)
# =========================

# Get all posts
@app.get("/api/posts", response_model=list[PostResponse])
def get_posts(db: Annotated[Session, Depends(get_db)]):

    result = db.execute(select(models.Post))
    return result.scalars().all()


# Create post
@app.post("/api/posts", response_model=PostResponse, status_code=201)
def create_post(post: PostCreate, db: Annotated[Session, Depends(get_db)]):

    # Check user exists
    result = db.execute(select(models.User).where(models.User.id == post.user_id))
    if not result.scalars().first():
        raise HTTPException(404, "User not found")

    # Create post
    new_post = models.Post(
        title=post.title,
        content=post.content,
        user_id=post.user_id,
    )

    db.add(new_post)
    db.commit()
    db.refresh(new_post)

    return new_post


# Get single post
@app.get("/api/posts/{post_id}", response_model=PostResponse)
def get_post(post_id: int, db: Annotated[Session, Depends(get_db)]):

    result = db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()

    if post:
        return post

    raise HTTPException(404, "Post not found")


# Full update (PUT)
@app.put("/api/posts/{post_id}", response_model=PostResponse)
def update_post_full(post_id: int, post_data: PostCreate, db: Annotated[Session, Depends(get_db)]):

    result = db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()

    if not post:
        raise HTTPException(404, "Post not found")

    # Replace all fields
    post.title = post_data.title
    post.content = post_data.content
    post.user_id = post_data.user_id

    db.commit()
    db.refresh(post)

    return post


# Partial update (PATCH)
@app.patch("/api/posts/{post_id}", response_model=PostResponse)
def update_post_partial(post_id: int, post_data: PostUpdate, db: Annotated[Session, Depends(get_db)]):

    result = db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()

    if not post:
        raise HTTPException(404, "Post not found")

    # Update only provided fields
    update_data = post_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(post, field, value)

    db.commit()
    db.refresh(post)

    return post


# Delete post
@app.delete("/api/posts/{post_id}", status_code=204)
def delete_post(post_id: int, db: Annotated[Session, Depends(get_db)]):

    result = db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()

    if not post:
        raise HTTPException(404, "Post not found")

    db.delete(post)
    db.commit()


# =========================
# ⚠️ ERROR HANDLING
# =========================

# Handle HTTP errors
@app.exception_handler(StarletteHTTPException)
def general_http_exception_handler(request: Request, exception: StarletteHTTPException):

    message = exception.detail or "Something went wrong"

    # API → JSON response
    if request.url.path.startswith("/api"):
        return JSONResponse(status_code=exception.status_code, content={"detail": message})

    # UI → HTML page
    return templates.TemplateResponse(
        request,
        "error.html",
        {"status_code": exception.status_code, "message": message},
        status_code=exception.status_code,
    )


# Handle validation errors
@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exception: RequestValidationError):

    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=422,
            content={"detail": exception.errors()},
        )

    return templates.TemplateResponse(
        request,
        "error.html",
        {"status_code": 422, "message": "Invalid input"},
        status_code=422,
    )