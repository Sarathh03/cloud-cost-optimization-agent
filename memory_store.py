"""
MEMORY / STATE MANAGEMENT
------------------------------
Stores every decision the agent makes (per instance) to a local JSON file,
so the agent has memory across runs instead of starting fresh every time.

This satisfies "memory and state management" as a real, working mechanism:
before deciding, the agent can look up what it decided last time for this
same instance and factor that into its reasoning (e.g. "I already
recommended stopping this and was overridden - should I ask again or note
that a human wants it kept running?").
"""

import json
import os
from datetime import datetime, timezone

MEMORY_FILE = "agent_memory.json"


def _load_memory():
    if not os.path.exists(MEMORY_FILE):
        return []
    with open(MEMORY_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def _save_memory(records):
    with open(MEMORY_FILE, "w") as f:
        json.dump(records, f, indent=2)


def log_decision(instance_id, instance_data, reasoning, action_taken, outcome=None):
    """
    Appends one decision record to memory. Call this after every agent run.
    """
    records = _load_memory()
    records.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "instance_id": instance_id,
        "instance_data": instance_data,
        "reasoning": reasoning,
        "action_taken": action_taken,   # "stopped" | "no_action" | "overridden"
        "outcome": outcome
    })
    _save_memory(records)


def get_history_for_instance(instance_id, limit=3):
    """
    Returns the last `limit` past decisions for this specific instance,
    most recent first. Used to give the agent memory of its own past
    reasoning about the same instance.
    """
    records = _load_memory()
    matching = [r for r in records if r["instance_id"] == instance_id]
    return list(reversed(matching))[:limit]


def summarize_history_for_prompt(instance_id):
    """
    Formats past decisions as a short text block to inject into the
    agent's reasoning prompt. Returns an empty string if there's no history.
    """
    history = get_history_for_instance(instance_id)
    if not history:
        return "No past decisions recorded for this instance."

    lines = []
    for h in history:
        lines.append(
            f"- {h['timestamp']}: action={h['action_taken']}, reasoning=\"{h['reasoning']}\""
        )
    return "Past decisions for this instance:\n" + "\n".join(lines)


if __name__ == "__main__":
    # Quick manual test
    log_decision(
        instance_id="i-testonly123",
        instance_data={"state": "running", "cpu_percent": 0.0},
        reasoning="Test entry - idle after training.",
        action_taken="no_action",
        outcome="Overridden by user"
    )
    print(summarize_history_for_prompt("i-testonly123"))
