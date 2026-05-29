from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from threading import Lock
from typing import Dict


@dataclass
class ProviderUsage:
    tokens: int = 0
    requests: int = 0


@dataclass
class RateLimitTracker:
    """Simple in-memory daily usage tracker.

    This can be replaced by Redis-backed storage in production.
    """

    daily_token_limits: Dict[str, int]
    alert_threshold_ratio: float = 0.9
    _usage: Dict[str, ProviderUsage] = field(default_factory=dict)
    _current_day: date = field(default_factory=date.today)
    _lock: Lock = field(default_factory=Lock)

    def _reset_if_new_day(self) -> None:
        if date.today() != self._current_day:
            self._usage.clear()
            self._current_day = date.today()

    def record(self, provider: str, tokens: int = 0) -> None:
        with self._lock:
            self._reset_if_new_day()
            usage = self._usage.setdefault(provider, ProviderUsage())
            usage.tokens += max(tokens, 0)
            usage.requests += 1

    def can_use(self, provider: str) -> bool:
        with self._lock:
            self._reset_if_new_day()
            limit = self.daily_token_limits.get(provider)
            if not limit:
                return True
            return self._usage.get(provider, ProviderUsage()).tokens < limit

    def nearing_limit(self, provider: str) -> bool:
        with self._lock:
            self._reset_if_new_day()
            limit = self.daily_token_limits.get(provider)
            if not limit:
                return False
            used = self._usage.get(provider, ProviderUsage()).tokens
            return used >= int(limit * self.alert_threshold_ratio)

    def status(self) -> Dict[str, dict]:
        with self._lock:
            self._reset_if_new_day()
            payload: Dict[str, dict] = {}
            for provider, usage in self._usage.items():
                limit = self.daily_token_limits.get(provider)
                payload[provider] = {
                    "tokens": usage.tokens,
                    "requests": usage.requests,
                    "daily_limit": limit,
                    "nearing_limit": self.nearing_limit(provider),
                }
            return payload
