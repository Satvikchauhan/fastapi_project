# Used to add type hints like Annotated (modern FastAPI dependency style)
from typing import Annotated

# FastAPI core imports
from fastapi import Depends, FastAPI, HTTPException, Request, status

# Handles validation errors (e.g. wrong data types)
from fastapi.exceptions import RequestValidationError

# Used to return JSON responses manually
from fastapi.responses import JSONResponse

# For serving static files (CSS, JS, images)
from fastapi.staticfiles import StaticFiles

# For rendering HTML templates (Jinja2)
from fastapi.templating import Jinja2Templates

# SQLAlchemy query builder
from sqlalchemy import select

# SQLAlchemy session (DB connection instance)
from sqlalchemy.orm import Session

# To catch HTTP errors from Starlette (FastAPI is built on Starlette)
from starlette.exceptions import HTTPException as StarletteHTTPException

# Import your database models (User, Post)
import models

# Import DB setup (engine, Base, dependency function)
from database import Base, engine, get_db

# Import Pydantic schemas (input/output validation)
from schemas import PostCreate, PostResponse, UserCreate, UserResponse


# 🔹 Create database tables automatically
Base.metadata.create_all(bind=engine)


# 🔹 Create FastAPI app
app = FastAPI()


# 🔹 Mount static folders
app.mount("/static", StaticFiles(directory="static"), name="static")  # CSS, JS
app.mount("/media", StaticFiles(directory="media"), name="media")    # Uploaded images


# 🔹 Setup template engine
templates = Jinja2Templates(directory="templates")


# =========================
# 🏠 HTML ROUTES (UI)
# =========================

# Home page (list all posts)
@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts")
def home(request: Request, db: Annotated[Session, Depends(get_db)]):
    
    # Query all posts from database
    result = db.execute(select(models.Post))
    posts = result.scalars().all()

    # Render HTML template
    return templates.TemplateResponse(
        request,
        "home.html",
        {"posts": posts, "title": "Home"},
    )


# Single post page
@app.get("/posts/{post_id}", include_in_schema=False)
def post_page(request: Request, post_id: int, db: Annotated[Session, Depends(get_db)]):

    # Query post by ID
    result = db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()

    if post:
        title = post.title[:50]

        # Render post page
        return templates.TemplateResponse(
            request,
            "post.html",
            {"post": post, "title": title},
        )

    # If not found → raise error
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")


# User-specific posts page
@app.get("/users/{user_id}/posts", include_in_schema=False, name="user_posts")
def user_posts_page(
    request: Request,
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    # Check if user exists
    result = db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Get posts of that user
    result = db.execute(select(models.Post).where(models.Post.user_id == user_id))
    posts = result.scalars().all()

    return templates.TemplateResponse(
        request,
        "user_posts.html",
        {"posts": posts, "user": user, "title": f"{user.username}'s Posts"},
    )


# =========================
# 👤 USER APIs
# =========================

# Create new user
@app.post(
    "/api/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user(user: UserCreate, db: Annotated[Session, Depends(get_db)]):

    # Check if username already exists
    result = db.execute(
        select(models.User).where(models.User.username == user.username),
    )
    existing_user = result.scalars().first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    # Check if email already exists
    result = db.execute(
        select(models.User).where(models.User.email == user.email),
    )
    existing_email = result.scalars().first()

    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create new user object
    new_user = models.User(
        username=user.username,
        email=user.email,
    )

    # Save to DB
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


# Get single user
@app.get("/api/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Annotated[Session, Depends(get_db)]):

    result = db.execute(
        select(models.User).where(models.User.id == user_id),
    )
    user = result.scalars().first()

    if user:
        return user

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")


# Get posts of a user (API)
@app.get("/api/users/{user_id}/posts", response_model=list[PostResponse])
def get_user_posts(user_id: int, db: Annotated[Session, Depends(get_db)]):

    # Check user exists
    result = db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Fetch posts
    result = db.execute(select(models.Post).where(models.Post.user_id == user_id))
    posts = result.scalars().all()

    return posts


# =========================
# 📝 POST APIs
# =========================

# Get all posts
@app.get("/api/posts", response_model=list[PostResponse])
def get_posts(db: Annotated[Session, Depends(get_db)]):

    result = db.execute(select(models.Post))
    posts = result.scalars().all()

    return posts


# Create new post
@app.post(
    "/api/posts",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_post(post: PostCreate, db: Annotated[Session, Depends(get_db)]):

    # Check user exists
    result = db.execute(select(models.User).where(models.User.id == post.user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Create new post object
    new_post = models.Post(
        title=post.title,
        content=post.content,
        user_id=post.user_id,
    )

    # Save to DB
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

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")


# =========================
# ⚠️ EXCEPTION HANDLING
# =========================

# Handle general HTTP errors
@app.exception_handler(StarletteHTTPException)
def general_http_exception_handler(request: Request, exception: StarletteHTTPException):

    message = (
        exception.detail
        if exception.detail
        else "An error occurred. Please check your request and try again."
    )

    # API → return JSON
    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=exception.status_code,
            content={"detail": message},
        )

    # UI → return HTML error page
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": exception.status_code,
            "title": exception.status_code,
            "message": message,
        },
        status_code=exception.status_code,
    )


# Handle validation errors (422)
@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exception: RequestValidationError):

    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": exception.errors()},
        )

    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "title": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "message": "Invalid request. Please check your input and try again.",
        },
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )