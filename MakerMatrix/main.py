import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import parts_routes, locations_routes, categories_routes, printer_routes, utility_routes
from services.printer_service import PrinterService

# Initialize the FastAPI app
app = FastAPI()

# Configure CORS
app.add_middleware(
                     CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include routers
app.include_router(parts_routes.router, prefix="/parts", tags=["parts"])
app.include_router(locations_routes.router, prefix="/locations", tags=["locations"])
app.include_router(categories_routes.router, prefix="/categories", tags=["categories"])
app.include_router(printer_routes.router, prefix="/printer", tags=["printer"])
app.include_router(utility_routes.router, prefix="/utility", tags=["utility"])

if __name__ == "__main__":
    # Load printer config at startup
    try:
        printer_service = PrinterService()
        printer_service.load_printer_config()
        print("Printer configuration loaded on startup.")
    except FileNotFoundError:
        print("No config file found. Using default printer configuration.")
    except Exception as e:
        print(f"Error loading configuration: {e}")

    # Start the FastAPI server
    uvicorn.run(app, host='0.0.0.0', port=57891)
