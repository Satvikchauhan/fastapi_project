# Used to create token expiry duration
from datetime import timedelta

# Used for modern dependency type hints
from typing import Annotated


# FastAPI imports:
# APIRouter -> group user routes
# Depends -> dependency injection
# HTTPException -> raise API errors
# status -> HTTP status codes
from fastapi import APIRouter, Depends, HTTPException, status

# OAuth2 login form
# Accepts username + password in form-data
from fastapi.security import OAuth2PasswordRequestForm


# SQLAlchemy imports
# func -> SQL functions like lower()
# select -> query builder
from sqlalchemy import func, select

# Async database session
from sqlalchemy.ext.asyncio import AsyncSession

# Load related objects efficiently
from sqlalchemy.orm import selectinload


# Import ORM models
import models


# Import auth helper functions
from auth import (
    create_access_token,   # Create JWT token
    hash_password,         # Hash password before saving
    oauth2_scheme,         # Extract Bearer token
    verify_access_token,   # Verify JWT token
    verify_password,       # Compare plain password with hash
)

# Import app settings
from config import settings

# Import DB dependency
from database import get_db

# Import response/input schemas
from schemas import (
    PostResponse,
    Token,
    UserCreate,
    UserPrivate,
    UserPublic,
    UserUpdate,
)


# Create router object
router = APIRouter()


# ==================================================
# 👤 REGISTER USER
# Route: POST /api/users
# ==================================================
@router.post(
    "",
    response_model=UserPrivate,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    user: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):

    # Check username already exists (case-insensitive)
    result = await db.execute(
        select(models.User).where(
            func.lower(models.User.username)
            == user.username.lower(),
        ),
    )

    existing_user = result.scalars().first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    # Check email already exists
    result = await db.execute(
        select(models.User).where(
            func.lower(models.User.email)
            == user.email.lower()
        ),
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
        email=user.email.lower(),

        # Store hashed password only
        password_hash=hash_password(user.password),
    )

    # Add to DB session
    db.add(new_user)

    # Save changes
    await db.commit()

    # Reload object with generated id
    await db.refresh(new_user)

    return new_user


# ==================================================
# 🔐 LOGIN USER
# Route: POST /api/users/token
# ==================================================
@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[
        OAuth2PasswordRequestForm,
        Depends()
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
):

    # OAuth2PasswordRequestForm uses username field
    # Here username = email
    result = await db.execute(
        select(models.User).where(
            func.lower(models.User.email)
            == form_data.username.lower(),
        ),
    )

    user = result.scalars().first()

    # Verify email exists + password matches
    if not user or not verify_password(
        form_data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",

            # Standard auth header
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create token expiry duration
    access_token_expires = timedelta(
        minutes=settings.access_token_expire_minutes
    )

    # Create JWT token
    access_token = create_access_token(
        data={"sub": str(user.id)},   # subject = user id
        expires_delta=access_token_expires,
    )

    # Return token response
    return Token(
        access_token=access_token,
        token_type="bearer",
    )


# ==================================================
# 👤 GET CURRENT LOGGED-IN USER
# Route: GET /api/users/me
# ==================================================
@router.get("/me", response_model=UserPrivate)
async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Reads Bearer token from header
    Returns currently authenticated user
    """

    # Decode token and get user id
    user_id = verify_access_token(token)

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Convert token user id into integer
    try:
        user_id_int = int(user_id)

    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch user from DB
    result = await db.execute(
        select(models.User).where(
            models.User.id == user_id_int
        ),
    )

    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


# ==================================================
# 👤 GET PUBLIC USER PROFILE
# Route: GET /api/users/{user_id}
# ==================================================
@router.get("/{user_id}", response_model=UserPublic)
async def get_user(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):

    result = await db.execute(
        select(models.User).where(
            models.User.id == user_id
        )
    )

    user = result.scalars().first()

    if user:
        return user

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found",
    )


# ==================================================
# 📝 GET USER POSTS
# Route: GET /api/users/{user_id}/posts
# ==================================================
@router.get(
    "/{user_id}/posts",
    response_model=list[PostResponse]
)
async def get_user_posts(
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

    # Fetch posts latest first
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.user_id == user_id)
        .order_by(models.Post.date_posted.desc()),
    )

    posts = result.scalars().all()

    return posts


# ==================================================
# ✏️ UPDATE USER
# Route: PATCH /api/users/{user_id}
# ==================================================
@router.patch(
    "/{user_id}",
    response_model=UserPrivate
)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
):

    # Find user
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

    # Check duplicate username
    if (
        user_update.username is not None
        and user_update.username.lower()
        != user.username.lower()
    ):
        result = await db.execute(
            select(models.User).where(
                func.lower(models.User.username)
                == user_update.username.lower(),
            ),
        )

        existing_user = result.scalars().first()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists",
            )

    # Check duplicate email
    if (
        user_update.email is not None
        and user_update.email.lower()
        != user.email.lower()
    ):
        result = await db.execute(
            select(models.User).where(
                func.lower(models.User.email)
                == user_update.email.lower(),
            ),
        )

        existing_email = result.scalars().first()

        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

    # Update provided fields only
    if user_update.username is not None:
        user.username = user_update.username

    if user_update.email is not None:
        user.email = user_update.email.lower()

    if user_update.image_file is not None:
        user.image_file = user_update.image_file

    # Save changes
    await db.commit()

    # Reload updated object
    await db.refresh(user)

    return user


# ==================================================
# ❌ DELETE USER
# Route: DELETE /api/users/{user_id}
# ==================================================
@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_user(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):

    # Find user
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

    # Delete user
    await db.delete(user)

    # Save deletion
    await db.commit()