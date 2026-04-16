from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
#👉create_engine → connects to database
#👉sessionmaker → creates DB sessions (like connection instances)
#👉DeclarativeBase → base class for models (tables)

SQLALCHEMY_DATABASE_URL = "sqlite:///./blog.db"       #👉sqlite → database type , ./blog.db → file path#


#below 👉 Creates a connection to database
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},     #below 👉 Needed for SQLite in FastAPI Allows multiple requests (threads) Without this → app may crash

)

#below 👉 Creates a factory to generate DB sessions
#Parameters:
#autocommit=False → you control when to save
#autoflush=False → no auto sync to DB
#bind=engine → connect to DB engine

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

#base class forall class
class Base(DeclarativeBase):
    pass

#👉 Provides a database session to your API

#Step-by-step:
#SessionLocal() → creates DB session
##with → ensures it closes automatically
#yield db → gives session to FastAPI
def get_db():
    with SessionLocal() as db:
        yield db