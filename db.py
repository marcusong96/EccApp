"""
db.py - everything that talks to the SQLite database lives here.

The web code (app.py) never writes SQL itself. It calls these functions
instead. Keeping all database code in one place makes it easier to read,
change and test.

Every function takes `db_path`, the location of the database file.
The real app uses "todo.db"; tests pass a temporary file so they never
touch your real data.
"""

import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime


@contextmanager
def get_connection(db_path):
    """Open a connection, and ALWAYS close it afterwards.

    Use it like:
        with get_connection(db_path) as conn:
            conn.execute(...)

    On leaving the `with` block, changes are committed (saved) - or rolled
    back (undone) if an error happened - and then the connection is closed.

    Note: sqlite3's own `with conn:` only commits; it does NOT close the
    connection. That is why we wrap it here (found in the Phase 7 code review).
    """
    conn = sqlite3.connect(db_path)
    # Return rows that behave like dictionaries: row["title"] instead of row[1].
    conn.row_factory = sqlite3.Row
    try:
        with conn:  # commit on success, roll back on error
            yield conn
    finally:
        conn.close()  # runs no matter what - even if an error was raised


def init_db(db_path):
    """Create the tasks table if it does not exist yet. Safe to call every start-up."""
    with get_connection(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,  -- unique number, set automatically
                title      TEXT    NOT NULL,                   -- the task text
                done       INTEGER NOT NULL DEFAULT 0,         -- 0 = not done, 1 = done
                created_at TEXT    NOT NULL                    -- when it was added (ISO 8601, UTC)
            )
            """
        )


def _row_to_dict(row):
    """Convert a database row into a plain dict that Flask can turn into JSON."""
    return {
        "id": row["id"],
        "title": row["title"],
        "done": bool(row["done"]),  # store 0/1, but give the front end true/false
        "created_at": row["created_at"],
    }


def _fetch_task(conn, task_id):
    """Read one task using an already-open connection. Returns a dict or None."""
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return _row_to_dict(row) if row else None


def list_tasks(db_path):
    """Return every task, oldest first."""
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()
    return [_row_to_dict(r) for r in rows]


def get_task(db_path, task_id):
    """Return one task as a dict, or None if that id does not exist."""
    with get_connection(db_path) as conn:
        return _fetch_task(conn, task_id)


def create_task(db_path, title):
    """Insert a new task and return it."""
    created_at = datetime.now(UTC).isoformat(timespec="seconds")
    with get_connection(db_path) as conn:
        # The "?" placeholders let SQLite insert the values safely.
        # Never build SQL by gluing strings together - that allows SQL injection.
        cursor = conn.execute(
            "INSERT INTO tasks (title, created_at) VALUES (?, ?)",
            (title, created_at),
        )
        return _fetch_task(conn, cursor.lastrowid)


def toggle_task(db_path, task_id):
    """Flip a task between done and not done. Returns the updated task, or None if missing."""
    # Update and re-read in ONE connection, so nothing can change in between.
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "UPDATE tasks SET done = 1 - done WHERE id = ?",  # 1-0 = 1, 1-1 = 0
            (task_id,),
        )
        if cursor.rowcount == 0:  # no row matched that id
            return None
        return _fetch_task(conn, task_id)


def delete_task(db_path, task_id):
    """Delete a task. Returns True if something was deleted, False if the id was not found."""
    with get_connection(db_path) as conn:
        cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        return cursor.rowcount > 0
