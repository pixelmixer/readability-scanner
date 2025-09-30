"""
Queue manager for handling Celery task submission and monitoring.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from celery.result import AsyncResult
from celery.exceptions import TimeoutError as CeleryTimeoutError

from celery_app.celery_worker import celery_app
from celery_app import tasks

logger = logging.getLogger(__name__)


class QueueManager:
    """
    High-level interface for interacting with Celery queues.
    Provides methods for submitting tasks and monitoring their status.
    """

    def __init__(self):
        self.celery_app = celery_app

    async def queue_manual_refresh(self, source_id: str, source_url: str, wait_for_result: bool = True, timeout: int = 300) -> Dict[str, Any]:
        """
        Queue a high-priority manual source refresh.

        Args:
            source_id: Database ID of the source
            source_url: URL of the RSS source to refresh
            wait_for_result: If True, wait for task completion before returning
            timeout: Maximum seconds to wait for result (default 5 minutes)

        Returns:
            Task result or task info if not waiting
        """
        try:
            logger.info(f"🔄 Queueing manual refresh for source: {source_url}")

            # Submit high-priority task
            task_result = tasks.manual_refresh_source_task.apply_async(
                args=[source_id, source_url],
                queue='high',
                priority=10  # Highest priority
            )

            logger.info(f"📤 Manual refresh queued with task ID: {task_result.id}")

            if wait_for_result:
                try:
                    # Wait for result with timeout
                    result = task_result.get(timeout=timeout)
                    logger.info(f"✅ Manual refresh completed for {source_url}")

                    return {
                        'success': True,
                        'task_id': task_result.id,
                        'result': result,
                        'completed': True,
                        'timestamp': datetime.utcnow().isoformat()
                    }

                except CeleryTimeoutError:
                    logger.warning(f"⏱️ Manual refresh timeout for {source_url} after {timeout}s")
                    return {
                        'success': False,
                        'task_id': task_result.id,
                        'error': f'Task timeout after {timeout} seconds',
                        'completed': False,
                        'timestamp': datetime.utcnow().isoformat()
                    }
            else:
                # Return immediately with task info
                return {
                    'success': True,
                    'task_id': task_result.id,
                    'status': 'queued',
                    'completed': False,
                    'timestamp': datetime.utcnow().isoformat()
                }

        except Exception as exc:
            logger.error(f"💥 Failed to queue manual refresh for {source_url}: {exc}")
            return {
                'success': False,
                'error': str(exc),
                'timestamp': datetime.utcnow().isoformat()
            }

    async def queue_source_scan(self, source_url: str, priority: int = 5) -> Dict[str, Any]:
        """
        Queue a normal-priority source scan.

        Args:
            source_url: URL of the RSS source to scan
            priority: Task priority (1-10, higher = more important)

        Returns:
            Task submission info
        """
        try:
            logger.info(f"📡 Queueing source scan for: {source_url}")

            # Submit normal-priority task
            task_result = tasks.scan_single_source_task.apply_async(
                args=[source_url],
                kwargs={'priority': priority},
                queue='normal',
                priority=priority
            )

            logger.info(f"📤 Source scan queued with task ID: {task_result.id}")

            return {
                'success': True,
                'task_id': task_result.id,
                'source_url': source_url,
                'priority': priority,
                'status': 'queued',
                'timestamp': datetime.utcnow().isoformat()
            }

        except Exception as exc:
            logger.error(f"💥 Failed to queue source scan for {source_url}: {exc}")
            return {
                'success': False,
                'error': str(exc),
                'timestamp': datetime.utcnow().isoformat()
            }

    async def trigger_scheduled_scan(self) -> Dict[str, Any]:
        """
        Trigger the scheduled scan for all sources.
        This replaces the old cron job by distributing scans over time.

        Returns:
            Task submission info
        """
        try:
            logger.info("⏰ Triggering scheduled scan for all sources")

            # Submit low-priority trigger task
            task_result = tasks.scheduled_scan_trigger_task.apply_async(
                queue='low',
                priority=3
            )

            logger.info(f"📤 Scheduled scan trigger queued with task ID: {task_result.id}")

            return {
                'success': True,
                'task_id': task_result.id,
                'status': 'queued',
                'timestamp': datetime.utcnow().isoformat()
            }

        except Exception as exc:
            logger.error(f"💥 Failed to trigger scheduled scan: {exc}")
            return {
                'success': False,
                'error': str(exc),
                'timestamp': datetime.utcnow().isoformat()
            }

    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get the status of a specific task.

        Args:
            task_id: Celery task ID

        Returns:
            Task status information
        """
        try:
            result = AsyncResult(task_id, app=self.celery_app)

            status_info = {
                'task_id': task_id,
                'status': result.status,
                'completed': result.ready(),
                'successful': result.successful() if result.ready() else None,
                'timestamp': datetime.utcnow().isoformat()
            }

            if result.ready():
                if result.successful():
                    status_info['result'] = result.result
                else:
                    status_info['error'] = str(result.info)
            else:
                status_info['info'] = str(result.info) if result.info else None

            return {
                'success': True,
                **status_info
            }

        except Exception as exc:
            logger.error(f"💥 Failed to get task status for {task_id}: {exc}")
            return {
                'success': False,
                'task_id': task_id,
                'error': str(exc),
                'timestamp': datetime.utcnow().isoformat()
            }

    async def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get statistics about queue usage and worker status.

        Returns:
            Queue and worker statistics
        """
        try:
            # Get active tasks
            active_tasks = self.celery_app.control.inspect().active()

            # Get queue lengths (this requires additional Redis queries)
            # For now, return active task counts
            stats = {
                'timestamp': datetime.utcnow().isoformat(),
                'workers': {},
                'total_active_tasks': 0,
                'queues': {
                    'high': {'active': 0, 'description': 'Manual refresh requests'},
                    'normal': {'active': 0, 'description': 'Scheduled source scans'},
                    'low': {'active': 0, 'description': 'Maintenance tasks'}
                }
            }

            if active_tasks:
                for worker_name, tasks in active_tasks.items():
                    stats['workers'][worker_name] = {
                        'active_tasks': len(tasks),
                        'task_details': []
                    }

                    stats['total_active_tasks'] += len(tasks)

                    # Categorize tasks by queue
                    for task in tasks:
                        task_name = task.get('name', '')
                        task_info = {
                            'id': task.get('id', ''),
                            'name': task_name,
                            'args': task.get('args', []),
                            'time_start': task.get('time_start')
                        }

                        stats['workers'][worker_name]['task_details'].append(task_info)

                        # Count by queue based on task routing
                        if 'manual_refresh' in task_name:
                            stats['queues']['high']['active'] += 1
                        elif task_name in ['scan_single_source_task', 'scan_article_task']:
                            stats['queues']['normal']['active'] += 1
                        else:
                            stats['queues']['low']['active'] += 1

            return {
                'success': True,
                **stats
            }

        except Exception as exc:
            logger.error(f"💥 Failed to get queue stats: {exc}")
            return {
                'success': False,
                'error': str(exc),
                'timestamp': datetime.utcnow().isoformat()
            }

    async def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """
        Cancel a pending or running task.

        Args:
            task_id: Celery task ID to cancel

        Returns:
            Cancellation result
        """
        try:
            logger.info(f"🚫 Canceling task: {task_id}")

            # Revoke the task
            self.celery_app.control.revoke(task_id, terminate=True)

            return {
                'success': True,
                'task_id': task_id,
                'action': 'canceled',
                'timestamp': datetime.utcnow().isoformat()
            }

        except Exception as exc:
            logger.error(f"💥 Failed to cancel task {task_id}: {exc}")
            return {
                'success': False,
                'task_id': task_id,
                'error': str(exc),
                'timestamp': datetime.utcnow().isoformat()
            }


# Global queue manager instance
queue_manager = QueueManager()

