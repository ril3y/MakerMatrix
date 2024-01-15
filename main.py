import sys


sys.path.append("./lib")

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from lib.my_routes import setup_routes

# Initialize DatabaseManager
# db_manager = DatabaseManager('part_inventory.json')
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()


# Configure CORS
origins = [
    "http://localhost:3000",  # Allow your React application's origin
    # "http://another.origin.com"  # Add other origins if needed
]
# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

sys.path.append("./parsers")
sys.path.append("./lib")

# Serve static files from the "build/static" directory
app.mount("/static", StaticFiles(directory="static/part_inventory_ui/build/"), name="static")

if __name__ == "__main__":
    # Start the FastAPI server
    setup_routes(app)
    uvicorn.run(app, host='0.0.0.0', port=57891)
