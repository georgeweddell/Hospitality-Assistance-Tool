"""
How Alembic connects to a database (see migrate.py for when it runs).

- From the app (migrate.upgrade): the database to change is handed over as
  config.attributes['connection'].
- From the command line, to write a new migration: it compares models.py with
  a database already at the latest migration, backend/menu.db unless another
  is given:  alembic -x db=path/to/menu.db revision --autogenerate -m "..."
"""

from alembic import context
from sqlalchemy import create_engine

import models  # noqa: F401  (registers every table on Base)
from database import Base

config = context.config


def run(connection):
    # render_as_batch: SQLite can't change a column in place, so Alembic
    # rebuilds the table (copy, change, swap) instead.
    context.configure(connection=connection, target_metadata=Base.metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


connection = config.attributes.get('connection')
if connection is not None:
    run(connection)
else:
    engine = create_engine(f"sqlite:///{context.get_x_argument(as_dictionary=True).get('db', 'menu.db')}")
    with engine.connect() as connection:
        run(connection)
