from typing import Final
from time import time, sleep
from statistics import mean
from collections import deque
from dataclasses import dataclass
from typing import Deque

import requests

from src.utils import get_cushioned_cooldown_in_seconds

INTER_REQUEST_COOLDOWN_FIELD: Final[str] = "cooldown_between_each_request"

@dataclass
class AdaptiveRateLimiter:
    window_size: int = 50  # Number of requests to track
    target_response_time: float = 0.5  # Target response time in seconds
    min_delay: float = 0.2  # Minimum delay between requests
    max_delay: float = 5.0  # Maximum delay between requests
    
    def __init__(self):
        self.response_times: Deque[float] = deque(maxlen=self.window_size)
        self.current_delay: float = self.min_delay
        self.error_count: int = 0
        self.last_request_time: float = 0

    def pre_request(self) -> None:
        """Call this before making a request"""
        # Ensure minimum delay between requests
        time_since_last = time() - self.last_request_time
        if time_since_last < self.current_delay:
            sleep(self.current_delay - time_since_last)
        self.last_request_time = time()

    def post_request(self, response: requests.Response | None) -> None:
        """Call this after getting a response"""
        if response is None:
            self._handle_error()
            return

        response_time = response.elapsed.total_seconds()
        self.response_times.append(response_time)
        
        # Adjust delay based on recent response times
        if len(self.response_times) >= self.window_size // 2:
            self._adjust_delay()

    def _handle_error(self) -> None:
        """Handle failed requests by increasing delay"""
        self.error_count += 1
        # Exponential backoff on errors
        self.current_delay = min(
            self.max_delay,
            self.current_delay * (1.5 ** self.error_count)
        )

    def _adjust_delay(self) -> None:
        """Adjust delay based on moving average of response times"""
        avg_response_time = mean(self.response_times)
        
        if avg_response_time > self.target_response_time:
            # Response times too high, increase delay
            self.current_delay = min(
                self.max_delay,
                self.current_delay * 1.2
            )
        elif avg_response_time < self.target_response_time / 2:
            # Response times very good, cautiously decrease delay
            self.current_delay = max(
                self.min_delay,
                self.current_delay * 0.95
            )
            
        # Reset error count on successful adjustments
        self.error_count = max(0, self.error_count - 1)


def get_rate_limits(
    api_type: str,
    *,
    has_secured_cookie: bool = False,
) -> dict[str, int]:
    if has_secured_cookie:
        base_limits = {
            "market_order": {"queries": 50, "minutes": 1},
            "market_search": {"queries": 50, "minutes": 1},
            "market_listing": {"queries": 25, "minutes": 3},
        }
    else:
        base_limits = {
            "market_order": {"queries": 25, "minutes": 5},
            "market_search": {"queries": 25, "minutes": 5},
            "market_listing": {"queries": 25, "minutes": 5},
        }

    limits = base_limits[api_type]

    return {
        "max_num_queries": limits["queries"],
        "cooldown": get_cushioned_cooldown_in_seconds(num_minutes=limits["minutes"]),
        INTER_REQUEST_COOLDOWN_FIELD: 0,
    }
