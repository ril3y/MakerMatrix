import json
import os
import requests
import sqlite3
from typing import Dict, Any, Optional, List
from MakerMatrix.models.ai_config_model import AIConfig
from MakerMatrix.utils.config import load_ai_config
from MakerMatrix.database.db import DATABASE_URL
import logging

logger = logging.getLogger(__name__)

class AIService:
    """Service for AI interactions with MCP SQLite support"""
    
    def __init__(self):
        self.config: Optional[AIConfig] = None
        self.db_path = DATABASE_URL.replace("sqlite:///", "")
    
    def load_config(self) -> AIConfig:
        """Load AI configuration"""
        if not self.config:
            self.config = load_ai_config()
        return self.config
    
    def is_enabled(self) -> bool:
        """Check if AI is enabled"""
        config = self.load_config()
        return config.enabled
    
    def get_database_schema(self) -> Dict[str, Any]:
        """Get database schema for AI context"""
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
        """Execute a read-only database query safely"""
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
    
    def get_enhanced_system_prompt(self) -> str:
        """Get system prompt with database schema context"""
        config = self.load_config()
        base_prompt = config.system_prompt
        
        schema = self.get_database_schema()
        if not schema:
            return base_prompt
        
        schema_context = f"""

DATABASE SCHEMA CONTEXT:
You have access to a parts inventory database with the following structure:

"""
        
        for table_name, table_info in schema.items():
            schema_context += f"\nTable: {table_name}\n"
            schema_context += "Columns:\n"
            for col in table_info["columns"]:
                pk_marker = " (PRIMARY KEY)" if col["primary_key"] else ""
                nn_marker = " NOT NULL" if col["not_null"] else ""
                schema_context += f"  - {col['name']}: {col['type']}{pk_marker}{nn_marker}\n"
            
            if "sample_data" in table_info and table_info["sample_data"]:
                schema_context += f"Sample data: {table_info['sample_data'][0]}\n"
        
        schema_context += """

QUERY GUIDELINES:
- You can execute SELECT queries to get real-time data
- Use JOIN operations to connect related data
- Always limit results appropriately (use LIMIT clause)
- Common useful queries:
  * Find parts by name/category: SELECT * FROM parts WHERE name LIKE '%keyword%'
  * Check inventory levels: SELECT name, quantity, minimum_quantity FROM parts WHERE quantity < minimum_quantity
  * Find parts by location: SELECT p.*, l.name as location_name FROM parts p JOIN locations l ON p.location_id = l.id
  * Category analysis: SELECT c.name, COUNT(pc.part_id) as part_count FROM categories c LEFT JOIN part_categories pc ON c.id = pc.category_id GROUP BY c.id

When users ask about inventory, always query the database for real-time information.
"""
        
        return base_prompt + schema_context
    
    async def chat_with_ai(self, message: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """Chat with AI using configured provider with database access"""
        if not self.is_enabled():
            return {"error": "AI is disabled"}
        
        config = self.load_config()
        
        try:
            # Prepare messages with system prompt
            messages = [
                {
                    "role": "system",
                    "content": self.get_enhanced_system_prompt()
                }
            ]
            
            # Add conversation history
            if conversation_history:
                messages.extend(conversation_history)
            
            # Add current message
            messages.append({
                "role": "user", 
                "content": message
            })
            
            # Route to appropriate provider
            if config.provider.lower() == "ollama":
                ai_response = await self._chat_ollama(config, messages)
            elif config.provider.lower() == "openai":
                ai_response = await self._chat_openai(config, messages)
            elif config.provider.lower() == "anthropic":
                ai_response = await self._chat_anthropic(config, messages)
            else:
                return {"error": f"Unsupported AI provider: {config.provider}"}
            
            if ai_response.get("error"):
                return ai_response
            
            response_text = ai_response["response"]
            
            # Check if AI wants to query the database
            if "SELECT" in response_text.upper() and "```sql" in response_text.lower():
                response_text = await self._process_sql_queries(response_text)
            
            return {
                "success": True,
                "response": response_text,
                "model": config.model_name,
                "provider": config.provider
            }
                
        except Exception as e:
            logger.error(f"Unexpected AI service error: {e}")
            return {"error": f"AI service error: {str(e)}"}
    
    async def _chat_ollama(self, config: AIConfig, messages: List[Dict]) -> Dict[str, Any]:
        """Chat with Ollama API"""
        try:
            response = requests.post(
                f"{config.api_url}/api/chat",
                json={
                    "model": config.model_name,
                    "messages": messages,
                    "options": {
                        "temperature": config.temperature,
                        "num_predict": config.max_tokens
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "response": result.get("message", {}).get("content", "")
                }
            else:
                return {"error": f"Ollama API error: {response.status_code}"}
                
        except requests.RequestException as e:
            return {"error": f"Failed to connect to Ollama: {str(e)}"}
    
    async def _chat_openai(self, config: AIConfig, messages: List[Dict]) -> Dict[str, Any]:
        """Chat with OpenAI API"""
        if not config.api_key:
            return {"error": "OpenAI API key is required"}
        
        try:
            headers = {
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json"
            }
            
            # OpenAI API uses different URL structure
            api_url = config.api_url if config.api_url != "http://localhost:11434" else "https://api.openai.com/v1"
            
            response = requests.post(
                f"{api_url}/chat/completions",
                headers=headers,
                json={
                    "model": config.model_name,
                    "messages": messages,
                    "temperature": config.temperature,
                    "max_tokens": config.max_tokens
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "response": result["choices"][0]["message"]["content"]
                }
            else:
                return {"error": f"OpenAI API error: {response.status_code} - {response.text}"}
                
        except requests.RequestException as e:
            return {"error": f"Failed to connect to OpenAI: {str(e)}"}
    
    async def _chat_anthropic(self, config: AIConfig, messages: List[Dict]) -> Dict[str, Any]:
        """Chat with Anthropic Claude API"""
        if not config.api_key:
            return {"error": "Anthropic API key is required"}
        
        try:
            headers = {
                "x-api-key": config.api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            
            # Anthropic API uses different URL structure
            api_url = config.api_url if config.api_url != "http://localhost:11434" else "https://api.anthropic.com/v1"
            
            # Convert messages format for Anthropic
            system_prompt = ""
            user_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_prompt = msg["content"]
                else:
                    user_messages.append(msg)
            
            response = requests.post(
                f"{api_url}/messages",
                headers=headers,
                json={
                    "model": config.model_name,
                    "max_tokens": config.max_tokens,
                    "temperature": config.temperature,
                    "system": system_prompt,
                    "messages": user_messages
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "response": result["content"][0]["text"]
                }
            else:
                return {"error": f"Anthropic API error: {response.status_code} - {response.text}"}
                
        except requests.RequestException as e:
            return {"error": f"Failed to connect to Anthropic: {str(e)}"}
    
    async def _process_sql_queries(self, response_text: str) -> str:
        """Process SQL queries found in AI response"""
        try:
            # Extract all SQL code blocks
            import re
            sql_pattern = r'```sql\n(.*?)\n```'
            sql_matches = re.findall(sql_pattern, response_text, re.DOTALL | re.IGNORECASE)
            
            for sql_query in sql_matches:
                sql_query = sql_query.strip()
                if sql_query:
                    # Execute the query
                    query_result = self.execute_safe_query(sql_query)
                    
                    # Replace the SQL block with results
                    if query_result.get("success"):
                        result_text = f"\n\n**Query Result ({query_result['row_count']} rows):**\n```json\n{json.dumps(query_result['data'], indent=2)}\n```"
                    else:
                        result_text = f"\n\n**Query Error:** {query_result.get('error', 'Unknown error')}"
                    
                    # Replace the SQL block with query + results
                    old_block = f"```sql\n{sql_query}\n```"
                    new_block = f"```sql\n{sql_query}\n```{result_text}"
                    response_text = response_text.replace(old_block, new_block)
            
            return response_text
            
        except Exception as e:
            logger.error(f"Error processing SQL queries: {e}")
            return response_text
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to AI service"""
        if not self.is_enabled():
            return {"error": "AI is disabled"}
        
        config = self.load_config()
        
        try:
            if config.provider.lower() == "ollama":
                return await self._test_ollama_connection(config)
            elif config.provider.lower() == "openai":
                return await self._test_openai_connection(config)
            elif config.provider.lower() == "anthropic":
                return await self._test_anthropic_connection(config)
            else:
                return {"error": f"Unsupported provider: {config.provider}"}
                
        except Exception as e:
            return {"error": f"Connection test failed: {str(e)}"}
    
    async def _test_ollama_connection(self, config: AIConfig) -> Dict[str, Any]:
        """Test Ollama connection"""
        try:
            response = requests.get(f"{config.api_url}/api/tags", timeout=10)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [model.get("name", "") for model in models]
                
                if config.model_name in model_names:
                    return {
                        "success": True,
                        "message": f"Successfully connected to Ollama",
                        "available_models": model_names,
                        "current_model": config.model_name
                    }
                else:
                    return {
                        "warning": f"Model '{config.model_name}' not found",
                        "available_models": model_names,
                        "suggestion": f"Try pulling the model: ollama pull {config.model_name}"
                    }
            else:
                return {"error": f"Ollama connection failed: HTTP {response.status_code}"}
        except Exception as e:
            return {"error": f"Ollama connection failed: {str(e)}"}
    
    async def _test_openai_connection(self, config: AIConfig) -> Dict[str, Any]:
        """Test OpenAI connection"""
        if not config.api_key:
            return {"error": "OpenAI API key is required"}
        
        try:
            headers = {"Authorization": f"Bearer {config.api_key}"}
            api_url = config.api_url if config.api_url != "http://localhost:11434" else "https://api.openai.com/v1"
            
            response = requests.get(f"{api_url}/models", headers=headers, timeout=10)
            if response.status_code == 200:
                models = response.json().get("data", [])
                model_names = [model.get("id", "") for model in models]
                
                if config.model_name in model_names:
                    return {
                        "success": True,
                        "message": "Successfully connected to OpenAI",
                        "current_model": config.model_name
                    }
                else:
                    return {
                        "warning": f"Model '{config.model_name}' not found",
                        "suggestion": "Check available models in your OpenAI account"
                    }
            else:
                return {"error": f"OpenAI connection failed: HTTP {response.status_code}"}
        except Exception as e:
            return {"error": f"OpenAI connection failed: {str(e)}"}
    
    async def _test_anthropic_connection(self, config: AIConfig) -> Dict[str, Any]:
        """Test Anthropic connection"""
        if not config.api_key:
            return {"error": "Anthropic API key is required"}
        
        try:
            headers = {
                "x-api-key": config.api_key,
                "anthropic-version": "2023-06-01"
            }
            api_url = config.api_url if config.api_url != "http://localhost:11434" else "https://api.anthropic.com/v1"
            
            # Test with a simple message to verify API key works
            test_response = requests.post(
                f"{api_url}/messages",
                headers=headers,
                json={
                    "model": config.model_name,
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": "Hi"}]
                },
                timeout=10
            )
            
            if test_response.status_code == 200:
                return {
                    "success": True,
                    "message": "Successfully connected to Anthropic",
                    "current_model": config.model_name
                }
            else:
                return {"error": f"Anthropic connection failed: HTTP {test_response.status_code}"}
        except Exception as e:
            return {"error": f"Anthropic connection failed: {str(e)}"}

# Singleton instance
ai_service = AIService()