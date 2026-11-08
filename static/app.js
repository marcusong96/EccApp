/*
  static/app.js - the behaviour of the page.

  The pattern used everywhere here:
    1. The user does something (submit form, tick a box, click delete).
    2. We call the API with fetch().
    3. When it answers, we reload the list from the server and redraw it.

  Reloading from the server after every change keeps the page and the
  database in sync - the database is always the "source of truth".
*/

// Grab the page elements we need once, up front.
const form = document.getElementById("new-task-form");
const input = document.getElementById("new-task-title");
const addButton = form.querySelector("button[type=submit]");
const list = document.getElementById("task-list");
const emptyMessage = document.getElementById("empty-message");
const summary = document.getElementById("summary");
const errorMessage = document.getElementById("error-message");

/*
  api() - one small wrapper around fetch() so every call handles errors the
  same way. If the server answers with an error status (400, 404, 500...),
  it throws, using the {"error": "..."} message our Flask app sends.
*/
async function api(method, url, body) {
  const options = { method, headers: {} };
  if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }

  const response = await fetch(url, options);
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.error || `Request failed (${response.status})`);
  }
  // 204 No Content has no body to read.
  return response.status === 204 ? null : response.json();
}

function showError(message) {
  errorMessage.textContent = message;
  errorMessage.hidden = !message;
}

/* Build the <li> for one task. */
function renderTask(task) {
  const item = document.createElement("li");
  if (task.done) item.classList.add("done");

  // Checkbox: ticking it toggles done / not done.
  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.checked = task.done;
  checkbox.setAttribute("aria-label", `Mark "${task.title}" as done`);
  checkbox.addEventListener("change", () =>
    run(() => api("PATCH", `/api/tasks/${task.id}`))
  );

  // Title. IMPORTANT: textContent (not innerHTML) shows the text as plain text.
  // If someone types "<script>...</script>" as a task, it is displayed,
  // never executed. Using innerHTML here would be a security hole (XSS).
  const title = document.createElement("span");
  title.className = "title";
  title.textContent = task.title;

  // Delete button.
  const deleteButton = document.createElement("button");
  deleteButton.className = "delete";
  deleteButton.textContent = "✕";
  deleteButton.setAttribute("aria-label", `Delete "${task.title}"`);
  deleteButton.addEventListener("click", () =>
    run(() => api("DELETE", `/api/tasks/${task.id}`))
  );

  item.append(checkbox, title, deleteButton);
  return item;
}

/* Fetch all tasks from the server and redraw the whole list. */
async function loadTasks() {
  const tasks = await api("GET", "/api/tasks");
  list.replaceChildren(...tasks.map(renderTask));

  const doneCount = tasks.filter((t) => t.done).length;
  emptyMessage.hidden = tasks.length > 0;
  summary.textContent = tasks.length ? `${doneCount} of ${tasks.length} done` : "";
}

/*
  run() - do an action, then refresh the list. Any error along the way is
  shown on the page instead of failing silently.
  With no action given, it just loads and shows the tasks.
*/
async function run(action = async () => {}) {
  try {
    showError("");
    await action();
    await loadTasks();
  } catch (err) {
    showError(err.message);
  }
}

// True while a "create task" request is on its way to the server.
let adding = false;

// Creating a task: the form's "submit" fires on Enter or clicking "Add".
form.addEventListener("submit", async (event) => {
  event.preventDefault(); // stop the browser reloading the page
  const title = input.value.trim();
  // Ignore empty input, and ignore extra submits while one is still in
  // progress (pressing Enter twice quickly would otherwise add duplicates).
  if (!title || adding) return;

  adding = true;
  addButton.disabled = true;
  try {
    await run(async () => {
      await api("POST", "/api/tasks", { title });
      input.value = "";
    });
  } finally {
    adding = false;
    addButton.disabled = false;
    input.focus();
  }
});

// Show the tasks as soon as the page opens.
run();
