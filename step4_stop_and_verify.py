"""
STEP 7 + STEP 8: Real Stop Action + Verification
------------------------------------------------------
This adds two functions:
  - stop_instance()    -> actually calls AWS to stop an instance
  - verify_stopped()   -> checks AWS again to confirm it worked

Your IAM user now has ONLY these EC2 permissions:
  - DescribeInstances (read)
  - StopInstances (write - stop only, cannot launch/terminate)

Run this directly to test: python step4_stop_and_verify.py
(It will ask you to confirm before actually stopping anything.)
"""

import boto3
import time


def stop_instance(instance_id, region="us-east-2"):
    """
    Sends a Stop request to AWS for one specific instance.
    Returns the AWS response (mainly useful for logging).
    """
    ec2 = boto3.client("ec2", region_name=region)
    response = ec2.stop_instances(InstanceIds=[instance_id])
    return response


def verify_stopped(instance_id, region="us-east-2", wait_seconds=20):
    """
    Waits a bit, then re-checks AWS to confirm the instance
    actually reached the 'stopped' or 'stopping' state.
    This closes the loop: Act -> Verify.
    """
    ec2 = boto3.client("ec2", region_name=region)

    print(f"Waiting {wait_seconds}s before verifying...")
    time.sleep(wait_seconds)

    response = ec2.describe_instances(InstanceIds=[instance_id])
    state = response["Reservations"][0]["Instances"][0]["State"]["Name"]

    if state in ("stopped", "stopping"):
        return True, state
    else:
        return False, state


if __name__ == "__main__":
    instance_id = input("Enter the Instance ID to stop (e.g. i-074b998100d7f0eee): ").strip()

    confirm = input(f"Type YES to confirm stopping {instance_id}: ").strip()
    if confirm != "YES":
        print("Cancelled. Nothing was stopped.")
        exit()

    print(f"\nSending stop request for {instance_id}...")
    stop_instance(instance_id)
    print("Stop request sent.")

    success, state = verify_stopped(instance_id)

    print("\n--- Verification ---")
    print(f"Current state: {state}")
    if success:
        print("✅ Remediation Successful")
    else:
        print("⚠️ Instance did not stop as expected. Check AWS console manually.")
