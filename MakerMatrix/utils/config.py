import json
import os
from MakerMatrix.models.ai_config_model import AIConfig

AI_CONFIG_FILE = "ai_config.json"


def load_ai_config() -> AIConfig:
    """Load AI configuration from file"""
    if os.path.exists(AI_CONFIG_FILE):
        try:
            with open(AI_CONFIG_FILE, 'r') as f:
                config_data = json.load(f)
                return AIConfig(**config_data)
        except Exception as e:
            print(f"Error loading AI config: {e}")
    
    # Return default config if file doesn't exist or is invalid
    return AIConfig()


def save_ai_config(config: AIConfig) -> bool:
    """Save AI configuration to file"""
    try:
        with open(AI_CONFIG_FILE, 'w') as f:
            json.dump(config.model_dump(), f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving AI config: {e}")
        return False