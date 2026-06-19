class Clock:
    def __init__(self) -> None:
        self._now_ms: float = 0.0

    def now_ms(self) -> float:
        return self._now_ms

    def advance_to(self, target_ms: float) -> None:
        if target_ms < self._now_ms:
            raise ValueError("clock_non_monotonic")
        self._now_ms = target_ms

    def reset(self) -> None:
        self._now_ms = 0.0
