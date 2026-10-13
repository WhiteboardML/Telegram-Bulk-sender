import logging
import random
from typing import List, Optional


class SafetyManager:
    """Enforces Telegram rate limits, randomized jitter pacing, human batch breaks, and contact caps."""
    
    def __init__(self, daily_limit: int = 50, min_delay: float = 10.0, max_delay: float = 25.0,
                 batch_pause_interval: int = 15, batch_pause_min: float = 60.0, batch_pause_max: float = 120.0):
        self.daily_limit = max(1, daily_limit)
        self.min_delay = max(1.0, float(min_delay))
        self.max_delay = max(self.min_delay, float(max_delay))
        self.batch_pause_interval = max(0, batch_pause_interval)
        self.batch_pause_min = max(1.0, float(batch_pause_min))
        self.batch_pause_max = max(self.batch_pause_min, float(batch_pause_max))
        self.logger = logging.getLogger(__name__)
        
    def check_daily_limits(self, planned_messages: int) -> bool:
        """Check if planned messages exceed safe daily limits."""
        if planned_messages > self.daily_limit:
            self.logger.warning(
                f"Planned messages ({planned_messages}) exceed safe daily limit ({self.daily_limit})"
            )
            return False
        return True
        
    def get_jitter_delay(self, custom_min: Optional[float] = None, custom_max: Optional[float] = None) -> float:
        """Generate a random human-like delay between min_delay and max_delay (seconds)."""
        lower = max(1.0, custom_min) if custom_min is not None else self.min_delay
        upper = max(lower, custom_max) if custom_max is not None else self.max_delay
        delay = round(random.uniform(lower, upper), 2)
        return delay
        
    def get_safe_delay(self, requested_delay: float) -> float:
        """Ensure message delay respects minimum safety interval."""
        return max(float(requested_delay), self.min_delay)

    def should_take_batch_pause(self, messages_sent: int) -> bool:
        """Check if campaign should pause for a longer break to mimic human behavior."""
        if self.batch_pause_interval > 0 and messages_sent > 0 and (messages_sent % self.batch_pause_interval == 0):
            return True
        return False

    def get_batch_pause_duration(self) -> float:
        """Generate a random batch pause duration (seconds)."""
        return round(random.uniform(self.batch_pause_min, self.batch_pause_max), 1)
        
    def limit_contacts(self, contacts: List) -> List:
        """Truncate contact list if it exceeds the daily limit."""
        if len(contacts) > self.daily_limit:
            self.logger.warning(
                f"Total contacts ({len(contacts)}) exceeds safe daily limit ({self.daily_limit}). "
                f"Limiting to first {self.daily_limit} contacts for safety."
            )
            return contacts[:self.daily_limit]
        return contacts