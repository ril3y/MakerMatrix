from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from MakerMatrix.models.ai_config_model import AIConfig, AIConfigUpdate
from MakerMatrix.schemas.response import ResponseSchema
from MakerMatrix.services.ai_service import ai_service
from MakerMatrix.utils.config import load_ai_config, save_ai_config

router = APIRouter()


@router.get("/config")
async def get_ai_config():
    """Get current AI configuration"""
    try:
        config = load_ai_config()
        # Don't return the API key for security
        config_dict = config.model_dump()
        if config_dict.get('api_key'):
            config_dict['api_key'] = '***'
        
        return ResponseSchema(
            status="success",
            message="AI configuration retrieved successfully",
            data=config_dict
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get AI config: {str(e)}")


@router.put("/config")
async def update_ai_config(config_update: AIConfigUpdate):
    """Update AI configuration"""
    try:
        current_config = load_ai_config()
        
        # Update only provided fields
        update_data = config_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(current_config, field, value)
        
        if save_ai_config(current_config):
            return ResponseSchema(
                status="success",
                message="AI configuration updated successfully",
                data=None
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to save configuration")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update AI config: {str(e)}")


class ChatMessage(BaseModel):
    message: str
    conversation_history: List[Dict[str, str]] = []

class ChatResponse(BaseModel):
    response: str
    success: bool
    model: str = ""
    provider: str = ""

@router.post("/chat")
async def chat_with_ai(chat_data: ChatMessage):
    """Chat with AI assistant"""
    try:
        result = await ai_service.chat_with_ai(
            message=chat_data.message,
            conversation_history=chat_data.conversation_history
        )
        
        if result.get("error"):
            return ResponseSchema(
                status="error",
                message=result["error"],
                data=None
            )
        
        return ResponseSchema(
            status="success",
            message="AI response generated",
            data=ChatResponse(
                response=result["response"],
                success=result["success"],
                model=result.get("model", ""),
                provider=result.get("provider", "")
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to chat with AI: {str(e)}")

@router.post("/test")
async def test_ai_connection():
    """Test AI connection with current configuration"""
    try:
        result = await ai_service.test_connection()
        
        if result.get("error"):
            return ResponseSchema(
                status="error",
                message=result["error"],
                data=result
            )
        elif result.get("warning"):
            return ResponseSchema(
                status="warning",
                message=result["warning"],
                data=result
            )
        else:
            return ResponseSchema(
                status="success",
                message=result.get("message", "Connection successful"),
                data=result
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to test AI connection: {str(e)}")


@router.post("/reset")
async def reset_ai_config():
    """Reset AI configuration to defaults"""
    try:
        default_config = AIConfig()
        if save_ai_config(default_config):
            return ResponseSchema(
                status="success",
                message="AI configuration reset to defaults",
                data=None
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to reset configuration")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset AI config: {str(e)}")


@router.get("/models")
async def get_available_models():
    """Get available models from the current AI provider"""
    try:
        config = load_ai_config()
        
        if config.provider.lower() == "ollama":
            # Fetch models from Ollama
            import requests
            try:
                response = requests.get(f"{config.api_url}/api/tags", timeout=10)
                if response.status_code == 200:
                    models_data = response.json().get("models", [])
                    models = []
                    for model in models_data:
                        model_info = {
                            "name": model.get("name", ""),
                            "size": model.get("size", 0),
                            "modified_at": model.get("modified_at", ""),
                            "digest": model.get("digest", "")
                        }
                        models.append(model_info)
                    
                    return ResponseSchema(
                        status="success",
                        message=f"Found {len(models)} Ollama models",
                        data={
                            "provider": "ollama",
                            "models": models,
                            "current_model": config.model_name
                        }
                    )
                else:
                    return ResponseSchema(
                        status="error",
                        message=f"Failed to fetch Ollama models: HTTP {response.status_code}",
                        data={"provider": "ollama", "models": []}
                    )
            except requests.RequestException as e:
                return ResponseSchema(
                    status="error",
                    message=f"Cannot connect to Ollama: {str(e)}",
                    data={"provider": "ollama", "models": []}
                )
        
        elif config.provider.lower() == "openai":
            # OpenAI models are predefined
            models = [
                {"name": "gpt-4", "description": "Most capable GPT-4 model"},
                {"name": "gpt-4-turbo", "description": "Latest GPT-4 turbo model"},
                {"name": "gpt-3.5-turbo", "description": "Fast and efficient model"},
                {"name": "gpt-3.5-turbo-16k", "description": "Extended context version"}
            ]
            return ResponseSchema(
                status="success",
                message=f"OpenAI predefined models",
                data={
                    "provider": "openai",
                    "models": models,
                    "current_model": config.model_name
                }
            )
        
        elif config.provider.lower() == "anthropic":
            # Anthropic models are predefined
            models = [
                {"name": "claude-3-opus-20240229", "description": "Most capable Claude model"},
                {"name": "claude-3-sonnet-20240229", "description": "Balanced performance and speed"},
                {"name": "claude-3-haiku-20240307", "description": "Fastest Claude model"},
                {"name": "claude-2.1", "description": "Previous generation Claude"},
                {"name": "claude-2.0", "description": "Previous generation Claude"}
            ]
            return ResponseSchema(
                status="success",
                message=f"Anthropic predefined models",
                data={
                    "provider": "anthropic",
                    "models": models,
                    "current_model": config.model_name
                }
            )
        
        else:
            return ResponseSchema(
                status="error",
                message=f"Unsupported provider: {config.provider}",
                data={"provider": config.provider, "models": []}
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get available models: {str(e)}")