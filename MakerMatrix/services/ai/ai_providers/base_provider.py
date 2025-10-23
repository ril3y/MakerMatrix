"""Base AI Provider Interface"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from MakerMatrix.models.ai_config_model import AIConfig


class BaseAIProvider(ABC):
    """Abstract base class for AI providers"""

    def __init__(self, config: AIConfig):
        self.config = config
        self.sql_chain = None

    @abstractmethod
    async def chat(self, message: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """Send a chat message to the AI provider"""
        pass

    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to the AI provider"""
        pass

    @abstractmethod
    def supports_sql_queries(self) -> bool:
        """Check if this provider supports SQL database queries via LangChain"""
        pass

    @abstractmethod
    async def query_database(self, message: str) -> Optional[Dict[str, Any]]:
        """Query database using natural language (if supported)"""
        pass

    def is_database_query(self, message: str) -> bool:
        """Check if a message looks like a database query"""
        query_keywords = [
            "how many",
            "find",
            "search",
            "list",
            "show",
            "count",
            "what",
            "where",
            "inventory",
            "parts",
            "categories",
            "locations",
            "stock",
            "quantity",
            "total",
        ]
        return any(keyword.lower() in message.lower() for keyword in query_keywords)

    def get_provider_name(self) -> str:
        """Get the provider name"""
        return self.config.provider


class AIProviderError(Exception):
    """Exception raised by AI providers"""

    pass


class AIProviderConnectionError(AIProviderError):
    """Exception raised when connection to AI provider fails"""

    pass


class AIProviderNotSupportedError(AIProviderError):
    """Exception raised when AI provider is not supported"""

    pass
