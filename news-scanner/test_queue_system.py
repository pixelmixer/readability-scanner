#!/usr/bin/env python3
"""
Test script to validate the Celery queue system implementation.
Run this after starting the Docker services to verify everything works.
"""

import asyncio
import requests
import json
import time
from typing import Dict, Any

# Service endpoints
BASE_URL = "http://localhost:4913"
FLOWER_URL = "http://localhost:5555"

async def test_queue_system():
    """Test the complete queue system functionality."""

    print("🧪 Testing Celery Queue System Implementation")
    print("=" * 60)

    # Test 1: Check service health
    print("\n1. Testing Service Health...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        health_data = response.json()

        print(f"   Status: {health_data.get('status', 'unknown')}")
        print(f"   Database: {health_data.get('database', 'unknown')}")
        print(f"   Celery: {health_data.get('celery', {}).get('status', 'unknown')}")
        print(f"   Active Tasks: {health_data.get('celery', {}).get('active_tasks', 0)}")

        if health_data.get('status') == 'healthy':
            print("   ✅ Service is healthy")
        else:
            print("   ⚠️  Service has issues")

    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
        return False

    # Test 2: Check queue status
    print("\n2. Testing Queue Status...")
    try:
        response = requests.get(f"{BASE_URL}/sources/queue/status", timeout=10)
        queue_data = response.json()

        if queue_data.get('success'):
            print("   ✅ Queue system is accessible")
            print(f"   Total active tasks: {queue_data.get('total_active_tasks', 0)}")

            queues = queue_data.get('queues', {})
            for queue_name, queue_info in queues.items():
                print(f"   {queue_name.upper()} queue: {queue_info.get('active', 0)} active tasks")
        else:
            print(f"   ❌ Queue status error: {queue_data.get('error')}")

    except Exception as e:
        print(f"   ❌ Queue status check failed: {e}")

    # Test 3: Check Flower dashboard
    print("\n3. Testing Flower Dashboard...")
    try:
        response = requests.get(f"{FLOWER_URL}/api/workers", timeout=5)
        if response.status_code == 200:
            workers = response.json()
            print(f"   ✅ Flower accessible, {len(workers)} workers detected")
            for worker_name, worker_info in workers.items():
                status = worker_info.get('status', 'unknown')
                print(f"   Worker {worker_name}: {status}")
        else:
            print(f"   ⚠️  Flower returned status {response.status_code}")

    except Exception as e:
        print(f"   ⚠️  Flower not accessible: {e}")
        print("   (This is optional for queue functionality)")

    # Test 4: Test manual trigger
    print("\n4. Testing Manual Scan Trigger...")
    try:
        response = requests.post(f"{BASE_URL}/sources/queue/trigger-scan", timeout=30)
        trigger_data = response.json()

        if trigger_data.get('success'):
            task_id = trigger_data.get('task_id')
            print(f"   ✅ Scheduled scan triggered successfully")
            print(f"   Task ID: {task_id}")

            # Monitor task status
            print("   Monitoring task progress...")
            for i in range(10):  # Check for up to 50 seconds
                time.sleep(5)
                status_response = requests.get(f"{BASE_URL}/sources/queue/task/{task_id}")
                status_data = status_response.json()

                if status_data.get('success'):
                    task_status = status_data.get('status')
                    completed = status_data.get('completed', False)

                    print(f"   Status: {task_status}, Completed: {completed}")

                    if completed:
                        if status_data.get('successful'):
                            result = status_data.get('result', {})
                            sources_queued = result.get('sources_queued', 0)
                            print(f"   ✅ Task completed successfully, {sources_queued} sources queued")
                        else:
                            print(f"   ❌ Task failed: {status_data.get('error')}")
                        break
                else:
                    print(f"   ⚠️  Could not get task status: {status_data.get('error')}")
                    break
            else:
                print("   ⏱️  Task still running after 50 seconds (this is normal)")

        else:
            print(f"   ❌ Failed to trigger scan: {trigger_data.get('error')}")

    except Exception as e:
        print(f"   ❌ Manual trigger test failed: {e}")

    # Test 5: Check final queue status
    print("\n5. Final Queue Status Check...")
    try:
        response = requests.get(f"{BASE_URL}/sources/queue/status", timeout=10)
        queue_data = response.json()

        if queue_data.get('success'):
            total_active = queue_data.get('total_active_tasks', 0)
            queues = queue_data.get('queues', {})

            print(f"   Total active tasks: {total_active}")
            for queue_name, queue_info in queues.items():
                active = queue_info.get('active', 0)
                description = queue_info.get('description', '')
                print(f"   {queue_name.upper()}: {active} active ({description})")

            if total_active > 0:
                print("   ✅ Queue system is processing tasks")
            else:
                print("   ℹ️  No active tasks (queue system ready)")
        else:
            print(f"   ❌ Queue status error: {queue_data.get('error')}")

    except Exception as e:
        print(f"   ❌ Final queue check failed: {e}")

    print("\n" + "=" * 60)
    print("🎉 Queue System Test Completed!")
    print("\n📋 Next Steps:")
    print("   1. Check logs: docker-compose logs celery-worker")
    print("   2. Monitor queues: docker-compose logs celery-beat")
    print("   3. View dashboard: http://localhost:5555")
    print("   4. Test manual refresh from the web UI")
    print("   5. Monitor system performance during scheduled scans")

    return True


if __name__ == "__main__":
    print("🚀 Starting Queue System Test")
    print("Make sure Docker services are running:")
    print("   docker-compose up -d")
    print("\nWaiting 5 seconds for services to be ready...")
    time.sleep(5)

    try:
        asyncio.run(test_queue_system())
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")

