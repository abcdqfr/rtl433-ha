"""Test cleanup utilities for RTL-433 integration tests."""
import asyncio
import logging
import psutil
from typing import List, Optional, Set
from dataclasses import dataclass, field

_LOGGER = logging.getLogger(__name__)

@dataclass
class CleanupStats:
    """Statistics for cleanup operations."""
    processes_killed: List[int] = field(default_factory=list)
    tasks_cancelled: List[str] = field(default_factory=list)
    cleanup_errors: List[str] = field(default_factory=list)
    cleanup_duration: float = 0.0

class TestCleanup:
    """Cleanup utilities for tests with debugging capabilities."""

    def __init__(self):
        """Initialize cleanup utilities."""
        self.stats = CleanupStats()
        self._start_time: Optional[float] = None

    async def cleanup_processes(self, process_names: Set[str] = None) -> None:
        """Clean up processes with debug tracking."""
        if process_names is None:
            process_names = {"rtl_433"}

        self._start_time = asyncio.get_event_loop().time()
        
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if any(name in proc.info['name'] for name in process_names):
                        proc.kill()
                        self.stats.processes_killed.append(proc.info['pid'])
                        _LOGGER.debug(
                            "Killed process %s (PID: %d)",
                            proc.info['name'],
                            proc.info['pid']
                        )
                except (psutil.NoSuchProcess, psutil.AccessDenied) as err:
                    self.stats.cleanup_errors.append(f"Process cleanup error: {str(err)}")
        finally:
            self.stats.cleanup_duration = asyncio.get_event_loop().time() - self._start_time

    async def cleanup_tasks(self, exclude_tasks: Set[asyncio.Task] = None) -> None:
        """Clean up async tasks with debug tracking."""
        if exclude_tasks is None:
            exclude_tasks = {asyncio.current_task()}

        try:
            tasks = [t for t in asyncio.all_tasks() if t not in exclude_tasks]
            for task in tasks:
                if not task.done():
                    task.cancel()
                    self.stats.tasks_cancelled.append(task.get_name())
                    _LOGGER.debug("Cancelled task: %s", task.get_name())
            
            if tasks:
                await asyncio.wait(tasks, timeout=1)
        except Exception as err:
            self.stats.cleanup_errors.append(f"Task cleanup error: {str(err)}")

    async def wait_for_cleanup(self, timeout: float = 0.1) -> None:
        """Wait for cleanup operations with timeout."""
        try:
            await asyncio.wait_for(asyncio.sleep(0), timeout=timeout)
        except asyncio.TimeoutError:
            _LOGGER.debug("Cleanup wait timeout after %.2f seconds", timeout)

    def get_cleanup_report(self) -> str:
        """Generate a cleanup report for debugging."""
        report = [
            "Cleanup Report:",
            f"Duration: {self.stats.cleanup_duration:.3f}s",
            f"Processes Killed: {len(self.stats.processes_killed)}",
            f"Tasks Cancelled: {len(self.stats.tasks_cancelled)}",
            f"Errors: {len(self.stats.cleanup_errors)}"
        ]

        if self.stats.processes_killed:
            report.append("\nKilled Processes:")
            for pid in self.stats.processes_killed:
                report.append(f"- PID: {pid}")

        if self.stats.tasks_cancelled:
            report.append("\nCancelled Tasks:")
            for task in self.stats.tasks_cancelled:
                report.append(f"- {task}")

        if self.stats.cleanup_errors:
            report.append("\nCleanup Errors:")
            for error in self.stats.cleanup_errors:
                report.append(f"- {error}")

        return "\n".join(report)

# Global cleanup utility instance
cleanup_utility = TestCleanup()

async def cleanup_test_environment() -> None:
    """Clean up the test environment with full debug reporting."""
    await cleanup_utility.cleanup_processes()
    await cleanup_utility.cleanup_tasks()
    await cleanup_utility.wait_for_cleanup()
    _LOGGER.debug(cleanup_utility.get_cleanup_report()) 