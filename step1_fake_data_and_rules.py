"""
STEP 1 + STEP 2: Fake Instance Data + Rule Engine
--------------------------------------------------
No AWS needed. This simulates what CloudWatch + boto3 would give you later.
Run this file directly to test: python step1_fake_data_and_rules.py
"""

# -----------------------------
# STEP 1: Fake instance data
# -----------------------------
# Later, this same shape of data will come from real AWS CloudWatch/boto3.
# For now, we just hardcode a few example instances to test our logic.

fake_instances = [
    {
        "instance_id": "i-123",
        "state": "running",
        "cpu_percent": 3,
        "training_status": "completed",
        "runtime_hours": 2,
    },
    {
        "instance_id": "i-456",
        "state": "running",
        "cpu_percent": 5,
        "training_status": "completed",
        "runtime_hours": 1,
    },
    {
        "instance_id": "i-789",
        "state": "stopped",
        "cpu_percent": 0,
        "training_status": "completed",
        "runtime_hours": 5,
    },
]


# -----------------------------
# STEP 2: Rule engine
# -----------------------------
def detect_anomaly(instance):
    """
    Takes one instance's data and returns an anomaly dict if something
    looks wasteful, or None if everything looks fine.
    """

    # Rule 1: Training finished, but instance is still running and idle
    if (
        instance["training_status"] == "completed"
        and instance["state"] == "running"
        and instance["cpu_percent"] < 10
    ):
        return {
            "instance_id": instance["instance_id"],
            "anomaly_type": "Idle Instance After Training",
            "root_cause": "Training completed, but the instance was not stopped or terminated.",
            "recommended_action": "STOP_INSTANCE",
        }

    # Rule 2 (example of adding more rules later): Long-running training
    if instance["training_status"] == "running" and instance["runtime_hours"] > 24:
        return {
            "instance_id": instance["instance_id"],
            "anomaly_type": "Stuck Training Job",
            "root_cause": "Training has been running for over 24 hours without completing.",
            "recommended_action": "ALERT_USER",
        }

    # No anomaly found
    return None


# -----------------------------
# Run detection on all instances
# -----------------------------
if __name__ == "__main__":
    print("Scanning instances...\n")

    for instance in fake_instances:
        result = detect_anomaly(instance)

        print(f"Instance: {instance['instance_id']}")
        print(
            f"  State: {instance['state']} | CPU: {instance['cpu_percent']}% | Training: {instance['training_status']}"
        )

        if result:
            print("  ⚠️  ANOMALY DETECTED")
            print(f"     Type: {result['anomaly_type']}")
            print(f"     Root Cause: {result['root_cause']}")
            print(f"     Recommended Action: {result['recommended_action']}")
        else:
            print("  ✅ No anomaly")

        print("-" * 50)
