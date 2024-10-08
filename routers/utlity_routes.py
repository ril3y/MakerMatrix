import os
import shutil
import uuid

from fastapi import APIRouter, UploadFile, File
from starlette.responses import FileResponse

router = APIRouter()


@router.post("/upload_image/")
async def upload_image(file: UploadFile = File(...)):
    file_extension = os.path.splitext(file.filename)[1]
    image_id = str(uuid.uuid4())
    file_path = f"uploaded_images/{image_id}{file_extension}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"image_id": image_id}


@router.get("/")
async def serve_index_html():
    return FileResponse("static/part_inventory_ui/build/index.html")