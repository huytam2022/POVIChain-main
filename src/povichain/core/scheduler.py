import heapq
from typing import Callable, Dict, List, Optional

from .clock import Clock
from .event import Event, EventKind


Handler = Callable[[Event], None]


class Scheduler:
    def __init__(self, clock: Clock) -> None:
        self._clock = clock
        self._heap: List[Event] = []
        self._sequence: int = 0
        self._handlers: Dict[EventKind, List[Handler]] = {k: [] for k in EventKind}
        self._pending: int = 0
        self._max_time_ms: Optional[float] = None

    def schedule(
        self,
        delay_ms: float,
        kind: EventKind,
        payload: Optional[Dict] = None,
        priority: int = 0,
    ) -> Event:
        if delay_ms < 0:
            raise ValueError("negative_delay")
        at = self._clock.now_ms() + delay_ms
        evt = Event(
            time_ms=at,
            priority=priority,
            sequence=self._sequence,
            kind=kind,
            payload=payload or {},
        )
        self._sequence += 1
        heapq.heappush(self._heap, evt)
        self._pending += 1
        return evt

    def register(self, kind: EventKind, handler: Handler) -> None:
        self._handlers[kind].append(handler)

    def set_time_limit(self, max_time_ms: float) -> None:
        self._max_time_ms = max_time_ms

    def run(self) -> int:
        processed = 0
        while self._heap:
            top = self._heap[0]
            if self._max_time_ms is not None and top.time_ms > self._max_time_ms:
                break
            evt = heapq.heappop(self._heap)
            self._pending -= 1
            self._clock.advance_to(evt.time_ms)
            for h in self._handlers[evt.kind]:
                h(evt)
            processed += 1
        return processed

    def pending(self) -> int:
        return self._pending
