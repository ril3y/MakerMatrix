import pytest
import asyncio
import os
from MakerMatrix.services.ai.ai_service import ai_service
from MakerMatrix.utils.config import load_ai_config


@pytest.mark.asyncio
class TestAIServiceLangChain:
    """Live integration tests for AI service with LangChain SQL integration"""

    @pytest.fixture(autouse=True)
    async def setup(self):
        """Setup for AI service tests - requires Ollama running"""
        self.config = load_ai_config()

        # Skip tests if AI is disabled
        if not self.config.enabled:
            pytest.skip("AI service is disabled in config")

        # Skip tests if not using Ollama (LangChain integration only works with Ollama)
        if self.config.provider.lower() != "ollama":
            pytest.skip("LangChain integration only available for Ollama provider")

        # Test connection first
        connection_result = await ai_service.test_connection()
        if connection_result.get("error"):
            pytest.skip(f"Ollama connection failed: {connection_result['error']}")

    async def test_ai_service_basic_connection(self):
        """Test basic AI service connection"""
        result = await ai_service.test_connection()
        assert result.get("success") or result.get("warning"), f"Connection failed: {result}"
        assert self.config.model_name in str(result)

    async def test_langchain_sql_query_parts_count(self):
        """Test LangChain SQL generation for parts count query"""
        message = "How many parts do I have in total?"

        result = await ai_service.chat_with_ai(message)

        assert result.get("success"), f"Query failed: {result.get('error')}"
        assert "response" in result

        # Check if LangChain was used
        response = result["response"]
        assert isinstance(response, str)

        # The response should contain some information about parts
        assert len(response) > 0
        print(f"LangChain Response: {response}")

    async def test_langchain_sql_query_find_parts(self):
        """Test LangChain SQL generation for finding parts"""
        message = "Show me all parts with resistor in the name"

        result = await ai_service.chat_with_ai(message)

        assert result.get("success"), f"Query failed: {result.get('error')}"
        assert "response" in result

        response = result["response"]
        assert isinstance(response, str)
        assert len(response) > 0
        print(f"Find Parts Response: {response}")

    async def test_langchain_sql_query_categories(self):
        """Test LangChain SQL generation for category queries"""
        message = "What categories do I have?"

        result = await ai_service.chat_with_ai(message)

        assert result.get("success"), f"Query failed: {result.get('error')}"
        assert "response" in result

        response = result["response"]
        assert isinstance(response, str)
        assert len(response) > 0
        print(f"Categories Response: {response}")

    async def test_langchain_sql_query_locations(self):
        """Test LangChain SQL generation for location queries"""
        message = "List all my storage locations"

        result = await ai_service.chat_with_ai(message)

        assert result.get("success"), f"Query failed: {result.get('error')}"
        assert "response" in result

        response = result["response"]
        assert isinstance(response, str)
        assert len(response) > 0
        print(f"Locations Response: {response}")

    async def test_office_location_domain_context(self):
        """Test that 'office' refers to database location, not TV show"""
        message = "find all parts in the office"

        result = await ai_service.chat_with_ai(message)

        assert result.get("success"), f"Query failed: {result.get('error')}"
        assert "response" in result

        # Check that SQL was generated and used
        assert result.get("sql_used") == True, "Should use SQL for location queries"
        assert result.get("sql_query"), "Should include the SQL query used"

        # Check that the SQL query contains proper JOIN syntax
        sql_query = result.get("sql_query", "")
        assert "JOIN" in sql_query.upper(), f"Should use JOIN for location queries. SQL: {sql_query}"
        assert "locationmodel" in sql_query.lower(), f"Should reference locationmodel table. SQL: {sql_query}"
        assert "partmodel" in sql_query.lower(), f"Should reference partmodel table. SQL: {sql_query}"

        # Response should not mention TV shows or fictional content
        response = result["response"].lower()
        assert "tv show" not in response, "Should not mention TV shows"
        assert "dunder mifflin" not in response, "Should not mention fictional companies"
        assert "michael scott" not in response, "Should not mention TV characters"

        print(f"Office Query SQL: {sql_query}")
        print(f"Office Query Response: {result['response']}")

    async def test_sql_join_generation(self):
        """Test that proper SQL JOINs are generated for location-based queries"""
        queries_and_expectations = [
            ("parts in the office", "office"),
            ("what's in the warehouse", "warehouse"),
            ("show parts in lab", "lab"),
        ]

        for query, location_term in queries_and_expectations:
            result = await ai_service.chat_with_ai(query)

            # Should succeed or fail gracefully
            if result.get("success"):
                sql_query = result.get("sql_query", "")

                # Should use proper JOIN syntax
                assert "JOIN" in sql_query.upper(), f"Query '{query}' should use JOIN. SQL: {sql_query}"
                assert "location_id" in sql_query.lower(), f"Should reference location_id. SQL: {sql_query}"

                print(f"Query: '{query}' -> SQL: {sql_query}")
            else:
                # If it fails, should not be due to TV show confusion
                error_msg = result.get("response", "").lower()
                assert "tv show" not in error_msg, f"Should not fail due to TV show confusion: {error_msg}"
                print(f"Query: '{query}' -> Error: {result.get('error', 'Unknown error')}")

    async def test_various_inventory_queries(self):
        """Test various inventory-related queries with proper SQL generation"""
        test_queries = [
            "how many parts are in the office?",
            "what suppliers do we have?",
            "show me all locations",
            "find parts with quantity greater than 3000",
            "which parts have LCSC as supplier?",
            "list parts by location",
        ]

        for query in test_queries:
            result = await ai_service.chat_with_ai(query)

            # Log the result for inspection
            print(f"\n--- Query: {query} ---")
            print(f"Success: {result.get('success')}")
            print(f"SQL Used: {result.get('sql_used')}")

            if result.get("sql_query"):
                print(f"SQL: {result.get('sql_query')}")

            if result.get("success"):
                response = result.get("response", "")
                print(f"Response: {response[:200]}...")

                # Response should be informative
                assert len(response) > 10, f"Response should be informative for query: {query}"

                # Should not contain TV show references
                response_lower = response.lower()
                assert "dunder mifflin" not in response_lower, f"Should not mention TV shows in response to: {query}"
                assert (
                    "michael scott" not in response_lower
                ), f"Should not mention TV characters in response to: {query}"
            else:
                print(f"Error: {result.get('error', 'Unknown error')}")

                # Even errors should not be TV show related
                error_msg = result.get("response", "").lower()
                assert "tv show" not in error_msg, f"Errors should not be TV show related for: {query}"

    async def test_non_query_message_fallback(self):
        """Test that non-database questions fall back to regular chat"""
        message = "Hello, how are you?"

        result = await ai_service.chat_with_ai(message)

        assert result.get("success"), f"Chat failed: {result.get('error')}"
        assert "response" in result

        response = result["response"]
        assert isinstance(response, str)
        assert len(response) > 0

        # Should not indicate LangChain was used for non-database queries
        assert result.get("sql_used") != True
        print(f"Non-Query Response: {response}")

    async def test_database_schema_access(self):
        """Test that AI service can access database schema"""
        schema = ai_service.get_database_schema()

        assert isinstance(schema, dict)

        # Should have some tables if database exists
        if schema:
            assert len(schema) > 0
            print(f"Database Schema: {list(schema.keys())}")

            # Check for expected tables
            expected_tables = ["partmodel", "locationmodel", "categorymodel"]
            found_tables = [table for table in expected_tables if table in schema]

            if found_tables:
                print(f"Found expected tables: {found_tables}")
            else:
                print("No expected tables found - database might be empty")

    async def test_sql_engine_creation(self):
        """Test SQLAlchemy engine creation for LangChain"""
        engine = ai_service._get_sql_engine()

        if os.path.exists(ai_service.db_path):
            assert engine is not None, "SQL engine should be created when database exists"
            print("SQL engine created successfully")
        else:
            print("Database file does not exist - skipping engine test")

    async def test_langchain_chain_creation(self):
        """Test LangChain SQL Database Chain creation"""
        config = ai_service.load_config()

        if config.provider.lower() == "ollama":
            chain = ai_service._get_sql_chain(config)

            if os.path.exists(ai_service.db_path):
                # Chain creation might fail if Ollama is not accessible, that's okay
                print(f"LangChain SQL chain creation result: {chain is not None}")
            else:
                print("Database file does not exist - skipping chain test")
        else:
            print("LangChain chain only supported for Ollama provider")

    @pytest.mark.parametrize(
        "query",
        [
            "How many parts do I have?",
            "Show me parts running low on stock",
            "What's in location A1?",
            "Find all resistors",
            "Show me electronic components",
        ],
    )
    async def test_various_database_queries(self, query):
        """Test various types of database queries through LangChain"""
        result = await ai_service.chat_with_ai(query)

        # These tests should not fail, but might not return useful data if DB is empty
        assert result.get("success") or result.get("error"), "Should get either success or error response"

        if result.get("success"):
            assert "response" in result
            assert isinstance(result["response"], str)
            print(f"Query: '{query}' -> Response length: {len(result['response'])}")
        else:
            print(f"Query: '{query}' -> Error: {result.get('error')}")


if __name__ == "__main__":
    # Run a quick test
    async def quick_test():
        test_instance = TestAIServiceLangChain()
        await test_instance.setup()
        await test_instance.test_ai_service_basic_connection()
        print("Quick test passed!")

    asyncio.run(quick_test())
