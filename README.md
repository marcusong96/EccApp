# EccApp

A small **To-Do list web app** built step by step as a learning project, using
the ECC workflow (plan → test-first → build → verify → review → pull request).

Add tasks, tick them off, delete them. Everything is saved in a SQLite
database, so your tasks are still there after a restart.

**Tech:** Python 3.11+ · Flask · SQLite · plain HTML/CSS/JavaScript · pytest

---

## Run it on your computer

You need **Git** and **Python 3.11 or newer** (`python3 --version` to check).

```bash
git clone https://github.com/marcusong96/EccApp.git
cd EccApp
```

Create a virtual environment (a private folder of libraries for this project)
and install the dependencies:

**Mac / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell)**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Start the app:

```bash
python app.py
```

Open **http://127.0.0.1:5000** in your browser. Press `Ctrl + C` in the
terminal to stop the server.

> Port 5000 busy (common on macOS because of AirPlay)? Run
> `flask --app app run --port 5001` and open http://127.0.0.1:5001.
>
> Want auto-reload while editing code? `FLASK_DEBUG=1 python app.py`
> (only on your own machine - debug mode must never be reachable by others).

## Run the tests

With the virtual environment activated:

```bash
python -m pytest -v
```

Each test gets its own temporary database, so tests never touch your real data.

---

## How it works

```
Browser (templates/index.html + static/app.js)
   │  fetch("/api/tasks")                         ▲ JSON
   ▼                                              │
Flask routes (app.py)  ── validate input ──►  db.py  ──SQL──►  todo.db (SQLite file)
```

| File | Job |
|---|---|
| `app.py` | Flask web server: serves the page and the JSON API, validates input |
| `db.py` | All database code: creates the table, list / create / toggle / delete |
| `templates/index.html` | Page structure |
| `static/app.js` | Calls the API with `fetch()` and redraws the list after every change |
| `static/style.css` | Styling (follows your system's light/dark mode) |
| `tests/test_api.py` | Automated tests for every API route |

### Database

One table, `tasks`:

| Column | Type | Meaning |
|---|---|---|
| `id` | integer | Unique number, set automatically |
| `title` | text | The task (1-200 characters) |
| `done` | 0 / 1 | Finished or not |
| `created_at` | text | When it was added (ISO 8601, UTC) |

The database file `todo.db` is created automatically on first run and is
ignored by git (it's your data, not source code).

### API

| Method | URL | Body | Success | Errors |
|---|---|---|---|---|
| `GET` | `/api/tasks` | - | `200` list of tasks | - |
| `POST` | `/api/tasks` | `{"title": "Buy milk"}` | `201` new task | `400` missing / empty / too long title |
| `PATCH` | `/api/tasks/<id>` | - | `200` task with `done` flipped | `404` no such task |
| `DELETE` | `/api/tasks/<id>` | - | `204` no content | `404` no such task |

Errors always look like `{"error": "message"}`.

Try it from a terminal while the app is running:

```bash
curl -X POST http://127.0.0.1:5000/api/tasks -H "Content-Type: application/json" -d '{"title": "Buy milk"}'
curl http://127.0.0.1:5000/api/tasks
```

### Security basics in this project

- **SQL injection** is prevented by using `?` placeholders in every query (`db.py`).
- **XSS** is prevented by inserting task titles with `textContent`, never `innerHTML` (`static/app.js`).
- **Input is validated on the server** (type, blank, max length), not only in the browser (`app.py`).
- **Debug mode is off by default.**
