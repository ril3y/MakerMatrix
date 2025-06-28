"""OpenAI AI Provider with LangChain SQL support"""

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
    from langchain_openai import ChatOpenAI
    from langchain_experimental.sql import SQLDatabaseChain
    from langchain_community.utilities.sql_database import SQLDatabase
    from sqlalchemy import create_engine
    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    logger.warning(f"LangChain not available for OpenAI provider: {e}")
    LANGCHAIN_AVAILABLE = False


class OpenAIProvider(BaseAIProvider):
    """OpenAI AI Provider with LangChain SQL Database Chain support"""
    
    def __init__(self, config: AIConfig):
        super().__init__(config)
        self.db_path = DATABASE_URL.replace("sqlite:///", "")
        self._sql_engine = None
        self._sql_database = None
        self._sql_chain = None
        
        # Validate API key
        if not config.api_key:
            raise AIProviderConnectionError("OpenAI API key is required")
    
    def supports_sql_queries(self) -> bool:
        """OpenAI supports SQL queries via LangChain"""
        return LANGCHAIN_AVAILABLE and os.path.exists(self.db_path) and self.config.api_key
    
    async def chat(self, message: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """Send chat message to OpenAI"""
        try:
            # Try LangChain SQL query first if it looks like a database question
            if self.is_database_query(message):
                sql_result = await self.query_database(message)
                if sql_result:
                    return sql_result
            
            # Fallback to regular chat
            return await self._regular_chat(message, conversation_history)
            
        except Exception as e:
            logger.error(f"OpenAI chat error: {e}")
            return {"error": f"OpenAI chat failed: {str(e)}"}
    
    async def _regular_chat(self, message: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """Regular chat without SQL processing"""
        try:
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            }
            
            # Use correct API URL
            api_url = self.config.api_url if self.config.api_url != "http://localhost:11434" else "https://api.openai.com/v1"
            
            # Prepare messages
            messages = []
            
            # Add conversation history
            if conversation_history:
                messages.extend(conversation_history)
            
            # Add current message
            messages.append({
                "role": "user", 
                "content": message
            })
            
            response = requests.post(
                f"{api_url}/chat/completions",
                headers=headers,
                json={
                    "model": self.config.model_name,
                    "messages": messages,
                    "temperature": self.config.temperature,
                    "max_tokens": self.config.max_tokens
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "response": result["choices"][0]["message"]["content"],
                    "model": self.config.model_name,
                    "provider": "openai"
                }
            else:
                return {"error": f"OpenAI API error: {response.status_code} - {response.text}"}
                
        except requests.RequestException as e:
            raise AIProviderConnectionError(f"Failed to connect to OpenAI: {str(e)}")
    
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
                "provider": "openai-langchain",
                "sql_used": True
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
                # Create OpenAI LLM instance
                openai_llm = ChatOpenAI(
                    model=self.config.model_name,
                    api_key=self.config.api_key,
                    base_url=self.config.api_url if self.config.api_url != "http://localhost:11434" else None,
                    temperature=0  # Deterministic for SQL generation
                )
                
                # Get SQL database instance
                sql_db = self._get_sql_database()
                if sql_db:
                    # Create SQL Database Chain
                    self._sql_chain = SQLDatabaseChain.from_llm(
                        llm=openai_llm,
                        db=sql_db,
                        verbose=True,
                        return_intermediate_steps=True,
                        use_query_checker=True,
                        return_sql=True
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
        """Test connection to OpenAI"""
        try:
            headers = {"Authorization": f"Bearer {self.config.api_key}"}
            api_url = self.config.api_url if self.config.api_url != "http://localhost:11434" else "https://api.openai.com/v1"
            
            response = requests.get(f"{api_url}/models", headers=headers, timeout=10)
            if response.status_code == 200:
                models = response.json().get("data", [])
                model_names = [model.get("id", "") for model in models]
                
                # Check SQL support
                sql_support = self.supports_sql_queries()
                
                if self.config.model_name in model_names:
                    return {
                        "success": True,
                        "message": "Successfully connected to OpenAI",
                        "current_model": self.config.model_name,
                        "sql_support": sql_support,
                        "langchain_available": LANGCHAIN_AVAILABLE
                    }
                else:
                    return {
                        "warning": f"Model '{self.config.model_name}' not found",
                        "suggestion": "Check available models in your OpenAI account",
                        "sql_support": sql_support
                    }
            else:
                return {"error": f"OpenAI connection failed: HTTP {response.status_code}"}
                
        except Exception as e:
            raise AIProviderConnectionError(f"OpenAI connection test failed: {str(e)}")