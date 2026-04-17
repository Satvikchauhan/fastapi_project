# Used to manage app startup and shutdown events
from contextlib import asynccontextmanager

# Used for modern type hints with dependency injection
from typing import Annotated


# FastAPI imports:
# Depends -> inject dependencies like database session
# FastAPI -> main application object
# HTTPException -> raise custom errors
# Request -> access request data
# status -> HTTP status codes
from fastapi import Depends, FastAPI, HTTPException, Request, status


# Built-in FastAPI handlers for default API errors
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)

# Validation error class (422 errors)
from fastapi.exceptions import RequestValidationError

# Serve CSS, JS, images
from fastapi.staticfiles import StaticFiles

# Render HTML templates using Jinja2
from fastapi.templating import Jinja2Templates


# SQLAlchemy query builder
from sqlalchemy import select

# Async DB session
from sqlalchemy.ext.asyncio import AsyncSession

# Efficiently preload related tables (Post + author)
from sqlalchemy.orm import selectinload


# Base HTTP exception from Starlette
from starlette.exceptions import HTTPException as StarletteHTTPException


# Import database models
import models

# Import DB setup
# Base -> model base class
# engine -> DB connection engine
# get_db -> DB dependency function
from database import Base, engine, get_db


# Import routers
# posts.py routes
# users.py routes
from routers import posts, users


# ==================================================
# 🔄 APPLICATION LIFECYCLE
# Runs on startup and shutdown
# ==================================================
@asynccontextmanager
async def lifespan(_app: FastAPI):

    # -----------------------------
    # STARTUP EVENT
    # -----------------------------
    # Create database tables if they do not exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # App runs after this line
    yield

    # -----------------------------
    # SHUTDOWN EVENT
    # -----------------------------
    # Close database engine cleanly
    await engine.dispose()


# Create FastAPI app and attach lifespan manager
app = FastAPI(lifespan=lifespan)


# ==================================================
# 📁 STATIC FILES
# ==================================================

# Serve CSS / JS / images
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve uploaded media files
app.mount("/media", StaticFiles(directory="media"), name="media")


# ==================================================
# 🎨 TEMPLATE ENGINE
# ==================================================

# Jinja2 HTML templates folder
templates = Jinja2Templates(directory="templates")


# ==================================================
# 🧩 INCLUDE ROUTERS
# ==================================================

# User APIs
# Example:
# POST /api/users
# GET /api/users/1
app.include_router(users.router, prefix="/api/users", tags=["users"])

# Post APIs
# Example:
# GET /api/posts
# POST /api/posts
app.include_router(posts.router, prefix="/api/posts", tags=["posts"])


# ==================================================
# 🏠 HOME PAGE
# Route: /   and   /posts
# ==================================================
@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts")
async def home(request: Request, db: Annotated[AsyncSession, Depends(get_db)]):

    # Fetch all posts + author data
    result = await db.execute(
        select(models.Post).options(selectinload(models.Post.author)),
    )

    posts = result.scalars().all()

    # Render home.html
    return templates.TemplateResponse(
        request,
        "home.html",
        {"posts": posts, "title": "Home"},
    )


# ==================================================
# 📝 SINGLE POST PAGE
# Route: /posts/{post_id}
# ==================================================
@app.get("/posts/{post_id}", include_in_schema=False)
async def post_page(
    request: Request,
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):

    # Fetch single post by ID + author
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id),
    )

    post = result.scalars().first()

    if post:
        title = post.title[:50]

        # Render post.html
        return templates.TemplateResponse(
            request,
            "post.html",
            {"post": post, "title": title},
        )

    # If not found
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Post not found"
    )


# ==================================================
# 👤 USER POSTS PAGE
# Route: /users/{user_id}/posts
# ==================================================
@app.get("/users/{user_id}/posts", include_in_schema=False, name="user_posts")
async def user_posts_page(
    request: Request,
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):

    # Check if user exists
    result = await db.execute(
        select(models.User).where(models.User.id == user_id)
    )

    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Fetch all posts of that user
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.user_id == user_id),
    )

    posts = result.scalars().all()

    # Render user_posts.html
    return templates.TemplateResponse(
        request,
        "user_posts.html",
        {
            "posts": posts,
            "user": user,
            "title": f"{user.username}'s Posts"
        },
    )


# ==================================================
# ⚠️ GENERAL HTTP ERROR HANDLER
# ==================================================
@app.exception_handler(StarletteHTTPException)
async def general_http_exception_handler(
    request: Request,
    exception: StarletteHTTPException,
):

    # If API request (/api/...) return JSON error
    if request.url.path.startswith("/api"):
        return await http_exception_handler(request, exception)

    # Otherwise show HTML error page
    message = (
        exception.detail
        if exception.detail
        else "An error occurred. Please check your request and try again."
    )

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


# ==================================================
# ⚠️ VALIDATION ERROR HANDLER
# Handles wrong input types / missing fields
# ==================================================
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exception: RequestValidationError,
):

    # API requests → return default JSON validation error
    if request.url.path.startswith("/api"):
        return await request_validation_exception_handler(
            request,
            exception,
        )

    # UI requests → show HTML error page
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