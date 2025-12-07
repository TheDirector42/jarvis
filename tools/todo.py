import json
import time
from pathlib import Path
from typing import List, Dict
from langchain.tools import tool


TODO_PATH = Path(__file__).resolve().parent.parent / "slash_tasks.json"


def _load_tasks() -> List[Dict]:
    if not TODO_PATH.exists():
        return []
    try:
        return json.loads(TODO_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_tasks(tasks: List[Dict]) -> None:
    TODO_PATH.write_text(json.dumps(tasks, indent=2), encoding="utf-8")


@tool
def todo_add(task: str) -> str:
    """Add a to-do item."""
    text = task.strip()
    if not text:
        return "Please provide a task description."
    tasks = _load_tasks()
    task_id = int(time.time() * 1000)
    tasks.append({"id": task_id, "task": text, "done": False})
    _save_tasks(tasks)
    return f"Added task [{task_id}]: {text}"


@tool
def todo_list(_: str = "") -> str:
    """List to-do items with their ids and status."""
    tasks = _load_tasks()
    if not tasks:
        return "No tasks yet."
    lines = []
    for t in tasks:
        mark = "✅" if t.get("done") else "⬜"
        lines.append(f"{mark} [{t.get('id')}] {t.get('task')}")
    return "\n".join(lines)


@tool
def todo_complete(task_id: str) -> str:
    """Mark a to-do item complete by id."""
    try:
        target = int(task_id.strip())
    except Exception:
        return "Provide a numeric task id."

    tasks = _load_tasks()
    found = False
    for t in tasks:
        if t.get("id") == target:
            t["done"] = True
            found = True
            break
    if not found:
        return f"Task id {task_id} not found."
    _save_tasks(tasks)
    return f"Task {task_id} marked complete."
