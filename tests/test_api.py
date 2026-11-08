"""
tests/test_api.py - automated tests for the To-Do API.

Run them from the project folder with:
    python -m pytest -v

Each test is a small story: "do X, expect Y". If the code breaks later,
a test fails and tells you exactly which behaviour broke.
"""

import json
import sqlite3

import pytest

import db
from app import create_app

# ---------------------------------------------------------------------------
# Fixtures: reusable setup that pytest gives to any test that asks for it
# by name (e.g. a test with a `client` parameter gets the client below).
# ---------------------------------------------------------------------------

@pytest.fixture
def db_path(tmp_path):
    """A brand-new, empty database file for each test (deleted afterwards)."""
    return str(tmp_path / "test.db")


@pytest.fixture
def client(db_path):
    """A fake browser that sends requests to our app without starting a real server."""
    app = create_app(db_path)
    app.config["TESTING"] = True
    return app.test_client()


def add_task(client, title):
    """Helper: create a task through the API and return the response."""
    return client.post("/api/tasks", json={"title": title})


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------

def test_list_is_empty_at_start(client):
    response = client.get("/api/tasks")
    assert response.status_code == 200
    assert response.get_json() == []


# ---------------------------------------------------------------------------
# Creating
# ---------------------------------------------------------------------------

def test_create_task(client):
    response = add_task(client, "Buy milk")
    assert response.status_code == 201  # 201 = "Created"
    task = response.get_json()
    assert task["title"] == "Buy milk"
    assert task["done"] is False
    assert "id" in task and "created_at" in task


def test_created_task_appears_in_list(client):
    add_task(client, "Buy milk")
    add_task(client, "Walk the dog")
    titles = [t["title"] for t in client.get("/api/tasks").get_json()]
    assert titles == ["Buy milk", "Walk the dog"]


def test_title_is_trimmed(client):
    task = add_task(client, "   Read a book   ").get_json()
    assert task["title"] == "Read a book"


@pytest.mark.parametrize("bad_body", [{}, {"title": ""}, {"title": "   "}, {"title": 123}])
def test_create_rejects_missing_or_empty_title(client, bad_body):
    # parametrize runs this one test 4 times, once per bad input.
    response = client.post("/api/tasks", json=bad_body)
    assert response.status_code == 400  # 400 = "Bad Request"
    assert "error" in response.get_json()


def test_create_rejects_non_json_body(client):
    response = client.post("/api/tasks", data="not json")
    assert response.status_code == 400


def test_create_accepts_title_at_max_length(client):
    assert add_task(client, "a" * 200).status_code == 201


def test_create_rejects_oversized_request_body(client):
    # A huge body must be refused BEFORE it is read into memory - even if the
    # title inside it is fine. 413 = "Payload Too Large".
    big_body = json.dumps({"title": "ok", "padding": "x" * 100_000})
    response = client.post("/api/tasks", data=big_body, content_type="application/json")
    assert response.status_code == 413
    assert "error" in response.get_json()  # same JSON error shape as other errors


def test_create_rejects_too_long_title(client):
    # The HTML form limits input to 200 characters, but anyone can call the
    # API directly (e.g. with curl), so the server must check too.
    response = add_task(client, "a" * 201)
    assert response.status_code == 400
    assert "error" in response.get_json()


# ---------------------------------------------------------------------------
# Toggling done / not done
# ---------------------------------------------------------------------------

def test_toggle_marks_done_then_undone(client):
    task_id = add_task(client, "Buy milk").get_json()["id"]

    first = client.patch(f"/api/tasks/{task_id}")
    assert first.status_code == 200
    assert first.get_json()["done"] is True

    second = client.patch(f"/api/tasks/{task_id}")
    assert second.get_json()["done"] is False


def test_toggle_missing_task_returns_404(client):
    response = client.patch("/api/tasks/999")
    assert response.status_code == 404  # 404 = "Not Found"
    assert "error" in response.get_json()


# ---------------------------------------------------------------------------
# Deleting
# ---------------------------------------------------------------------------

def test_delete_task(client):
    task_id = add_task(client, "Buy milk").get_json()["id"]

    response = client.delete(f"/api/tasks/{task_id}")
    assert response.status_code == 204  # 204 = "No Content" (success, nothing to return)
    assert client.get("/api/tasks").get_json() == []


def test_delete_missing_task_returns_404(client):
    response = client.delete("/api/tasks/999")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Persistence: data really lives in the database, not just in memory
# ---------------------------------------------------------------------------

def test_tasks_are_saved_in_database(client, db_path):
    add_task(client, "Buy milk")
    # Read the database directly, bypassing the API.
    rows = db.list_tasks(db_path)
    assert len(rows) == 1
    assert rows[0]["title"] == "Buy milk"


def test_tasks_survive_app_restart(db_path):
    # Start the app, add a task, then start a *new* app on the same file.
    create_app(db_path).test_client().post("/api/tasks", json={"title": "Buy milk"})
    restarted = create_app(db_path).test_client()
    assert [t["title"] for t in restarted.get("/api/tasks").get_json()] == ["Buy milk"]


def test_database_connections_are_closed(client, monkeypatch):
    # Record every connection the app opens, then check each one was closed.
    opened = []
    real_connect = sqlite3.connect

    def tracking_connect(*args, **kwargs):
        conn = real_connect(*args, **kwargs)
        opened.append(conn)
        return conn

    monkeypatch.setattr(sqlite3, "connect", tracking_connect)

    task_id = add_task(client, "Buy milk").get_json()["id"]
    client.get("/api/tasks")
    client.patch(f"/api/tasks/{task_id}")
    client.delete(f"/api/tasks/{task_id}")

    assert opened, "expected the app to open at least one connection"
    for conn in opened:
        # Using a closed connection raises ProgrammingError.
        with pytest.raises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")


# ---------------------------------------------------------------------------
# Home page
# ---------------------------------------------------------------------------

def test_home_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"<html" in response.data.lower()
