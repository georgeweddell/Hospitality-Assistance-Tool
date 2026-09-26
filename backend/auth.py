"""
Accounts, logins and one database per account (roadmap step 10, agreed with
George 26 Sep 2026).

How it works:
  - Accounts live in their own small database, auth.db. A password is never
    stored: only a bcrypt hash, a one-way scramble that can check a password
    but can't be turned back into it.
  - Logging in returns a token (a JWT): signed text saying "account 7, valid
    until 3 Oct". The browser sends it with every request as
    "Authorization: Bearer <token>". It is signed with SECRET_KEY from .env,
    so it can't be forged or edited.
  - Each account's restaurant data is its own SQLite file,
    accounts/<id>/menu.db, with its uploads and backups beside it. get_db
    (database.py) opens the logged-in account's file, so every route that uses
    it only ever sees that account's data: no query needs a filter, and a
    forgotten one can't leak data between accounts.

Kinds of account: "owner" (signed up with the invite code; no AI limit) and
"guest" (Try the demo: a private copy of the demo pizzeria, deleted after
GUEST_DAYS, with a small AI allowance: GUEST_AI_CALLS and GUEST_REPORTS).
"""

import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import Header, HTTPException
from sqlalchemy import Column, DateTime, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

BACKEND = Path(__file__).parent
ACCOUNTS_DIR = BACKEND / 'accounts'      # tests point this at a temporary folder
TOKEN_DAYS = 7
GUEST_DAYS = 7
MIN_PASSWORD = 8

AuthBase = declarative_base()   # separate from database.Base: accounts aren't restaurant data


class Account(AuthBase):
    __tablename__ = 'accounts'
    # Never reuse an id: a deleted guest's number (and folder name) must not pass to a new account.
    __table_args__ = {'sqlite_autoincrement': True}
    id = Column(Integer, primary_key=True)
    email = Column(String, nullable=True, unique=True)     # None for guests
    password_hash = Column(String, nullable=True)          # None for guests (they can't log in again)
    kind = Column(String, nullable=False, default='owner')  # owner / guest
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    expires_at = Column(DateTime, nullable=True)            # guests only
    ai_calls_used = Column(Integer, nullable=False, default=0)   # counted for guests only
    reports_used = Column(Integer, nullable=False, default=0)


auth_engine = create_engine(f"sqlite:///{BACKEND / 'auth.db'}", connect_args={'check_same_thread': False})
AuthSession = sessionmaker(bind=auth_engine, expire_on_commit=False)   # tests swap in an in-memory one


def init_auth():
    AuthBase.metadata.create_all(bind=AuthSession.kw['bind'])


# --- Passwords and tokens --------------------------------------------------------------

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(password: str, password_hash: str | None) -> bool:
    return bool(password_hash) and bcrypt.checkpw(password.encode(), password_hash.encode())


def secret() -> str:
    key = os.getenv('SECRET_KEY')
    if not key:
        raise RuntimeError('SECRET_KEY is not set in backend/.env: tokens cannot be signed without it.')
    return key


def make_token(account: Account, now: datetime | None = None) -> str:
    """A signed token for the account, valid for TOKEN_DAYS (or until a guest expires, if sooner)."""
    now = now or datetime.now(timezone.utc)
    expires = now + timedelta(days=TOKEN_DAYS)
    if account.expires_at:
        expires = min(expires, account.expires_at.replace(tzinfo=timezone.utc))
    return jwt.encode({'sub': str(account.id), 'exp': expires}, secret(), algorithm='HS256')


def read_token(token: str) -> int:
    """The account id in a token. Raises jwt.InvalidTokenError if it's forged, edited or expired."""
    return int(jwt.decode(token, secret(), algorithms=['HS256'])['sub'])


def get_account(authorization: str | None = Header(None)) -> Account:
    """
    The logged-in account, from the "Authorization: Bearer <token>" header.
    401 if there's no token, it's invalid or expired, or the account is gone
    or (a guest) past its date.
    """
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail='Please sign in')
    try:
        account_id = read_token(authorization.removeprefix('Bearer '))
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail='Your session has ended. Please sign in again')
    with AuthSession() as session:
        account = session.get(Account, account_id)
    if account is None or (account.expires_at and account.expires_at < datetime.now()):
        raise HTTPException(status_code=401, detail='Please sign in')
    return account


# --- One database per account -----------------------------------------------------------

_engines = {}


def account_folder(account_id: int) -> Path:
    folder = ACCOUNTS_DIR / str(account_id)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def engine_for(account_id: int):
    """The account's database engine, opened once and kept; new tables are created on first open."""
    if account_id not in _engines:
        from database import Base   # here, not at the top: database.py imports this file
        import models  # noqa: F401  (registers every table on Base)
        engine = create_engine(f"sqlite:///{account_folder(account_id) / 'menu.db'}",
                               connect_args={'check_same_thread': False})
        Base.metadata.create_all(bind=engine)
        _engines[account_id] = engine
    return _engines[account_id]


def session_factory_for(account_id: int):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine_for(account_id))


def delete_account_files(account_id: int):
    """Closes the account's database and deletes its folder (database, uploads, backups)."""
    engine = _engines.pop(account_id, None)
    if engine is not None:
        engine.dispose()
    shutil.rmtree(ACCOUNTS_DIR / str(account_id), ignore_errors=True)


def remove_expired_guests(now: datetime | None = None) -> int:
    """Deletes guest accounts past their date, with their files. Returns how many."""
    now = now or datetime.now()
    with AuthSession() as session:
        expired = session.query(Account).filter(Account.kind == 'guest', Account.expires_at < now).all()
        for account in expired:
            delete_account_files(account.id)
            session.delete(account)
        session.commit()
    return len(expired)


# --- The guest AI allowance ---------------------------------------------------------------

def guest_limits() -> tuple[int, int]:
    return int(os.getenv('GUEST_AI_CALLS', '15')), int(os.getenv('GUEST_REPORTS', '1'))


def use_ai(account: Account, report: bool = False):
    """
    Counts one AI call (or report) for a guest, or refuses with 429 when the
    allowance is used up. Owners are never counted or limited (George's choice).
    """
    if account.kind != 'guest':
        return
    calls, reports = guest_limits()
    with AuthSession() as session:
        row = session.get(Account, account.id)
        if report and row.reports_used >= reports:
            raise HTTPException(status_code=429, detail="The demo's report allowance is used up")
        if not report and row.ai_calls_used >= calls:
            raise HTTPException(status_code=429, detail="The demo's AI allowance is used up")
        if report:
            row.reports_used += 1
        else:
            row.ai_calls_used += 1
        session.commit()
