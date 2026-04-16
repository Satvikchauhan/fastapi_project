# For handling datetime in responses (e.g., post creation time)
from datetime import datetime

# Pydantic tools for data validation and schema definition
from pydantic import BaseModel, ConfigDict, EmailStr, Field


# =========================
# 👤 USER SCHEMAS
# =========================

# Base schema (shared fields)
class UserBase(BaseModel):
    # Username validation:
    # - must be string
    # - min length = 1
    # - max length = 50
    username: str = Field(min_length=1, max_length=50)

    # Email validation:
    # - must be valid email format
    # - max length = 120
    email: EmailStr = Field(max_length=120)


# Schema used when creating a user (request body)
# Inherits all fields from UserBase
class UserCreate(UserBase):
    pass


# Schema used when returning user data (response)
class UserResponse(UserBase):
    # Allows this model to read data from ORM (SQLAlchemy models)
    model_config = ConfigDict(from_attributes=True)

    # Additional fields returned in response
    id: int                          # User ID
    image_file: str | None           # Profile image filename (optional)
    image_path: str                  # Computed full image path


# =========================
# 📝 POST SCHEMAS
# =========================

# Base schema for posts (shared fields)
class PostBase(BaseModel):
    # Title validation:
    # - required
    # - 1 to 100 characters
    title: str = Field(min_length=1, max_length=100)

    # Content validation:
    # - required
    # - at least 1 character
    content: str = Field(min_length=1)


# Schema used when creating a post (request body)
class PostCreate(PostBase):
    # TEMPORARY: user_id is passed manually
    # Later, you’ll replace this with authenticated user
    user_id: int


# Schema used when returning post data (response)
class PostResponse(PostBase):
    # Enables reading from SQLAlchemy models
    model_config = ConfigDict(from_attributes=True)

    # Additional fields returned in API response
    id: int                      # Post ID
    user_id: int                 # ID of the author
    date_posted: datetime        # When post was created

    # Nested response (VERY IMPORTANT 🔥)
    # Includes full user data inside post response
    author: UserResponse