"""
app.py - the Flask web server.

It does two jobs:
  1. Serves the web page (templates/index.html) at "/".
  2. Provides a JSON REST API at "/api/tasks" that the page's JavaScript calls.

Flow of one request:
    browser --HTTP--> route function here --calls--> db.py --SQL--> todo.db
    browser <--JSON-- route function here <--dict--- db.py

Start it with:  python app.py   then open http://127.0.0.1:5000
"""

import os

from flask import Flask, jsonify, render_template, request

import db

# Where the real database file lives. Tests use their own temporary file instead.
DEFAULT_DB_PATH = "todo.db"

# Longest title allowed. Matches maxlength="200" in templates/index.html,
# but enforced HERE too, because anyone can call the API without the page.
MAX_TITLE_LENGTH = 200


def create_app(db_path=DEFAULT_DB_PATH):
    """Build and return the Flask app.

    This is the "app factory" pattern: instead of one global app, we build a
    fresh one on demand. That lets each test create an app with its own database.
    """
    app = Flask(__name__)
    db.init_db(db_path)  # make sure the tasks table exists before any request

    def error(message, status):
        """Every error response has the same shape: {"error": "..."} + a status code."""
        return jsonify({"error": message}), status

    # ---------------------------------------------------------------- page --

    @app.get("/")
    def home():
        # Looks for templates/index.html (we build it in the next phase).
        return render_template("index.html")

    # ----------------------------------------------------------------- API --

    @app.get("/api/tasks")
    def list_tasks_route():
        """GET /api/tasks -> list of all tasks."""
        return jsonify(db.list_tasks(db_path))

    @app.post("/api/tasks")
    def create_task_route():
        """POST /api/tasks with {"title": "..."} -> the new task (201 Created)."""
        # silent=True returns None instead of crashing if the body is not valid JSON.
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return error("Request body must be JSON like {\"title\": \"...\"}", 400)

        title = body.get("title")
        # Validate input at the edge: never trust what the browser sends.
        if not isinstance(title, str) or not title.strip():
            return error("Title must be a non-empty string", 400)

        title = title.strip()
        if len(title) > MAX_TITLE_LENGTH:
            return error(f"Title must be at most {MAX_TITLE_LENGTH} characters", 400)

        task = db.create_task(db_path, title)
        return jsonify(task), 201

    @app.patch("/api/tasks/<int:task_id>")
    def toggle_task_route(task_id):
        """PATCH /api/tasks/<id> -> flip done/not done."""
        # <int:task_id> means Flask only matches numbers and hands us an int.
        task = db.toggle_task(db_path, task_id)
        if task is None:
            return error(f"Task {task_id} not found", 404)
        return jsonify(task)

    @app.delete("/api/tasks/<int:task_id>")
    def delete_task_route(task_id):
        """DELETE /api/tasks/<id> -> 204 No Content on success."""
        if not db.delete_task(db_path, task_id):
            return error(f"Task {task_id} not found", 404)
        return "", 204

    return app


# This block only runs when you start the file directly (python app.py),
# not when the tests import it.
if __name__ == "__main__":
    # Debug mode reloads on code changes and shows an in-browser debugger that
    # can run code - so it is OFF unless you ask for it:
    #     FLASK_DEBUG=1 python app.py
    # Never turn it on for a server other people can reach.
    create_app().run(debug=os.environ.get("FLASK_DEBUG") == "1")
