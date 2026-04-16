# Allows using class names before they are defined (forward references)
from __future__ import annotations

# For handling date and time (used in post creation time)
from datetime import UTC, datetime

# SQLAlchemy column types and constraints
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text

# ORM tools for defining models and relationships
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Base class from your database setup (all models inherit from this)
from database import Base


# =========================
# 👤 USER TABLE (users)
# =========================
class User(Base):
    # Name of the table in database
    __tablename__ = "users"

    # Primary key (unique ID for each user)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Username column
    # - max length: 50
    # - must be unique
    # - cannot be NULL
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    # Email column
    # - max length: 120
    # - must be unique
    # - cannot be NULL
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)

    # Profile image file name
    # - optional (can be NULL)
    # - default value is None
    image_file: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        default=None,
    )

    # Relationship: One user can have many posts
    # "posts" will give a list of Post objects for this user
    posts: Mapped[list[Post]] = relationship(back_populates="author")

    # Computed property (NOT stored in database)
    # Returns full image path for frontend use
    @property
    def image_path(self) -> str:
        if self.image_file:
            # If user uploaded an image
            return f"/media/profile_pics/{self.image_file}"
        
        # Default image if no profile picture
        return "/static/profile_pics/default.jpg"


# =========================
# 📝 POST TABLE (posts)
# =========================
class Post(Base):
    # Table name in database
    __tablename__ = "posts"

    # Primary key (unique ID for each post)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Post title
    # - max length: 100
    # - cannot be NULL
    title: Mapped[str] = mapped_column(String(100), nullable=False)

    # Post content (large text allowed)
    # - cannot be NULL
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Foreign key linking post to user
    # - references users.id
    # - cannot be NULL
    # - indexed for faster queries
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    # Date when post was created
    # - automatically set to current UTC time
    date_posted: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    # Relationship: Each post belongs to one user
    # "author" gives access to the User object
    author: Mapped[User] = relationship(back_populates="posts")