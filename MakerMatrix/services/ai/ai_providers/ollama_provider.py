"""Ollama AI Provider with LangChain SQL support"""

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
    from langchain_ollama import OllamaLLM
    from langchain_experimental.sql import SQLDatabaseChain
    from langchain_community.utilities.sql_database import SQLDatabase
    from sqlalchemy import create_engine
    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    logger.warning(f"LangChain not available for Ollama provider: {e}")
    LANGCHAIN_AVAILABLE = False


class OllamaProvider(BaseAIProvider):
    """Ollama AI Provider with LangChain SQL Database Chain support"""
    
    def __init__(self, config: AIConfig):
        super().__init__(config)
        self.db_path = DATABASE_URL.replace("sqlite:///", "")
        self._sql_engine = None
        self._sql_database = None
        self._sql_chain = None
    
    def supports_sql_queries(self) -> bool:
        """Ollama supports SQL queries via LangChain"""
        return LANGCHAIN_AVAILABLE and os.path.exists(self.db_path)
    
    async def chat(self, message: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """Send chat message to Ollama"""
        try:
            # Try LangChain SQL query first if it looks like a database question
            if self.is_database_query(message):
                sql_result = await self.query_database(message)
                if sql_result:
                    return sql_result
            
            # Fallback to regular chat
            return await self._regular_chat(message, conversation_history)
            
        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            return {"error": f"Ollama chat failed: {str(e)}"}
    
    async def _regular_chat(self, message: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """Regular chat without SQL processing"""
        try:
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
                f"{self.config.api_url}/api/chat",
                json={
                    "model": self.config.model_name,
                    "messages": messages,
                    "options": {
                        "temperature": self.config.temperature,
                        "num_predict": self.config.max_tokens
                    },
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "response": result.get("message", {}).get("content", ""),
                    "model": self.config.model_name,
                    "provider": "ollama"
                }
            else:
                return {"error": f"Ollama API error: {response.status_code}"}
                
        except requests.RequestException as e:
            raise AIProviderConnectionError(f"Failed to connect to Ollama: {str(e)}")
    
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
            
            # Get SQL database for execution
            sql_db = self._get_sql_database()
            if not sql_db:
                logger.warning("SQL database not available")
                return None
            
            # Generate SQL query using the chain
            sql_query = sql_chain.invoke({"question": message})
            
            # Clean up the SQL query (remove any extra text)
            if isinstance(sql_query, str):
                # Extract just the SQL if there's extra text
                lines = sql_query.strip().split('\n')
                sql_query = lines[-1] if lines else sql_query
                sql_query = sql_query.strip()
                
                # Remove common prefixes that might be added
                if sql_query.lower().startswith('sql query:'):
                    sql_query = sql_query[10:].strip()
                elif sql_query.lower().startswith('query:'):
                    sql_query = sql_query[6:].strip()
            
            logger.info(f"Generated SQL: {sql_query}")
            
            # Execute the SQL query
            try:
                query_result = sql_db.run(sql_query)
                
                # Create a natural language response from the SQL results
                if query_result:
                    # Create context for the LLM to generate a natural response
                    context = f"""Based on the SQL query: {sql_query}
Results: {query_result}

Question: {message}"""
                    
                    # Use the LLM to create a natural language response
                    from langchain_ollama import OllamaLLM
                    response_llm = OllamaLLM(
                        model=self.config.model_name,
                        base_url=self.config.api_url,
                        temperature=0.3
                    )
                    
                    response_prompt = f"""You are a helpful database assistant. Based on the SQL query results below, provide a clear, natural language answer to the user's question.

{context}

Provide a helpful response based on the data:"""
                    
                    natural_response = response_llm.invoke(response_prompt)
                    
                    return {
                        "success": True,
                        "response": natural_response,
                        "model": self.config.model_name,
                        "provider": "ollama-langchain",
                        "sql_used": True,
                        "sql_query": sql_query,
                        "raw_results": query_result
                    }
                else:
                    return {
                        "success": True,
                        "response": "No results found for your query.",
                        "model": self.config.model_name,
                        "provider": "ollama-langchain",
                        "sql_used": True,
                        "sql_query": sql_query
                    }
                    
            except Exception as exec_error:
                logger.error(f"SQL execution failed: {exec_error}")
                return {
                    "success": False,
                    "response": f"Error executing SQL query: {str(exec_error)}",
                    "model": self.config.model_name,
                    "provider": "ollama-langchain",
                    "sql_used": True,
                    "sql_query": sql_query
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
                # Create Ollama LLM instance
                ollama_llm = OllamaLLM(
                    model=self.config.model_name,
                    base_url=self.config.api_url,
                    temperature=0  # Deterministic for SQL generation
                )
                
                # Get SQL database instance
                sql_db = self._get_sql_database()
                if sql_db:
                    # Import required classes for latest LangChain pattern
                    from langchain.chains import create_sql_query_chain
                    from langchain_core.prompts import PromptTemplate
                    
                    # Domain-specific prefix exactly as shown in user's example
                    domain_prefix = """You are a database assistant for an inventory management system.

When the user mentions locations like "office", "warehouse", or "lab", 
they are referring to storage locations in the database (locationmodel table).
They are NOT talking about TV shows, movies, or physical buildings outside this inventory system.

IMPORTANT SCHEMA NOTES:
- Parts are stored in the 'partmodel' table
- Locations are stored in the 'locationmodel' table  
- Parts reference locations via 'location_id' (foreign key to locationmodel.id)
- To find parts in a location, JOIN partmodel.location_id = locationmodel.id
- Location names are stored in locationmodel.name column

Always query the database for actual inventory data and answer based strictly on the SQL results."""
                    
                    # Create custom prompt with domain context
                    custom_prompt = PromptTemplate(
                        input_variables=["input", "table_info", "top_k"],
                        template=f"""{domain_prefix}

You have access to a SQLite database with the following schema:
{{table_info}}

CRITICAL: When users ask about parts in locations, you MUST JOIN the tables correctly:
- Parts table: partmodel (columns: id, part_number, part_name, description, quantity, supplier, location_id, image_url, additional_properties)
- Locations table: locationmodel (columns: id, name, description, parent_id, location_type)
- To find parts in "office": JOIN partmodel p JOIN locationmodel l ON p.location_id = l.id WHERE l.name = 'Office'

EXAMPLES:
- "parts in office" → SELECT p.* FROM partmodel p JOIN locationmodel l ON p.location_id = l.id WHERE l.name = 'Office'
- "parts in warehouse" → SELECT p.* FROM partmodel p JOIN locationmodel l ON p.location_id = l.id WHERE l.name = 'warehouse'

Given the user question below, create a syntactically correct SQLite query to run.
Only return the SQL query, nothing else.
Look at at most {{top_k}} results unless the user specifies otherwise.

Question: {{input}}
SQL Query:"""
                    )
                    
                    # Create SQL query chain with custom prompt
                    self._sql_chain = create_sql_query_chain(
                        llm=ollama_llm,
                        db=sql_db,
                        prompt=custom_prompt
                    )
                    
                    logger.info("Successfully created SQL chain with domain-specific prompt")
                
            except Exception as e:
                logger.error(f"Error creating SQL chain: {e}")
                # Fallback to old method if new pattern fails
                try:
                    from langchain_experimental.sql import SQLDatabaseChain
                    self._sql_chain = SQLDatabaseChain.from_llm(
                        ollama_llm,
                        sql_db,
                        verbose=True,
                        return_intermediate_steps=True
                    )
                    logger.info("Created SQL chain using fallback method")
                except Exception as fallback_error:
                    logger.error(f"Fallback SQL chain creation failed: {fallback_error}")
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
    
    def _get_schema_context(self) -> str:
        """Get formatted database schema context"""
        if not os.path.exists(self.db_path):
            return "No database found."
        
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = cursor.fetchall()
            
            schema_text = ""
            for (table_name,) in tables:
                # Get column info for each table
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                
                schema_text += f"\nTable: {table_name}\n"
                schema_text += "Columns:\n"
                for col in columns:
                    col_name, col_type, not_null, default, pk = col[1], col[2], col[3], col[4], col[5]
                    pk_marker = " (PRIMARY KEY)" if pk else ""
                    nn_marker = " NOT NULL" if not_null else ""
                    schema_text += f"  - {col_name}: {col_type}{pk_marker}{nn_marker}\n"
                
                # Get sample data (first 2 rows)
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 2")
                sample_data = cursor.fetchall()
                if sample_data:
                    column_names = [desc[0] for desc in cursor.description]
                    schema_text += f"Sample data:\n"
                    for row in sample_data:
                        row_dict = dict(zip(column_names, row))
                        # Truncate long values
                        for k, v in row_dict.items():
                            if isinstance(v, str) and len(v) > 50:
                                row_dict[k] = v[:47] + "..."
                        schema_text += f"  {row_dict}\n"
                schema_text += "\n"
            
            conn.close()
            return schema_text
            
        except Exception as e:
            return f"Error getting schema: {e}"
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to Ollama"""
        try:
            response = requests.get(f"{self.config.api_url}/api/tags", timeout=10)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [model.get("name", "") for model in models]
                
                # Check SQL support
                sql_support = self.supports_sql_queries()
                
                if self.config.model_name in model_names:
                    return {
                        "success": True,
                        "message": "Successfully connected to Ollama",
                        "available_models": model_names,
                        "current_model": self.config.model_name,
                        "sql_support": sql_support,
                        "langchain_available": LANGCHAIN_AVAILABLE
                    }
                else:
                    return {
                        "warning": f"Model '{self.config.model_name}' not found",
                        "available_models": model_names,
                        "suggestion": f"Try pulling the model: ollama pull {self.config.model_name}",
                        "sql_support": sql_support
                    }
            else:
                return {"error": f"Ollama connection failed: HTTP {response.status_code}"}
                
        except Exception as e:
            raise AIProviderConnectionError(f"Ollama connection test failed: {str(e)}")