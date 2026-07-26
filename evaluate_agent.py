"""
EVALUATION HARNESS
----------------------
Runs the agent against a set of LABELED test scenarios (each with a known
"correct" answer) and computes concrete success metrics. This is what
turns "our agent seems to work" into "our agent is X% accurate."

We reuse the SAME diagnose_node/reflect_node logic the real dashboard
uses (via run_full_agent), but with human_approved=False, so NO real
AWS action is ever taken during evaluation - only the reasoning quality
is being measured, safely and repeatably.

Run with: python evaluate_agent.py
Results are printed and saved to eval_results.json
"""

import json
import time
from agent_graph import run_full_agent

# -----------------------------------------
# Labeled test set: each scenario has a known correct answer,
# based on the same policies in knowledge_base.py.
# -----------------------------------------
TEST_SCENARIOS = [
    {
        "name": "Clearly idle after training",
        "instance": {"instance_id": "i-test01", "state": "running", "cpu_percent": 0.5,
                     "training_status": "completed", "runtime_hours": 5.0},
        "expected_should_stop": True
    },
    {
        "name": "Actively training, high CPU",
        "instance": {"instance_id": "i-test02", "state": "running", "cpu_percent": 87.0,
                     "training_status": "running", "runtime_hours": 2.0},
        "expected_should_stop": False
    },
    {
        "name": "Already stopped",
        "instance": {"instance_id": "i-test03", "state": "stopped", "cpu_percent": 0.0,
                     "training_status": "completed", "runtime_hours": 0.0},
        "expected_should_stop": False
    },
    {
        "name": "Freshly started, low CPU (should be cautious)",
        "instance": {"instance_id": "i-test04", "state": "running", "cpu_percent": 0.0,
                     "training_status": "completed", "runtime_hours": 0.05},
        "expected_should_stop": False  # too new to trust the data yet
    },
    {
        "name": "Idle for a long time, unknown training status",
        "instance": {"instance_id": "i-test05", "state": "running", "cpu_percent": 2.0,
                     "training_status": "unknown", "runtime_hours": 6.0},
        "expected_should_stop": False  # policy says don't stop on 'unknown' status
    },
    {
        "name": "Moderate CPU, training completed",
        "instance": {"instance_id": "i-test06", "state": "running", "cpu_percent": 25.0,
                     "training_status": "completed", "runtime_hours": 3.0},
        "expected_should_stop": False  # meaningful CPU activity, not idle
    },
]


def run_evaluation():
    results = []
    reflection_interventions = 0
    total_latency = 0.0

    for scenario in TEST_SCENARIOS:
        print(f"Running: {scenario['name']}...")
        start = time.time()
        outcome = run_full_agent(scenario["instance"], human_approved=False)
        latency = round(time.time() - start, 2)
        total_latency += latency

        agent_said_stop = outcome["wants_to_act"] and outcome["reflection_passed"]
        correct = agent_said_stop == scenario["expected_should_stop"]

        # Did reflection change the outcome from the initial diagnosis?
        reflection_intervened = outcome["wants_to_act"] and not outcome["reflection_passed"]
        if reflection_intervened:
            reflection_interventions += 1

        results.append({
            "scenario": scenario["name"],
            "expected_should_stop": scenario["expected_should_stop"],
            "agent_decision": agent_said_stop,
            "correct": correct,
            "reflection_intervened": reflection_intervened,
            "reasoning": outcome["reasoning"],
            "reflection_notes": outcome["reflection_notes"],
            "latency_seconds": latency
        })

        status = "✅ CORRECT" if correct else "❌ WRONG"
        print(f"  Expected: {scenario['expected_should_stop']} | Agent said: {agent_said_stop} | {status}\n")

    # ---- Compute metrics ----
    total = len(results)
    correct_count = sum(1 for r in results if r["correct"])
    accuracy = round(correct_count / total * 100, 1)

    false_positives = sum(1 for r in results if r["agent_decision"] and not r["expected_should_stop"])
    false_negatives = sum(1 for r in results if not r["agent_decision"] and r["expected_should_stop"])

    avg_latency = round(total_latency / total, 2)

    summary = {
        "total_scenarios": total,
        "correct": correct_count,
        "accuracy_percent": accuracy,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "reflection_intervention_count": reflection_interventions,
        "average_latency_seconds": avg_latency,
        "results": results
    }

    with open("eval_results.json", "w") as f:
        json.dump(summary, f, indent=2)

    print("=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)
    print(f"Accuracy: {accuracy}% ({correct_count}/{total} correct)")
    print(f"False positives (stopped something that shouldn't be): {false_positives}")
    print(f"False negatives (missed something that should stop): {false_negatives}")
    print(f"Reflection stepped in to override the first decision: {reflection_interventions} time(s)")
    print(f"Average decision latency: {avg_latency}s")
    print("\nFull results saved to eval_results.json")

    return summary


if __name__ == "__main__":
    run_evaluation()
