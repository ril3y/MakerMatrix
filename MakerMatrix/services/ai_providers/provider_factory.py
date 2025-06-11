"""AI Provider Factory"""

import logging
from typing import Dict, Type

from .base_provider import BaseAIProvider, AIProviderNotSupportedError
from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from MakerMatrix.models.ai_config_model import AIConfig

logger = logging.getLogger(__name__)


class AIProviderFactory:
    """Factory for creating AI providers"""
    
    # Registry of available providers
    _providers: Dict[str, Type[BaseAIProvider]] = {
        "ollama": OllamaProvider,
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
    }
    
    @classmethod
    def create_provider(cls, config: AIConfig) -> BaseAIProvider:
        """Create an AI provider instance based on config"""
        provider_name = config.provider.lower()
        
        if provider_name not in cls._providers:
            available_providers = list(cls._providers.keys())
            raise AIProviderNotSupportedError(
                f"Provider '{provider_name}' not supported. "
                f"Available providers: {available_providers}"
            )
        
        provider_class = cls._providers[provider_name]
        
        try:
            return provider_class(config)
        except Exception as e:
            logger.error(f"Failed to create {provider_name} provider: {e}")
            raise
    
    @classmethod
    def get_available_providers(cls) -> Dict[str, Dict[str, any]]:
        """Get information about available providers"""
        return {
            "ollama": {
                "name": "Ollama",
                "description": "Local Ollama server",
                "requires_api_key": False,
                "supports_sql": True,
                "default_url": "http://localhost:11434",
                "models": ["llama3.2:latest", "llama3.1:latest", "codellama:latest"]
            },
            "openai": {
                "name": "OpenAI",
                "description": "OpenAI GPT models",
                "requires_api_key": True,
                "supports_sql": True,
                "default_url": "https://api.openai.com/v1",
                "models": ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"]
            },
            "anthropic": {
                "name": "Anthropic",
                "description": "Anthropic Claude models",
                "requires_api_key": True,
                "supports_sql": True,
                "default_url": "https://api.anthropic.com/v1",
                "models": ["claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"]
            }
        }
    
    @classmethod
    def register_provider(cls, name: str, provider_class: Type[BaseAIProvider]):
        """Register a new provider (for extensions)"""
        cls._providers[name.lower()] = provider_class
        logger.info(f"Registered new AI provider: {name}")
    
    @classmethod
    def get_provider_info(cls, provider_name: str) -> Dict[str, any]:
        """Get information about a specific provider"""
        available = cls.get_available_providers()
        return available.get(provider_name.lower(), {})