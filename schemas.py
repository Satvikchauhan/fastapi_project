# Used for date/time fields in API responses
from datetime import datetime

# Pydantic imports:
# BaseModel -> base class for schemas
# ConfigDict -> configure schema behavior
# EmailStr -> validates email format
# Field -> add validations like min/max length
from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ==================================================
# 👤 USER SCHEMAS
# ==================================================

# Base user schema
# Common fields reused in multiple user schemas
class UserBase(BaseModel):

    # Username:
    # Required string
    # Minimum 1 character
    # Maximum 50 characters
    username: str = Field(min_length=1, max_length=50)

    # Email:
    # Must be valid email format
    # Max 120 characters
    email: EmailStr = Field(max_length=120)


# --------------------------------------------------
# Schema used when creating a new user
# Input body for signup/register API
# --------------------------------------------------
class UserCreate(UserBase):

    # Password:
    # Minimum 8 characters
    password: str = Field(min_length=8)


# --------------------------------------------------
# Public user schema
# Safe data to expose publicly
# --------------------------------------------------
class UserPublic(BaseModel):

    # Allows reading directly from SQLAlchemy ORM objects
    model_config = ConfigDict(from_attributes=True)

    # User ID
    id: int

    # Public username
    username: str

    # Profile image filename (optional)
    image_file: str | None

    # Computed full image path
    image_path: str


# --------------------------------------------------
# Private user schema
# Used when user can see own private data
# Includes email
# --------------------------------------------------
class UserPrivate(UserPublic):

    # Private field
    email: EmailStr


# --------------------------------------------------
# User update schema
# Used for PATCH / partial updates
# All fields optional
# --------------------------------------------------
class UserUpdate(BaseModel):

    # Optional username update
    username: str | None = Field(
        default=None,
        min_length=1,
        max_length=50
    )

    # Optional email update
    email: EmailStr | None = Field(
        default=None,
        max_length=120
    )

    # Optional profile image filename update
    image_file: str | None = Field(
        default=None,
        min_length=1,
        max_length=200
    )


# ==================================================
# 🔐 AUTH SCHEMA
# ==================================================

# Used after login
# Returns JWT token data
class Token(BaseModel):

    # JWT access token
    access_token: str

    # Token type usually "bearer"
    token_type: str


# ==================================================
# 📝 POST SCHEMAS
# ==================================================

# Base post schema
# Shared fields for create / response
class PostBase(BaseModel):

    # Post title:
    # Required
    # 1 to 100 chars
    title: str = Field(min_length=1, max_length=100)

    # Post content:
    # Required
    # At least 1 character
    content: str = Field(min_length=1)


# --------------------------------------------------
# Schema used to create post
# Input for POST /posts
# --------------------------------------------------
class PostCreate(PostBase):

    # TEMPORARY:
    # Currently passing user_id manually
    # Later replaced by authenticated logged-in user
    user_id: int


# --------------------------------------------------
# Schema for partial update
# Used in PATCH /posts/{id}
# All fields optional
# --------------------------------------------------
class PostUpdate(BaseModel):

    # Optional title update
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=100
    )

    # Optional content update
    content: str | None = Field(
        default=None,
        min_length=1
    )


# --------------------------------------------------
# Schema returned in API response
# Used for GET /posts etc.
# --------------------------------------------------
class PostResponse(PostBase):

    # Allows reading from SQLAlchemy ORM objects
    model_config = ConfigDict(from_attributes=True)

    # Post ID
    id: int

    # User who created post
    user_id: int

    # Post creation datetime
    date_posted: datetime

    # Nested author object
    # Includes public user info
    author: UserPublic