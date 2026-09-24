"""
Date ranges for analysis. The default view is a calendar month.
"""

from datetime import date, timedelta

from sqlalchemy import func

from models import SalesRecord


def month_bounds(day: date) -> tuple[date, date]:
    """The first and last day of the month containing `day`."""
    start = day.replace(day=1)
    next_month = (start + timedelta(days=32)).replace(day=1)
    return start, next_month - timedelta(days=1)


def default_range(db) -> tuple[date, date]:
    """
    The month containing the most recent sale: the latest month with data.
    (Not "last month from today", so an old dataset still opens on something.)
    With no sales at all, the current month.
    """
    latest = db.query(func.max(SalesRecord.period_end)).scalar()
    return month_bounds(latest or date.today())


def resolve_range(db, start: date | None, end: date | None) -> tuple[date, date]:
    """The range a route should analyse: the one asked for, or the default."""
    if start is None or end is None:
        return default_range(db)
    if start > end:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="The start date is after the end date")
    return start, end
