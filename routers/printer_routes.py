from fastapi import APIRouter, HTTPException
from models.label_model import LabelData
from models import printer_config_model
from services.printer_service import PrinterService

router = APIRouter()

@router.post("/print_qr")
async def print_qr_code(label_data: LabelData):
    try:
        response = await PrinterService.print_qr_code(label_data)
        return {"message": "QR code printed successfully"} if response else HTTPException(status_code=500, detail="Failed to print QR code")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/config")
async def configure_printer(config: printer_config_model.PrinterConfig):
    try:
        PrinterService.configure_printer(config)
        return {"message": "Printer configuration updated and saved."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/load_config")
async def load_printer_config():
    try:
        PrinterService.load_printer_config()
        return {"message": "Printer configuration loaded."}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Config file not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/current_printer")
async def get_current_printer():
    try:
        current_printer = PrinterService.get_current_configuration()
        return {"current_printer": current_printer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))