"""
User agent rotation for avoiding bot detection.
"""

import random
import logging
from typing import List

from config import settings

logger = logging.getLogger(__name__)


class UserAgentRotator:
    """Manages rotation of user agent strings to avoid bot detection."""

    def __init__(self, user_agents: List[str] = None):
        """
        Initialize user agent rotator.

        Args:
            user_agents: List of user agent strings. Uses config default if None.
        """
        self.user_agents = user_agents or settings.user_agents
        self.current_index = 0
        self.logger = logging.getLogger(__name__)

        if not self.user_agents:
            # Fallback user agents if none provided
            self.user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            ]

        logger.info(f"Initialized user agent rotator with {len(self.user_agents)} agents")

    def get_random_user_agent(self) -> str:
        """Get a random user agent string."""
        return random.choice(self.user_agents)

    def get_next_user_agent(self) -> str:
        """Get the next user agent in rotation."""
        user_agent = self.user_agents[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.user_agents)
        return user_agent

    def get_user_agent_summary(self, user_agent: str, max_length: int = 50) -> str:
        """Get a shortened version of user agent for logging."""
        if len(user_agent) <= max_length:
            return user_agent
        return user_agent[:max_length] + "..."


# Global user agent rotator instance
user_agent_rotator = UserAgentRotator()
