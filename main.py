# Used to manage startup & shutdown lifecycle (async version)
from contextlib import asynccontextmanager

# For modern dependency injection typing
from typing import Annotated

# FastAPI core imports
from fastapi import Depends, FastAPI, HTTPException, Request, status

# Built-in FastAPI exception handlers (reused for API responses)
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)

# Validation error class
from fastapi.exceptions import RequestValidationError

# Serve static files (CSS, JS, images)
from fastapi.staticfiles import StaticFiles

# Render HTML templates
from fastapi.templating import Jinja2Templates

# SQLAlchemy query builder
from sqlalchemy import select

# Async DB session
from sqlalchemy.ext.asyncio import AsyncSession

# Used to eagerly load relationships (avoid extra queries)
from sqlalchemy.orm import selectinload

# Starlette HTTP exception (base of FastAPI errors)
from starlette.exceptions import HTTPException as StarletteHTTPException

# Import your models
import models

# Import DB setup
from database import Base, engine, get_db

# Import schemas (validation)
from schemas import (
    PostCreate,
    PostResponse,
    PostUpdate,
    UserCreate,
    UserResponse,
    UserUpdate,
)


# =========================
# 🔄 APP LIFECYCLE (STARTUP/SHUTDOWN)
# =========================

@asynccontextmanager
async def lifespan(_app: FastAPI):
    
    # 🔹 Startup: create DB tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield  # App runs here

    # 🔹 Shutdown: close DB engine
    await engine.dispose()


# Create FastAPI app with lifecycle
app = FastAPI(lifespan=lifespan)


# =========================
# 📁 STATIC + TEMPLATES
# =========================

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")

# Template engine
templates = Jinja2Templates(directory="templates")


# =========================
# 🏠 UI ROUTES (HTML)
# =========================

@app.get("/", include_in_schema=False)
@app.get("/posts", include_in_schema=False)
async def home(request: Request, db: Annotated[AsyncSession, Depends(get_db)]):

    # Fetch posts with author (optimized query)
    result = await db.execute(
        select(models.Post).options(selectinload(models.Post.author)),
    )
    posts = result.scalars().all()

    # Render HTML
    return templates.TemplateResponse(
        request,
        "home.html",
        {"posts": posts, "title": "Home"},
    )


# =========================
# 📝 SINGLE POST PAGE
# =========================

@app.get("/posts/{post_id}", include_in_schema=False)
async def post_page(request: Request, post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):

    # Fetch one post with author
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id),
    )
    post = result.scalars().first()

    if post:
        return templates.TemplateResponse(
            request,
            "post.html",
            {"post": post, "title": post.title[:50]},
        )

    raise HTTPException(404, "Post not found")


# =========================
# 👤 CREATE USER
# =========================

@app.post("/api/users", response_model=UserResponse, status_code=201)
async def create_user(user: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):

    # Check username exists
    result = await db.execute(select(models.User).where(models.User.username == user.username))
    if result.scalars().first():
        raise HTTPException(400, "Username already exists")

    # Check email exists
    result = await db.execute(select(models.User).where(models.User.email == user.email))
    if result.scalars().first():
        raise HTTPException(400, "Email already registered")

    # Create user
    new_user = models.User(username=user.username, email=user.email)

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


# =========================
# 📝 CREATE POST
# =========================

@app.post("/api/posts", response_model=PostResponse, status_code=201)
async def create_post(post: PostCreate, db: Annotated[AsyncSession, Depends(get_db)]):

    # Check user exists
    result = await db.execute(select(models.User).where(models.User.id == post.user_id))
    if not result.scalars().first():
        raise HTTPException(404, "User not found")

    # Create post
    new_post = models.Post(
        title=post.title,
        content=post.content,
        user_id=post.user_id,
    )

    db.add(new_post)
    await db.commit()

    # Load author relationship
    await db.refresh(new_post, attribute_names=["author"])

    return new_post


# =========================
# 🔄 UPDATE POST (PATCH)
# =========================

@app.patch("/api/posts/{post_id}", response_model=PostResponse)
async def update_post_partial(post_id: int, post_data: PostUpdate, db: Annotated[AsyncSession, Depends(get_db)]):

    result = await db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()

    if not post:
        raise HTTPException(404, "Post not found")

    # Update only provided fields
    update_data = post_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(post, field, value)

    await db.commit()
    await db.refresh(post, attribute_names=["author"])

    return post


# =========================
# ❌ DELETE POST
# =========================

@app.delete("/api/posts/{post_id}", status_code=204)
async def delete_post(post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):

    result = await db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()

    if not post:
        raise HTTPException(404, "Post not found")

    await db.delete(post)
    await db.commit()


# =========================
# ⚠️ ERROR HANDLING
# =========================

@app.exception_handler(StarletteHTTPException)
async def general_http_exception_handler(request: Request, exception: StarletteHTTPException):

    # API → return default JSON handler
    if request.url.path.startswith("/api"):
        return await http_exception_handler(request, exception)

    # UI → return HTML page
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": exception.status_code,
            "message": exception.detail or "Something went wrong",
        },
        status_code=exception.status_code,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exception: RequestValidationError):

    # API → return default validation handler
    if request.url.path.startswith("/api"):
        return await request_validation_exception_handler(request, exception)

    # UI → custom HTML error page
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": 422,
            "message": "Invalid request",
        },
        status_code=422,
    )