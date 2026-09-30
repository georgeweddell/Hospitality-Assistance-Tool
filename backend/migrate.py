"""
Keeps every account database's schema (its tables and columns) up to date
with models.py, using Alembic migrations (step 11, agreed with George 28 Sep 2026).

A migration is a numbered script in migrations/versions/ that changes the
schema (e.g. adds a column). Each database records the last one it has run
(Alembic's alembic_version table); upgrade() runs any newer ones.

upgrade(engine) runs whenever an account database is first opened
(auth.engine_for), so after a deploy each account catches up on its next
request. `python migrate.py --all` brings every account up to date at once
(the live site runs it at startup).

Changing the schema from now on:
  1. change models.py
  2. from backend/:  alembic revision --autogenerate -m "what changed"
     (it compares models.py with backend/menu.db, which is still at the last
     migration: so do this before restarting the backend)
  3. read the new file in migrations/versions/ (autogenerate can miss things,
     e.g. a renamed column looks like one dropped and one added)
  4. restart the backend (main.py upgrades menu.db; accounts upgrade when
     opened), then commit the migration.
`alembic check` says whether models.py and the migrations agree.
Adding a table needs a migration too: create_all only runs for brand-new databases.
"""

import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect

HERE = Path(__file__).parent
BASELINE = '0001_baseline'


def alembic_config(connection) -> Config:
    config = Config(str(HERE / 'alembic.ini'))
    config.set_main_option('script_location', str(HERE / 'migrations'))
    config.attributes['connection'] = connection
    return config


def latest() -> str:
    """The newest migration in migrations/versions/."""
    return ScriptDirectory.from_config(alembic_config(None)).get_current_head()


def revision(engine) -> str | None:
    """The last migration this database has run; None if it has no record."""
    with engine.connect() as connection:
        return MigrationContext.configure(connection).get_current_revision()


def mark_up_to_date(engine):
    """Records that the database is at the latest migration (it was just built from models.py)."""
    with engine.begin() as connection:
        command.stamp(alembic_config(connection), 'head')


def upgrade(engine):
    """
    Brings the database's schema up to date:
      - brand new (no tables): built from models.py, marked as up to date;
      - made before Alembic (tables, no record): any missing tables added,
        marked as the baseline, then newer migrations run. (This catch-up
        assumes models.py is still at the baseline; every database is marked
        at the first deploy, and resets mark theirs: seed_demo.reset_database.)
      - otherwise: newer migrations run (none: nothing happens).
    """
    import models  # noqa: F401  (registers every table on Base)
    from database import Base
    with engine.begin() as connection:
        config = alembic_config(connection)
        if MigrationContext.configure(connection).get_current_revision() is None:
            new = not inspect(connection).get_table_names()
            Base.metadata.create_all(bind=connection)
            if new:
                command.stamp(config, 'head')
                return
            command.stamp(config, BASELINE)
        command.upgrade(config, 'head')


def upgrade_all() -> int:
    """Every account database brought up to date. Returns how many."""
    import auth
    folders = [f for f in auth.ACCOUNTS_DIR.glob('*') if f.name.isdigit() and (f / 'menu.db').exists()]
    for folder in folders:
        auth.engine_for(int(folder.name))     # opening an account runs upgrade()
    return len(folders)


if __name__ == '__main__':
    if sys.argv[1:] != ['--all']:
        sys.exit('Usage: python migrate.py --all')
    print(f'{upgrade_all()} account databases up to date')
