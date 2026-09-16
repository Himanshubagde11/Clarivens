"""
Job queue abstractions for Clarivens asynchronous data processing.
Supports in-memory queue for development and Azure Service Bus for production.
"""
import json
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from backend.config import settings

logger = logging.getLogger(__name__)

class MemoryJobQueue:
    """Lightweight in-memory queue suitable for single-instance / local execution."""
    def __init__(self):
        self._queue = asyncio.Queue()

    async def enqueue(self, job_payload: Dict[str, Any]):
        await self._queue.put(job_payload)
        logger.info(f"[JobQueue] Enqueued job: {job_payload.get('job_id')}")

    async def dequeue(self) -> Dict[str, Any]:
        return await self._queue.get()


class AzureServiceBusQueue:
    """Production job queue integration with Azure Service Bus."""
    def __init__(self, connection_str: str, queue_name: str):
        self.connection_str = connection_str
        self.queue_name = queue_name
        self.client = None

        if connection_str:
            try:
                from azure.servicebus import ServiceBusClient
                self.client = ServiceBusClient.from_connection_string(connection_str)
            except ImportError:
                logger.warning("[JobQueue] azure-servicebus package not installed.")

    async def enqueue(self, job_payload: Dict[str, Any]):
        if not self.client:
            logger.warning("[JobQueue] Service Bus client unavailable; job was dropped.")
            return

        from azure.servicebus import ServiceBusMessage
        with self.client.get_queue_sender(self.queue_name) as sender:
            msg = ServiceBusMessage(json.dumps(job_payload))
            sender.send_messages(msg)
            logger.info(f"[JobQueue] Sent job {job_payload.get('job_id')} to Azure Service Bus")


# Singleton instance
_queue_instance = None

def get_job_queue():
    global _queue_instance
    if _queue_instance is None:
        if settings.job_backend == "azure_service_bus" and settings.azure_service_bus_connection:
            _queue_instance = AzureServiceBusQueue(
                connection_str=settings.azure_service_bus_connection,
                queue_name=settings.azure_service_bus_queue
            )
        else:
            _queue_instance = MemoryJobQueue()
    return _queue_instance
