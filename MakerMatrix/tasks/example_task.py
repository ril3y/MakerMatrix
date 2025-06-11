"""
Example Task - Shows how easy it is to create new tasks
"""

import asyncio
from typing import Dict, Any
from .base_task import BaseTask
from MakerMatrix.models.task_models import TaskModel


class ExampleTask(BaseTask):
    """Example task to demonstrate the modular system"""
    
    @property
    def task_type(self) -> str:
        return "example_task"
    
    @property
    def name(self) -> str:
        return "Example Task"
    
    @property
    def description(self) -> str:
        return "This is an example task to demonstrate how easy it is to add new tasks"
    
    async def execute(self, task: TaskModel) -> Dict[str, Any]:
        """Execute the example task"""
        input_data = self.get_input_data(task)
        message = input_data.get('message', 'Hello World!')
        steps = input_data.get('steps', 5)
        
        await self.update_progress(task, 0, f"Starting example task with message: {message}")
        self.log_info(f"Example task started with {steps} steps", task)
        
        for i in range(steps):
            step_message = f"Processing step {i+1}/{steps}"
            progress = int((i / steps) * 90)
            
            await self.update_progress(task, progress, step_message)
            self.log_info(f"Completed step {i+1}", task)
            
            # Simulate some work
            await self.sleep(0.5)
        
        await self.update_progress(task, 100, "Example task completed successfully!")
        
        result = {
            "message": message,
            "steps_completed": steps,
            "status": "success",
            "example_data": {
                "random_number": 42,
                "processed_items": list(range(steps))
            }
        }
        
        self.log_info("Example task completed successfully", task)
        
        return result