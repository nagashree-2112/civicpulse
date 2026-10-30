from pathlib import Path
from uuid import uuid4
from fastapi import HTTPException, UploadFile

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "data" / "uploads"
MAX_IMAGE_BYTES = 5 * 1024 * 1024
SIGNATURES = ((b"\x89PNG\r\n\x1a\n", ".png", "image/png"), (b"\xff\xd8\xff", ".jpg", "image/jpeg"), (b"GIF87a", ".gif", "image/gif"), (b"GIF89a", ".gif", "image/gif"))

async def store_image(file: UploadFile) -> str:
    data=await file.read(MAX_IMAGE_BYTES+1)
    await file.close()
    if len(data)>MAX_IMAGE_BYTES: raise HTTPException(413,"Image must be 5 MB or smaller")
    kind=next(((ext,mime) for signature,ext,mime in SIGNATURES if data.startswith(signature)),None)
    if not kind and len(data)>=12 and data[:4]==b"RIFF" and data[8:12]==b"WEBP": kind=(".webp","image/webp")
    if not kind: raise HTTPException(415,"Use a valid PNG, JPEG, GIF, or WebP image")
    if file.content_type not in (kind[1], "application/octet-stream"): raise HTTPException(415,"Image content does not match its file type")
    ext=kind[0]
    if ext==".png": structurally_valid=len(data)>=45 and data[12:16]==b"IHDR" and data.endswith(b"\x00\x00\x00\x00IEND\xaeB`\x82")
    elif ext==".jpg": structurally_valid=len(data)>=8 and data.endswith(b"\xff\xd9")
    elif ext==".gif": structurally_valid=len(data)>=14 and data.endswith(b";")
    else: structurally_valid=len(data)>=16 and data[8:12]==b"WEBP" and int.from_bytes(data[4:8],"little")==len(data)-8
    if not structurally_valid: raise HTTPException(415,"Image file is incomplete or malformed")
    UPLOAD_DIR.mkdir(parents=True,exist_ok=True)
    name=f"{uuid4().hex}{kind[0]}"
    (UPLOAD_DIR/name).write_bytes(data)
    return f"/uploads/{name}"
