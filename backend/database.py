from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from fastapi import Depends

from auth import get_account, session_factory_for

# The shared menu.db in the backend folder: used by seed_demo.py and the one-off
# check scripts. The app itself uses one database per account (auth.py, get_db).
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

def get_db(account=Depends(get_account)):
    """
    A session on the logged-in account's own database (auth.py): every route
    that uses this only ever sees that account's data, and needs a valid login
    token to run at all. The shared menu.db above is only for the one-off
    scripts and seed_demo.py.
    """
    db = session_factory_for(account.id)()
    try:
        yield db
    finally:
        db.close()
