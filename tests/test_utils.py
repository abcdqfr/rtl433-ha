import asyncio
import psutil
import logging
from typing import Optional, List
from asyncio import Task

_LOGGER = logging.getLogger(__name__)

def kill_rtl433_processes():
    """Kill any lingering rtl_433 processes."""
    killed = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if 'rtl_433' in proc.info['name']:
                proc.kill()
                killed.append(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    if killed:
        _LOGGER.debug(f"Killed rtl_433 processes with PIDs: {killed}")

async def cleanup_tasks(tasks: List[Optional[Task]]):
    """Clean up async tasks safely."""
    for task in tasks:
        if task and not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception) as e:
                _LOGGER.debug(f"Task cleanup error: {str(e)}")

async def wait_for_cleanup(timeout: float = 0.1):
    """Wait for a short period to allow cleanup operations."""
    try:
        await asyncio.wait_for(asyncio.sleep(0), timeout=timeout)
    except asyncio.TimeoutError:
        pass 