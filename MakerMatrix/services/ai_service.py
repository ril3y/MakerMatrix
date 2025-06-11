"""Refactored AI Service using modular provider architecture"""

import json
import os
import sqlite3
import logging
from typing import Dict, Any, Optional, List

from MakerMatrix.models.ai_config_model import AIConfig
from MakerMatrix.utils.config import load_ai_config
from MakerMatrix.database.db import DATABASE_URL
from .ai_providers.provider_factory import AIProviderFactory
from .ai_providers.base_provider import BaseAIProvider, AIProviderError

logger = logging.getLogger(__name__)


class IntentClassifier:
    """Classifies user messages into different intents"""
    
    @staticmethod
    def classify_intent(message: str) -> str:
        """Classify the intent of a user message"""
        message_lower = message.lower()
        
        # Database query patterns
        database_patterns = [
            # Inventory queries
            r'how many.*parts',
            r'count.*parts',
            r'total.*parts',
            r'parts.*count',
            r'parts.*in.*database',
            r'inventory.*size',
            
            # Find/search patterns
            r'find.*parts',
            r'search.*parts',
            r'show.*parts',
            r'list.*parts',
            r'get.*parts',
            
            # Location-based queries
            r'parts.*in.*office',
            r'parts.*in.*warehouse',
            r'parts.*in.*lab',
            r'parts.*in.*location',
            r'what.*in.*office',
            r'what.*in.*warehouse',
            
            # Supplier queries
            r'what.*suppliers',
            r'list.*suppliers',
            r'show.*suppliers',
            r'suppliers.*do.*have',
            
            # Location queries
            r'show.*locations',
            r'list.*locations',
            r'what.*locations',
            r'all.*locations',
            
            # Category queries
            r'show.*categories',
            r'list.*categories',
            r'what.*categories',
            
            # Quantity/stock queries
            r'low.*stock',
            r'quantity.*greater',
            r'quantity.*less',
            r'stock.*level',
            
            # General inventory terms
            r'inventory.*status',
            r'stock.*report',
            r'parts.*database'
        ]
        
        # Check for database query patterns
        import re
        for pattern in database_patterns:
            if re.search(pattern, message_lower):
                return "database_query"
        
        # Navigation patterns
        navigation_patterns = [
            r'go to.*',
            r'navigate.*',
            r'open.*page',
            r'show.*page'
        ]
        
        for pattern in navigation_patterns:
            if re.search(pattern, message_lower):
                return "navigation"
        
        # Default to general chat for other messages
        return "general_chat"


class AIService:
    """Modern AI Service with modular provider support and LangChain integration"""
    
    def __init__(self):
        self.config: Optional[AIConfig] = None
        self.provider: Optional[BaseAIProvider] = None
        self.db_path = DATABASE_URL.replace("sqlite:///", "")
        self.intent_classifier = IntentClassifier()
    
    def load_config(self) -> AIConfig:
        """Load AI configuration"""
        if not self.config:
            self.config = load_ai_config()
        return self.config
    
    def is_enabled(self) -> bool:
        """Check if AI is enabled"""
        config = self.load_config()
        return config.enabled
    
    def _get_provider(self) -> BaseAIProvider:
        """Get or create the AI provider instance"""
        if not self.provider:
            config = self.load_config()
            self.provider = AIProviderFactory.create_provider(config)
        return self.provider
    
    def reload_provider(self):
        """Reload the provider (call after config changes)"""
        self.config = None
        self.provider = None
    
    async def chat_with_ai(self, message: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """Chat with AI using intent-based routing"""
        if not self.is_enabled():
            return {"error": "AI is disabled"}
        
        try:
            # Classify the user's intent
            intent = self.intent_classifier.classify_intent(message)
            logger.info(f"Classified intent: {intent} for message: '{message[:50]}...'")
            
            # Route to appropriate handler based on intent
            if intent == "database_query":
                return await self.handle_database_query(message, conversation_history)
            elif intent == "navigation":
                return await self.handle_navigation(message, conversation_history)
            else:  # general_chat
                return await self.handle_general_chat(message, conversation_history)
            
        except AIProviderError as e:
            logger.error(f"AI provider error: {e}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected AI service error: {e}")
            return {"error": f"AI service error: {str(e)}"}
    
    async def handle_database_query(self, message: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """Handle database-related queries using LangChain SQL"""
        try:
            provider = self._get_provider()
            
            # Force use of database query for this intent
            if provider.supports_sql_queries():
                result = await provider.query_database(message)
                if result:
                    result["intent"] = "database_query"
                    result["timestamp"] = json.dumps({"provider": provider.get_provider_name()})
                    return result
            
            # Fallback if SQL queries not supported
            logger.warning("SQL queries not supported, falling back to general chat")
            return await self.handle_general_chat(message, conversation_history)
            
        except Exception as e:
            logger.error(f"Database query error: {e}")
            return {"error": f"Database query failed: {str(e)}"}
    
    async def handle_navigation(self, message: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """Handle navigation requests"""
        # Extract navigation target from message
        message_lower = message.lower()
        
        # Simple navigation routing
        if "parts" in message_lower:
            nav_target = "/parts"
        elif "locations" in message_lower:
            nav_target = "/locations"
        elif "categories" in message_lower:
            nav_target = "/categories"
        elif "settings" in message_lower:
            nav_target = "/settings"
        elif "users" in message_lower:
            nav_target = "/users"
        else:
            nav_target = "/"
        
        return {
            "success": True,
            "response": f"Navigating to {nav_target}",
            "intent": "navigation",
            "navigation_target": nav_target,
            "provider": "navigation_handler"
        }
    
    async def handle_general_chat(self, message: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """Handle general chat using the AI provider"""
        try:
            provider = self._get_provider()
            result = await provider.chat(message, conversation_history)
            
            # Add metadata
            result["intent"] = "general_chat"
            result["timestamp"] = json.dumps({"provider": provider.get_provider_name()})
            
            return result
            
        except Exception as e:
            logger.error(f"General chat error: {e}")
            return {"error": f"General chat failed: {str(e)}"}
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to the configured AI provider"""
        if not self.is_enabled():
            return {"error": "AI is disabled"}
        
        try:
            provider = self._get_provider()
            return await provider.test_connection()
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return {"error": f"Connection test failed: {str(e)}"}
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about the current provider"""
        config = self.load_config()
        return AIProviderFactory.get_provider_info(config.provider)
    
    def get_available_providers(self) -> Dict[str, Dict[str, any]]:
        """Get information about all available providers"""
        return AIProviderFactory.get_available_providers()
    
    def supports_sql_queries(self) -> bool:
        """Check if current provider supports SQL queries"""
        if not self.is_enabled():
            return False
        try:
            provider = self._get_provider()
            return provider.supports_sql_queries()
        except:
            return False
    
    # Legacy methods for backward compatibility
    def get_database_schema(self) -> Dict[str, Any]:
        """Get database schema for AI context (legacy method)"""
        if not os.path.exists(self.db_path):
            return {}
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = cursor.fetchall()
            
            schema = {}
            for (table_name,) in tables:
                # Get column info for each table
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                
                schema[table_name] = {
                    "columns": [
                        {
                            "name": col[1],
                            "type": col[2],
                            "not_null": bool(col[3]),
                            "primary_key": bool(col[5])
                        }
                        for col in columns
                    ]
                }
                
                # Get sample data (first 3 rows)
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                sample_data = cursor.fetchall()
                if sample_data:
                    column_names = [desc[0] for desc in cursor.description]
                    schema[table_name]["sample_data"] = [
                        dict(zip(column_names, row)) for row in sample_data
                    ]
            
            conn.close()
            return schema
            
        except Exception as e:
            logger.error(f"Error getting database schema: {e}")
            return {}
    
    def execute_safe_query(self, query: str) -> Dict[str, Any]:
        """Execute a read-only database query safely (legacy method)"""
        if not os.path.exists(self.db_path):
            return {"error": "Database not found"}
        
        # Basic safety checks
        query_lower = query.lower().strip()
        if any(dangerous in query_lower for dangerous in ['insert', 'update', 'delete', 'drop', 'alter', 'create']):
            return {"error": "Only SELECT queries are allowed"}
        
        if not query_lower.startswith('select'):
            return {"error": "Query must start with SELECT"}
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # This enables column access by name
            cursor = conn.cursor()
            
            # Set query timeout and limits
            cursor.execute("PRAGMA query_only = ON")  # Read-only mode
            cursor.execute(query)
            
            rows = cursor.fetchall()
            
            # Convert to list of dictionaries
            result = [dict(row) for row in rows]
            
            conn.close()
            
            return {
                "success": True,
                "data": result,
                "row_count": len(result)
            }
            
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return {"error": str(e)}


# Singleton instance
ai_service = AIService()