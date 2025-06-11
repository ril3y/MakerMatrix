"""
Task system for MakerMatrix background operations
"""

import os
import importlib
import inspect
from typing import Dict, Type
from .base_task import BaseTask

# Dictionary to store all discovered task classes
TASK_REGISTRY: Dict[str, Type[BaseTask]] = {}

def discover_tasks():
    """Automatically discover and register all task classes in this directory"""
    global TASK_REGISTRY
    
    # Get the current directory
    current_dir = os.path.dirname(__file__)
    
    # Scan all Python files in the tasks directory
    for filename in os.listdir(current_dir):
        if filename.endswith('_task.py') and filename != 'base_task.py':
            module_name = filename[:-3]  # Remove .py extension
            
            try:
                # Import the module dynamically
                module = importlib.import_module(f'.{module_name}', package='MakerMatrix.tasks')
                
                # Find all classes in the module that inherit from BaseTask
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (issubclass(obj, BaseTask) and 
                        obj != BaseTask and 
                        hasattr(obj, 'task_type')):
                        
                        # Create an instance to get the task_type
                        try:
                            instance = obj()
                            task_type = instance.task_type
                            TASK_REGISTRY[task_type] = obj
                            print(f"Registered task: {task_type} -> {obj.__name__}")
                        except Exception as e:
                            print(f"Failed to register task {obj.__name__}: {e}")
                            
            except Exception as e:
                print(f"Failed to import task module {module_name}: {e}")

def get_task_class(task_type: str) -> Type[BaseTask]:
    """Get a task class by its task type"""
    return TASK_REGISTRY.get(task_type)

def get_all_task_types() -> Dict[str, Type[BaseTask]]:
    """Get all registered task types"""
    return TASK_REGISTRY.copy()

def list_available_tasks():
    """List all available task types"""
    return list(TASK_REGISTRY.keys())

# Automatically discover tasks when the module is imported
discover_tasks()

__all__ = [
    "BaseTask",
    "TASK_REGISTRY",
    "discover_tasks",
    "get_task_class", 
    "get_all_task_types",
    "list_available_tasks"
]