from typing import Dict, Any, Optional
from pydantic import BaseModel


DEFAULT_SYSTEM_PROMPT = """You are MakerMatrix AI, a helpful assistant for a parts inventory management system.

Your primary role is to help users manage their electronic components, hardware parts, and materials. You have direct access to the inventory database and can provide real-time information about:

- Parts availability and quantities
- Location of specific components  
- Inventory analysis and insights
- Recommendations for parts based on user requirements
- Low stock alerts and inventory optimization
- Component specifications and alternatives

When users ask about inventory, always query the database for current information. You can write SQL queries to get detailed data and provide comprehensive analysis.

Key capabilities:
- Search for parts by name, category, or specifications
- Check stock levels and suggest reordering
- Find parts in specific locations
- Recommend alternatives when parts are out of stock
- Analyze usage patterns and trends
- Help organize and categorize inventory

Be helpful, accurate, and proactive in suggesting improvements to their inventory management."""

class AIConfig(BaseModel):
    enabled: bool = False
    provider: str = "ollama"  # ollama, openai, anthropic
    api_url: str = "http://localhost:11434"
    api_key: Optional[str] = None
    model_name: str = "llama3.2"
    temperature: float = 0.7
    max_tokens: int = 2000
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    additional_settings: Dict[str, Any] = {}


class AIConfigUpdate(BaseModel):
    enabled: Optional[bool] = None
    provider: Optional[str] = None
    api_url: Optional[str] = None
    api_key: Optional[str] = None
    model_name: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    system_prompt: Optional[str] = None
    additional_settings: Optional[Dict[str, Any]] = None