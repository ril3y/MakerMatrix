import sys
import uvicorn
from fastapi import FastAPI
from lib.my_routes import setup_routes

sys.path.append("./lib")

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
# try:
#
#     app.mount("/static", StaticFiles(directory="static/part_inventory_ui/build/"), name="static")
# except RuntimeError as e:
#     print("Error while mounting static")

if __name__ == "__main__":
    # Start the FastAPI server
    setup_routes(app)
    uvicorn.run(app, host='0.0.0.0', port=57891)
