"""Anthropic Claude AI Provider with LangChain SQL support"""

import os
import requests
import logging
from typing import Dict, Any, Optional, List

from .base_provider import BaseAIProvider, AIProviderConnectionError
from MakerMatrix.models.ai_config_model import AIConfig
from MakerMatrix.database.db import DATABASE_URL

logger = logging.getLogger(__name__)

# LangChain imports with fallback
try:
    from langchain_anthropic import ChatAnthropic
    from langchain_experimental.sql import SQLDatabaseChain
    from langchain_community.utilities.sql_database import SQLDatabase
    from sqlalchemy import create_engine

    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    logger.warning(f"LangChain not available for Anthropic provider: {e}")
    LANGCHAIN_AVAILABLE = False


class AnthropicProvider(BaseAIProvider):
    """Anthropic Claude AI Provider with LangChain SQL Database Chain support"""

    def __init__(self, config: AIConfig):
        super().__init__(config)
        self.db_path = DATABASE_URL.replace("sqlite:///", "")
        self._sql_engine = None
        self._sql_database = None
        self._sql_chain = None

        # Validate API key
        if not config.api_key:
            raise AIProviderConnectionError("Anthropic API key is required")

    def supports_sql_queries(self) -> bool:
        """Anthropic supports SQL queries via LangChain"""
        return LANGCHAIN_AVAILABLE and os.path.exists(self.db_path) and self.config.api_key

    async def chat(self, message: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """Send chat message to Anthropic"""
        try:
            # Try LangChain SQL query first if it looks like a database question
            if self.is_database_query(message):
                sql_result = await self.query_database(message)
                if sql_result:
                    return sql_result

            # Fallback to regular chat
            return await self._regular_chat(message, conversation_history)

        except Exception as e:
            logger.error(f"Anthropic chat error: {e}")
            return {"error": f"Anthropic chat failed: {str(e)}"}

    async def _regular_chat(self, message: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """Regular chat without SQL processing"""
        try:
            headers = {
                "x-api-key": self.config.api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01",
            }

            # Use correct API URL
            api_url = (
                self.config.api_url
                if self.config.api_url != "http://localhost:11434"
                else "https://api.anthropic.com/v1"
            )

            # Convert messages format for Anthropic
            system_prompt = ""
            user_messages = []

            # Add conversation history
            if conversation_history:
                for msg in conversation_history:
                    if msg["role"] == "system":
                        system_prompt = msg["content"]
                    else:
                        user_messages.append(msg)

            # Add current message
            user_messages.append({"role": "user", "content": message})

            response = requests.post(
                f"{api_url}/messages",
                headers=headers,
                json={
                    "model": self.config.model_name,
                    "max_tokens": self.config.max_tokens,
                    "temperature": self.config.temperature,
                    "system": system_prompt,
                    "messages": user_messages,
                },
                timeout=30,
            )

            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "response": result["content"][0]["text"],
                    "model": self.config.model_name,
                    "provider": "anthropic",
                }
            else:
                return {"error": f"Anthropic API error: {response.status_code} - {response.text}"}

        except requests.RequestException as e:
            raise AIProviderConnectionError(f"Failed to connect to Anthropic: {str(e)}")

    async def query_database(self, message: str) -> Optional[Dict[str, Any]]:
        """Query database using LangChain SQL Database Chain"""
        if not self.supports_sql_queries():
            return None

        try:
            # Get or create SQL chain
            sql_chain = self._get_sql_chain()
            if not sql_chain:
                logger.warning("SQL chain not available")
                return None

            # Run the chain
            result = sql_chain.invoke({"query": message})

            # Return formatted result
            return {
                "success": True,
                "response": result.get("result", str(result)),
                "model": self.config.model_name,
                "provider": "anthropic-langchain",
                "sql_used": True,
            }

        except Exception as e:
            logger.error(f"LangChain SQL query failed: {e}")
            return None

    def _get_sql_chain(self):
        """Get or create LangChain SQL Database Chain"""
        if not LANGCHAIN_AVAILABLE:
            return None

        if not self._sql_chain:
            try:
                # Create Anthropic LLM instance
                anthropic_llm = ChatAnthropic(
                    model=self.config.model_name,
                    api_key=self.config.api_key,
                    base_url=self.config.api_url if self.config.api_url != "http://localhost:11434" else None,
                    temperature=0,  # Deterministic for SQL generation
                )

                # Get SQL database instance
                sql_db = self._get_sql_database()
                if sql_db:
                    # Create SQL Database Chain
                    self._sql_chain = SQLDatabaseChain.from_llm(
                        llm=anthropic_llm,
                        db=sql_db,
                        verbose=True,
                        return_intermediate_steps=True,
                        use_query_checker=True,
                        return_sql=True,
                    )

            except Exception as e:
                logger.error(f"Error creating SQL chain: {e}")
                self._sql_chain = None

        return self._sql_chain

    def _get_sql_database(self):
        """Get or create LangChain SQLDatabase instance"""
        if not self._sql_database:
            engine = self._get_sql_engine()
            if engine:
                self._sql_database = SQLDatabase(engine)
        return self._sql_database

    def _get_sql_engine(self):
        """Get or create SQLAlchemy engine"""
        if not self._sql_engine and os.path.exists(self.db_path):
            self._sql_engine = create_engine(DATABASE_URL, echo=False)
        return self._sql_engine

    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to Anthropic"""
        try:
            headers = {"x-api-key": self.config.api_key, "anthropic-version": "2023-06-01"}
            api_url = (
                self.config.api_url
                if self.config.api_url != "http://localhost:11434"
                else "https://api.anthropic.com/v1"
            )

            # Test with a simple message to verify API key works
            test_response = requests.post(
                f"{api_url}/messages",
                headers=headers,
                json={
                    "model": self.config.model_name,
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": "Hi"}],
                },
                timeout=10,
            )

            # Check SQL support
            sql_support = self.supports_sql_queries()

            if test_response.status_code == 200:
                return {
                    "success": True,
                    "message": "Successfully connected to Anthropic",
                    "current_model": self.config.model_name,
                    "sql_support": sql_support,
                    "langchain_available": LANGCHAIN_AVAILABLE,
                }
            else:
                return {"error": f"Anthropic connection failed: HTTP {test_response.status_code}"}

        except Exception as e:
            raise AIProviderConnectionError(f"Anthropic connection test failed: {str(e)}")
