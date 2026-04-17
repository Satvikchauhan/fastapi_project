# Used for modern type hints with FastAPI dependencies
from typing import Annotated

# FastAPI imports:
# APIRouter -> group all user routes in one file
# Depends -> inject database dependency
# HTTPException -> raise API errors
# status -> HTTP status codes (201, 404, etc.)
from fastapi import APIRouter, Depends, HTTPException, status

# SQLAlchemy select query builder
from sqlalchemy import select

# Async database session
from sqlalchemy.ext.asyncio import AsyncSession

# Used to preload related tables efficiently
from sqlalchemy.orm import selectinload

# Import database models (User, Post)
import models

# Import database dependency function
from database import get_db

# Import Pydantic schemas
# UserCreate -> input for creating user
# UserResponse -> output schema
# UserUpdate -> partial update schema
# PostResponse -> nested response for posts
from schemas import PostResponse, UserCreate, UserResponse, UserUpdate


# Create router object for user routes
# This router will be included in main.py
router = APIRouter()


# ==================================================
# 👤 CREATE USER
# Route: POST /api/users
# ==================================================
@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(user: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):

    # Check if username already exists
    result = await db.execute(
        select(models.User).where(models.User.username == user.username),
    )

    existing_user = result.scalars().first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    # Check if email already exists
    result = await db.execute(
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

    # Add to DB session
    db.add(new_user)

    # Save to database
    await db.commit()

    # Refresh object to get generated values like id
    await db.refresh(new_user)

    return new_user


# ==================================================
# 👤 GET SINGLE USER
# Route: GET /api/users/{user_id}
# ==================================================
@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):

    # Find user by ID
    result = await db.execute(
        select(models.User).where(models.User.id == user_id)
    )

    user = result.scalars().first()

    if user:
        return user

    # If user not found
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )


# ==================================================
# 👤 GET POSTS OF A USER
# Route: GET /api/users/{user_id}/posts
# ==================================================
@router.get("/{user_id}/posts", response_model=list[PostResponse])
async def get_user_posts(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):

    # First verify user exists
    result = await db.execute(
        select(models.User).where(models.User.id == user_id)
    )

    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Fetch all posts of that user + author relationship
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.user_id == user_id),
    )

    posts = result.scalars().all()

    return posts


# ==================================================
# 👤 UPDATE USER PARTIALLY
# Route: PATCH /api/users/{user_id}
# ==================================================
@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
):

    # Find user by ID
    result = await db.execute(
        select(models.User).where(models.User.id == user_id)
    )

    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # If username is changing, check duplicate username
    if user_update.username is not None and user_update.username != user.username:

        result = await db.execute(
            select(models.User).where(
                models.User.username == user_update.username
            ),
        )

        existing_user = result.scalars().first()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists",
            )

    # If email is changing, check duplicate email
    if user_update.email is not None and user_update.email != user.email:

        result = await db.execute(
            select(models.User).where(
                models.User.email == user_update.email
            ),
        )

        existing_email = result.scalars().first()

        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

    # Update only fields that were provided
    if user_update.username is not None:
        user.username = user_update.username

    if user_update.email is not None:
        user.email = user_update.email

    if user_update.image_file is not None:
        user.image_file = user_update.image_file

    # Save changes
    await db.commit()

    # Refresh updated object
    await db.refresh(user)

    return user


# ==================================================
# 👤 DELETE USER
# Route: DELETE /api/users/{user_id}
# ==================================================
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):

    # Find user by ID
    result = await db.execute(
        select(models.User).where(models.User.id == user_id)
    )

    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Delete user from DB
    await db.delete(user)

    # Save deletion
    await db.commit()