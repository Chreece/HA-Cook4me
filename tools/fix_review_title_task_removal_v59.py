#!/usr/bin/env python3
"""One-shot fail-closed fix for reviewed recipe-title task removal."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "tools/apply_release_catalog_reviews_v2.py"
text = PATH.read_text(encoding="utf-8")
old_groups = '''    recipe_groups = [\n        row for row in prep.get("recipeGroups") or [] if isinstance(row, dict)\n    ]\n\n    # Exact provider-group reviews'''
new_groups = '''    recipe_groups = [\n        row for row in prep.get("recipeGroups") or [] if isinstance(row, dict)\n    ]\n    original_recipe_title_tasks = {\n        _text(row.get("translationTaskId"))\n        for row in recipe_groups\n        if _text(row.get("translationTaskId"))\n    }\n\n    # Exact provider-group reviews'''
old_removal = '''    for task in queue.get("tasks") or []:\n        if not isinstance(task, dict) or task.get("type") != "recipe_title_english":\n            continue\n        task_id = _text(task.get("taskId"))\n        if task_id and task_id not in pending_recipe_title_tasks:\n            remove_tasks.add(task_id)\n'''
new_removal = '''    # Only remove title tasks that were actually referenced by this prep input\n    # before review and are no longer referenced afterwards. Unknown/partial\n    # queue rows are preserved fail-safe.\n    remove_tasks.update(original_recipe_title_tasks - pending_recipe_title_tasks)\n'''
for label, old, new in (
    ("capture original title tasks", old_groups, new_groups),
    ("safe reviewed title task removal", old_removal, new_removal),
):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one match, got {count}")
    text = text.replace(old, new, 1)
PATH.write_text(text, encoding="utf-8")
