from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from fastapi import Depends

# Where the database lives — just a file called menu.db in the backend folder.
SQLALCHEMY_DATABASE_URL = "sqlite:///./menu.db"

# The engine is the live connection to that file.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite-only quirk (see below)
)

# SessionLocal is a factory: call it to get a fresh session (one DB conversation).
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base is the parent class every model will inherit from.
# SQLAlchemy uses it to keep track of all your tables.
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



def get_current_user(db: Session = Depends(get_db)) -> "User": # type: ignore
    from models import User
    # Stub for now — always returns the one seeded dev user.
    # Phase 6 replaces this body with real login-token verification;
    # every route that calls Depends(get_current_user) stays unchanged.
    return db.query(User).first()