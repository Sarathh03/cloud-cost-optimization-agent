"""
STEP 6: Real AWS Data (boto3 + CloudWatch)
----------------------------------------------
This replaces the fake_instances list from step1 with REAL data pulled
from your AWS account. It automatically finds all your EC2 instances,
so you don't need to hardcode any instance ID.

Before running:
1. Make sure you already ran "aws configure" successfully (you did this earlier).
2. Make sure your test instance is tagged: training_status = completed
3. Install boto3 if not already done: pip install boto3
4. Run with: python step3_aws_real_data.py
"""

import boto3
from datetime import datetime, timedelta, timezone

# Reuse the SAME rule engine you already built and tested in step 1
from step1_fake_data_and_rules import detect_anomaly


def get_cpu_usage(instance_id, region="us-east-2"):
    """
    Asks CloudWatch for the average CPU usage of an instance
    over the last 10 minutes. Real instances take a few minutes
    after launch before CloudWatch has any data.
    """
    cloudwatch = boto3.client("cloudwatch", region_name=region)

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=10)

    response = cloudwatch.get_metric_statistics(
        Namespace="AWS/EC2",
        MetricName="CPUUtilization",
        Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
        StartTime=start_time,
        EndTime=end_time,
        Period=300,  # 5-minute chunks
        Statistics=["Average"],
    )

    datapoints = response.get("Datapoints", [])
    if not datapoints:
        # No data yet (instance just launched) - treat as unknown/idle
        return 0.0

    # Take the most recent datapoint
    latest = sorted(datapoints, key=lambda d: d["Timestamp"])[-1]
    return round(latest["Average"], 2)


def get_real_instances(region="us-east-2"):
    """
    Fetches all EC2 instances in your account and shapes them into
    the SAME dictionary format as fake_instances from step1, so our
    existing detect_anomaly() function works without changes.
    """
    ec2 = boto3.client("ec2", region_name=region)
    response = ec2.describe_instances()

    instances = []

    for reservation in response["Reservations"]:
        for inst in reservation["Instances"]:
            instance_id = inst["InstanceId"]
            state = inst["State"]["Name"]  # e.g. "running", "stopped"

            # Read the training_status tag we manually added.
            # If it's missing, default to "unknown" so it won't
            # accidentally trigger a false anomaly.
            tags = {t["Key"]: t["Value"] for t in inst.get("Tags", [])}
            training_status = tags.get("training_status", "unknown")

            cpu = get_cpu_usage(instance_id, region) if state == "running" else 0.0

            # Compute REAL runtime from AWS's LaunchTime, instead of
            # hardcoding 0. This matters for the agent's reflection step:
            # a genuinely "0 hours" instance likely just started and
            # deserves caution, but a real several-hours-old instance
            # showing 0 shouldn't be treated the same way.
            runtime_hours = 0.0
            if state == "running":
                launch_time = inst["LaunchTime"]
                now = datetime.now(timezone.utc)
                runtime_hours = round((now - launch_time).total_seconds() / 3600, 2)

            instances.append(
                {
                    "instance_id": instance_id,
                    "state": state,
                    "cpu_percent": cpu,
                    "training_status": training_status,
                    "runtime_hours": runtime_hours,
                }
            )

    return instances


if __name__ == "__main__":
    print("Fetching real AWS instances...\n")

    real_instances = get_real_instances()

    if not real_instances:
        print("No instances found. Make sure you launched one in us-east-2.")

    for instance in real_instances:
        anomaly = detect_anomaly(instance)

        print(f"Instance: {instance['instance_id']}")
        print(
            f"  State: {instance['state']} | CPU: {instance['cpu_percent']}% | Training: {instance['training_status']}"
        )

        if anomaly:
            print("  ⚠️  ANOMALY DETECTED")
            print(f"     Type: {anomaly['anomaly_type']}")
            print(f"     Root Cause: {anomaly['root_cause']}")
        else:
            print("  ✅ No anomaly")

        print("-" * 50)
