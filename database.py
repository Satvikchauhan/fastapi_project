# Import async SQLAlchemy tools
# - AsyncSession → async DB session
# - async_sessionmaker → creates async session factory
# - create_async_engine → creates async DB connection
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Base class for defining database models (tables)
from sqlalchemy.orm import DeclarativeBase


# 🔹 Database connection URL
# Using SQLite with async driver (aiosqlite)
# Format: dialect+driver://path
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./blog.db"


# 🔹 Create async database engine (connection to DB)
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,

    # Required for SQLite to allow multiple threads (FastAPI uses concurrency)
    connect_args={"check_same_thread": False},
)


# 🔹 Create async session factory
# This will generate new DB sessions when needed
AsyncSessionLocal = async_sessionmaker(

    engine,                     # Bind session to DB engine
    class_=AsyncSession,        # Use async session class
    expire_on_commit=False,     # Prevent objects from expiring after commit
)


# 🔹 Base class for all ORM models (tables)
# All your models will inherit from this
class Base(DeclarativeBase):
    pass


# 🔹 Dependency function for FastAPI
# Provides a database session to each request
async def get_db():

    # Create a new async DB session
    async with AsyncSessionLocal() as session:

        # Yield session to API endpoint
        # FastAPI will automatically close it after request
        yield session