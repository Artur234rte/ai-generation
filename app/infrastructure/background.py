import asyncio
import logging
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


class BackgroundTaskManager:
    """Менеджер фоновых задач."""

    def __init__(self, start_tasks: bool = True):
        self._tasks: set[asyncio.Task[Any]] = set()
        self._start_tasks = start_tasks
        self.enqueued: list[Callable[[], Coroutine[Any, Any, Any]]] = []

    def submit(
        self, coro_factory: Callable[[], Coroutine[Any, Any, Any]]
    ) -> asyncio.Task[Any] | None:
        """Добавить фоновую задачу."""
        if self._start_tasks:
            task: asyncio.Task[Any] = asyncio.create_task(coro_factory())
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)
            return task
        self.enqueued.append(coro_factory)
        return None

    async def shutdown(self) -> None:
        """Остановить все задачи."""
        to_cancel = [t for t in self._tasks if isinstance(t, asyncio.Task)]
        for task in to_cancel:
            task.cancel()
        if to_cancel:
            await asyncio.gather(*to_cancel, return_exceptions=True)
        self._tasks.clear()


def maybe_run_background(
    manager: BackgroundTaskManager,
    coro_factory: Callable[[], Coroutine[Any, Any, Any]],
) -> None:
    """Запустить задачу в фоне."""
    try:
        manager.submit(coro_factory)
    except Exception:
        logger.exception("failed_to_submit_background_task")
