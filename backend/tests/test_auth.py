"""
Tests for logins and one database per account (auth.py, database.get_db).

Each test gets its own empty accounts database (in memory) and a temporary
accounts folder, so nothing touches backend/auth.db or backend/accounts/.
Routes are called directly, like the rest of the tests.
"""

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import auth
import database
import main
import schemas
from models import DishType

INVITE = 'test-invite'


@pytest.fixture(autouse=True)
def accounts(tmp_path, monkeypatch):
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    monkeypatch.setattr(auth, 'AuthSession', sessionmaker(bind=engine, expire_on_commit=False))
    monkeypatch.setattr(auth, 'ACCOUNTS_DIR', tmp_path / 'accounts')
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    monkeypatch.setenv('INVITE_CODE', INVITE)
    monkeypatch.setenv('GUEST_AI_CALLS', '2')
    monkeypatch.setenv('GUEST_REPORTS', '1')
    auth.init_auth()
    yield
    for account_id in list(auth._engines):
        auth._engines.pop(account_id).dispose()
    engine.dispose()


def signup(email='owner@example.com', password='kitchen123', invite=INVITE):
    return main.signup(schemas.SignupIn(email=email, password=password, invite_code=invite))


def account_for(token):
    return auth.get_account(f'Bearer {token}')


def session_for(token):
    """The database session a route would get for this token (database.get_db)."""
    return next(database.get_db(account_for(token)))


# --- Passwords and tokens ------------------------------------------------------------

def test_a_password_is_stored_only_as_a_hash():
    hashed = auth.hash_password('kitchen123')
    assert 'kitchen123' not in hashed
    assert auth.check_password('kitchen123', hashed)
    assert not auth.check_password('kitchen124', hashed)


def test_a_token_carries_the_account_and_cant_be_edited():
    token = signup()['token']
    assert account_for(token).email == 'owner@example.com'
    forged = jwt.encode({'sub': '1', 'exp': datetime.now(timezone.utc) + timedelta(days=1)}, 'wrong-key', algorithm='HS256')
    with pytest.raises(HTTPException) as e:
        account_for(forged)
    assert e.value.status_code == 401


def test_an_expired_token_is_refused():
    account = account_for(signup()['token'])
    old = auth.make_token(account, now=datetime.now(timezone.utc) - timedelta(days=auth.TOKEN_DAYS + 1))
    with pytest.raises(HTTPException) as e:
        account_for(old)
    assert e.value.status_code == 401


def test_no_token_means_no_data():
    with pytest.raises(HTTPException) as e:
        auth.get_account(None)
    assert e.value.status_code == 401


# --- Sign-up and login ---------------------------------------------------------------

def test_sign_up_needs_the_invite_code():
    with pytest.raises(HTTPException) as e:
        signup(invite='guess')
    assert e.value.status_code == 403


def test_one_account_per_email_whatever_the_case():
    signup()
    with pytest.raises(HTTPException) as e:
        signup(email='Owner@Example.com')
    assert e.value.status_code == 409


def test_login_with_the_right_password_only():
    signup()
    assert main.login(schemas.LoginIn(email='OWNER@example.com', password='kitchen123'))['token']
    with pytest.raises(HTTPException) as e:
        main.login(schemas.LoginIn(email='owner@example.com', password='wrong-one'))
    assert (e.value.status_code, e.value.detail) == (401, 'Email or password is wrong')


def test_a_new_account_starts_with_benchmarks_and_no_dishes():
    db = session_for(signup()['token'])
    assert main.fetch_dish(db) == []
    assert len(main.list_ingredients(db)) > 100          # the benchmark list


# --- Each account sees only its own data -------------------------------------------------

def test_accounts_cannot_see_each_others_dishes():
    a = session_for(signup('a@example.com')['token'])
    b = session_for(signup('b@example.com')['token'])
    main.create_dish(schemas.DishCreate(name='Margherita', menu_price=10.0, category=DishType.MAIN), a)
    assert [d.name for d in main.fetch_dish(a)] == ['Margherita']
    assert main.fetch_dish(b) == []


def test_each_account_has_its_own_folder_for_uploads():
    token = signup()['token']
    assert main.uploads_dir(session_for(token)) == auth.ACCOUNTS_DIR / str(account_for(token).id) / 'uploads'


# --- Try the demo ------------------------------------------------------------------------------

def test_the_demo_is_a_private_copy_of_the_demo_pizzeria():
    first, second = main.try_demo(), main.try_demo()
    assert first['account']['kind'] == 'guest'
    a, b = session_for(first['token']), session_for(second['token'])
    assert len(main.fetch_dish(a)) > 10
    main.delete_dish(main.fetch_dish(a)[0].id, a)
    assert len(main.fetch_dish(b)) == len(main.fetch_dish(a)) + 1     # b's copy untouched


def test_an_expired_guest_is_refused_and_cleared_away():
    demo = main.try_demo()
    account = account_for(demo['token'])
    with auth.AuthSession() as session:
        session.get(auth.Account, account.id).expires_at = datetime.now() - timedelta(minutes=1)
        session.commit()
    with pytest.raises(HTTPException):
        account_for(demo['token'])
    folder = auth.ACCOUNTS_DIR / str(account.id)
    assert folder.exists()
    newer = account_for(main.try_demo()['token'])     # the next demo clears expired guests
    assert not folder.exists()
    assert newer.id != account.id                     # ids are never reused


def test_guests_have_an_ai_allowance_and_owners_dont():
    guest = account_for(main.try_demo()['token'])
    main.count_ai_call(guest)
    main.count_ai_call(guest)                   # GUEST_AI_CALLS is 2 in these tests
    with pytest.raises(HTTPException) as e:
        main.count_ai_call(guest)
    assert e.value.status_code == 429
    main.count_report(guest)
    with pytest.raises(HTTPException):
        main.count_report(guest)                # GUEST_REPORTS is 1
    assert main.me(auth.get_account(f"Bearer {auth.make_token(guest)}"))['ai_calls_left'] == 0

    owner = account_for(signup()['token'])
    for _ in range(10):
        main.count_ai_call(owner)               # never limited
    assert main.me(owner)['ai_calls_left'] is None


def test_report_jobs_are_kept_apart_by_account():
    a = session_for(signup('a@example.com')['token'])
    b = session_for(signup('b@example.com')['token'])
    assert main.job_key(a, 1) != main.job_key(b, 1)
