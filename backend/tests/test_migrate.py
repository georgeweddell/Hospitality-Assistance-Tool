"""
Tests for schema migrations (migrate.py, step 11). Each test uses SQLite files
in a temporary folder, so no real account database is touched.
"""

import shutil

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

import migrate
import models  # noqa: F401  (registers every table on Base)
from database import Base


def engine_at(path):
    return create_engine(f'sqlite:///{path}')


def columns(engine, table):
    return [c['name'] for c in inspect(engine).get_columns(table)]


def test_a_brand_new_database_is_built_and_marked_up_to_date(tmp_path):
    engine = engine_at(tmp_path / 'menu.db')
    migrate.upgrade(engine)
    assert 'dishes' in inspect(engine).get_table_names()
    assert migrate.revision(engine) == migrate.BASELINE      # the latest migration, for now


def test_a_database_from_before_alembic_keeps_its_data_and_gets_a_record(tmp_path):
    engine = engine_at(tmp_path / 'menu.db')
    Base.metadata.create_all(bind=engine)                    # how every database was made until now
    with Session(engine) as db:
        db.add(models.Dish(name='Margherita', category=models.DishType.MAIN))
        db.commit()
    with engine.begin() as c:
        c.execute(text('DROP TABLE reports'))                # a table added after this database was made
    assert migrate.revision(engine) is None

    migrate.upgrade(engine)
    assert migrate.revision(engine) == migrate.BASELINE
    assert 'reports' in inspect(engine).get_table_names()    # the missing table is added
    with engine.connect() as c:
        assert c.execute(text('SELECT name, category FROM dishes')).all() == [('Margherita', 'MAIN')]


def test_upgrading_twice_changes_nothing(tmp_path):
    engine = engine_at(tmp_path / 'menu.db')
    migrate.upgrade(engine)
    migrate.upgrade(engine)
    assert migrate.revision(engine) == migrate.BASELINE


def test_a_new_migration_reaches_an_existing_database(tmp_path, monkeypatch):
    # A copy of the migrations with one more: a new column on dishes.
    shutil.copy(migrate.HERE / 'alembic.ini', tmp_path / 'alembic.ini')
    shutil.copytree(migrate.HERE / 'migrations', tmp_path / 'migrations',
                    ignore=shutil.ignore_patterns('__pycache__'))
    (tmp_path / 'migrations' / 'versions' / '0002_note.py').write_text(
        "from alembic import op\n"
        "import sqlalchemy as sa\n"
        "revision = '0002_note'\n"
        "down_revision = '0001_baseline'\n"
        "branch_labels = depends_on = None\n"
        "def upgrade():\n"
        "    with op.batch_alter_table('dishes') as batch:\n"
        "        batch.add_column(sa.Column('note', sa.String(), nullable=True))\n"
        "def downgrade():\n"
        "    pass\n")

    engine = engine_at(tmp_path / 'menu.db')
    migrate.upgrade(engine)                                  # at the baseline, with the real migrations
    assert 'note' not in columns(engine, 'dishes')

    monkeypatch.setattr(migrate, 'HERE', tmp_path)           # a deploy that brings 0002
    migrate.upgrade(engine)
    assert migrate.revision(engine) == '0002_note'
    assert 'note' in columns(engine, 'dishes')


def test_a_reset_database_is_marked_up_to_date(tmp_path):
    from seed_demo import reset_database
    engine = engine_at(tmp_path / 'menu.db')
    reset_database(engine, with_demo=False)                  # "start fresh": built from today's models
    assert migrate.revision(engine) == migrate.BASELINE      # so no migration is run on it again
