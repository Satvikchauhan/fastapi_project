# Used to manage startup and shutdown lifecycle events
from contextlib import asynccontextmanager

# Used for modern type hints with dependency injection
from typing import Annotated


# FastAPI imports:
# Depends -> inject dependencies like DB session
# FastAPI -> create app instance
# HTTPException -> raise errors
# Request -> access request object
# status -> HTTP status codes
from fastapi import Depends, FastAPI, HTTPException, Request, status


# Built-in FastAPI exception handlers for API JSON responses
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)

# Validation error class (422 errors)
from fastapi.exceptions import RequestValidationError

# Serve CSS / JS / images
from fastapi.staticfiles import StaticFiles

# Render HTML templates
from fastapi.templating import Jinja2Templates


# SQLAlchemy query builder
from sqlalchemy import select

# Async database session
from sqlalchemy.ext.asyncio import AsyncSession

# Efficient relationship loading
from sqlalchemy.orm import selectinload


# Base HTTP exception from Starlette
from starlette.exceptions import HTTPException as StarletteHTTPException


# Import ORM models
import models

# Import database setup
from database import Base, engine, get_db

# Import routers
from routers import posts, users


# ==================================================
# 🔄 APP STARTUP / SHUTDOWN
# ==================================================
@asynccontextmanager
async def lifespan(_app: FastAPI):

    # -------------------------
    # STARTUP
    # -------------------------
    # Create DB tables if missing
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # App runs here
    yield

    # -------------------------
    # SHUTDOWN
    # -------------------------
    # Close DB engine
    await engine.dispose()


# Create FastAPI app
app = FastAPI(lifespan=lifespan)


# ==================================================
# 📁 STATIC FILES
# ==================================================

# Serve CSS, JS, images
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve uploaded media files
app.mount("/media", StaticFiles(directory="media"), name="media")


# ==================================================
# 🎨 TEMPLATE ENGINE
# ==================================================

# Templates folder
templates = Jinja2Templates(directory="templates")


# ==================================================
# 🧩 INCLUDE ROUTERS
# ==================================================

# Include user API routes
# /api/users
app.include_router(
    users.router,
    prefix="/api/users",
    tags=["users"]
)

# Include post API routes
# /api/posts
app.include_router(
    posts.router,
    prefix="/api/posts",
    tags=["posts"]
)


# ==================================================
# 🏠 HOME PAGE
# Routes:
# /
# /posts
# ==================================================
@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts")
async def home(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):

    # Fetch all posts + author data
    # Latest posts first
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .order_by(models.Post.date_posted.desc()),
    )

    posts = result.scalars().all()

    # Render home page
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

    # Fetch single post by ID
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id),
    )

    post = result.scalars().first()

    if post:

        # Use first 50 chars as title
        title = post.title[:50]

        # Render post page
        return templates.TemplateResponse(
            request,
            "post.html",
            {"post": post, "title": title},
        )

    # If post not found
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Post not found",
    )


# ==================================================
# 👤 USER POSTS PAGE
# Route: /users/{user_id}/posts
# ==================================================
@app.get(
    "/users/{user_id}/posts",
    include_in_schema=False,
    name="user_posts",
)
async def user_posts_page(
    request: Request,
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):

    # Check user exists
    result = await db.execute(
        select(models.User).where(
            models.User.id == user_id
        )
    )

    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Fetch all posts by that user
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.user_id == user_id)
        .order_by(models.Post.date_posted.desc()),
    )

    posts = result.scalars().all()

    # Render user posts page
    return templates.TemplateResponse(
        request,
        "user_posts.html",
        {
            "posts": posts,
            "user": user,
            "title": f"{user.username}'s Posts",
        },
    )


# ==================================================
# 🔐 LOGIN PAGE
# Route: /login
# ==================================================
@app.get("/login", include_in_schema=False)
async def login_page(request: Request):

    # Render login page
    return templates.TemplateResponse(
        request,
        "login.html",
        {"title": "Login"},
    )


# ==================================================
# 📝 REGISTER PAGE
# Route: /register
# ==================================================
@app.get("/register", include_in_schema=False)
async def register_page(request: Request):

    # Render register page
    return templates.TemplateResponse(
        request,
        "register.html",
        {"title": "Register"},
    )


# ==================================================
# ⚠️ GENERAL HTTP ERROR HANDLER
# Handles 404, 400 etc.
# ==================================================
@app.exception_handler(StarletteHTTPException)
async def general_http_exception_handler(
    request: Request,
    exception: StarletteHTTPException,
):

    # If API route, return JSON error
    if request.url.path.startswith("/api"):
        return await http_exception_handler(
            request,
            exception,
        )

    # UI route -> show HTML error page
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
# Handles wrong inputs / missing fields
# ==================================================
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exception: RequestValidationError,
):

    # API request -> JSON validation error
    if request.url.path.startswith("/api"):
        return await request_validation_exception_handler(
            request,
            exception,
        )

    # UI request -> HTML error page
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