import sys
from asyncio import Queue
sys.path.append("./lib")

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import routes
# Initialize DatabaseManager
# db_manager = DatabaseManager('part_inventory.json')

app = FastAPI()
sys.path.append("./parsers")
sys.path.append("./lib")



# Serve static files from the "build/static" directory
app.mount("/static", StaticFiles(directory="static/part_inventory_ui/build/static"), name="static")






if __name__ == "__main__":
    # Start the FastAPI server
    routes.setup_routes(app)
    uvicorn.run(app, host='0.0.0.0', port=57891)
