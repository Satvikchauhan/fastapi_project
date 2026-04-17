# Used for modern type hints with FastAPI dependencies
from typing import Annotated

# FastAPI imports:
# APIRouter -> used to group related routes (posts routes)
# Depends -> dependency injection (get_db)
# HTTPException -> raise API errors
# status -> HTTP status codes like 201, 404
from fastapi import APIRouter, Depends, HTTPException, status

# SQLAlchemy select query builder
from sqlalchemy import select

# Async database session
from sqlalchemy.ext.asyncio import AsyncSession

# Loads related data efficiently (Post + author)
from sqlalchemy.orm import selectinload

# Import database models (User, Post)
import models

# Import DB dependency function
from database import get_db

# Import request/response schemas
from schemas import PostCreate, PostResponse, PostUpdate


# Create router object
# This file will later be included in main.py
router = APIRouter()


# ==================================================
# 📝 GET ALL POSTS
# Route: GET /api/posts
# ==================================================
@router.get("", response_model=list[PostResponse])
async def get_posts(db: Annotated[AsyncSession, Depends(get_db)]):

    # Fetch all posts + related author data
    result = await db.execute(
        select(models.Post).options(selectinload(models.Post.author)),
    )

    # Convert result into Python list
    posts = result.scalars().all()

    return posts


# ==================================================
# 📝 CREATE NEW POST
# Route: POST /api/posts
# ==================================================
@router.post(
    "",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_post(post: PostCreate, db: Annotated[AsyncSession, Depends(get_db)]):

    # Check if user exists before creating post
    result = await db.execute(
        select(models.User).where(models.User.id == post.user_id),
    )

    user = result.scalars().first()

    # If user not found → error
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Create new Post object
    new_post = models.Post(
        title=post.title,
        content=post.content,
        user_id=post.user_id,
    )

    # Add to DB session
    db.add(new_post)

    # Save changes
    await db.commit()

    # Refresh object and load author relationship
    await db.refresh(new_post, attribute_names=["author"])

    return new_post


# ==================================================
# 📝 GET SINGLE POST
# Route: GET /api/posts/{post_id}
# ==================================================
@router.get("/{post_id}", response_model=PostResponse)
async def get_post(post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):

    # Fetch one post by ID + author
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id),
    )

    post = result.scalars().first()

    if post:
        return post

    # If not found
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Post not found"
    )


# ==================================================
# 📝 FULL UPDATE POST
# Route: PUT /api/posts/{post_id}
# PUT replaces all fields
# ==================================================
@router.put("/{post_id}", response_model=PostResponse)
async def update_post_full(
    post_id: int,
    post_data: PostCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):

    # Find existing post
    result = await db.execute(
        select(models.Post).where(models.Post.id == post_id)
    )

    post = result.scalars().first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    # If user_id changed, validate new user exists
    if post_data.user_id != post.user_id:

        result = await db.execute(
            select(models.User).where(models.User.id == post_data.user_id),
        )

        user = result.scalars().first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

    # Replace all values
    post.title = post_data.title
    post.content = post_data.content
    post.user_id = post_data.user_id

    # Save changes
    await db.commit()

    # Reload author relation
    await db.refresh(post, attribute_names=["author"])

    return post


# ==================================================
# 📝 PARTIAL UPDATE POST
# Route: PATCH /api/posts/{post_id}
# PATCH updates only sent fields
# ==================================================
@router.patch("/{post_id}", response_model=PostResponse)
async def update_post_partial(
    post_id: int,
    post_data: PostUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
):

    # Find post
    result = await db.execute(
        select(models.Post).where(models.Post.id == post_id)
    )

    post = result.scalars().first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    # Convert only provided fields to dictionary
    update_data = post_data.model_dump(exclude_unset=True)

    # Dynamically update fields
    for field, value in update_data.items():
        setattr(post, field, value)

    # Save changes
    await db.commit()

    # Reload author relation
    await db.refresh(post, attribute_names=["author"])

    return post


# ==================================================
# 📝 DELETE POST
# Route: DELETE /api/posts/{post_id}
# ==================================================
@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):

    # Find post
    result = await db.execute(
        select(models.Post).where(models.Post.id == post_id)
    )

    post = result.scalars().first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    # Delete post
    await db.delete(post)

    # Save deletion
    await db.commit()