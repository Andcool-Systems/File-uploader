from fastapi import FastAPI, UploadFile, Request
from fastapi.responses import JSONResponse, FileResponse, Response
import shutil
import uvicorn
from filetypes import *
import glob
import utils
from slowapi.errors import RateLimitExceeded
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from fastapi.middleware.cors import CORSMiddleware

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/upload/")
@limiter.limit(f"1/minute")
async def upload_file(file: UploadFile, request: Request):
    if not file:
        return JSONResponse(content={"status": "error", "message": "No file uploaded"}, status_code=400)

    if file.filename.find(".") == -1:
        return JSONResponse(content={"status": "error", "message": "Bad file extension"}, status_code=400)

    if file.size > 10 * 1024 * 1024:  # 10MB limit
        return JSONResponse(content={"status": "error", "message": "File size exceeds the limit (10MB)"}, status_code=413)

    fid = utils.generate_token(10)
    fn = fid + '$' + file.filename.replace("$", "")
    with open(f"uploads/{fn}", "wb") as f:
        shutil.copyfileobj(file.file, f)

    return JSONResponse(content={"status": "success", "message": "File uploaded successfully", "file_url": fid}, status_code=200)


@app.get("/file/{filename}")
async def send_file(filename: str):
    finded = glob.glob(f"uploads/{filename}$*")
    if finded == []: return JSONResponse(content="File not found!", status_code=404)

    filename_finded = finded[0]
    content_type = filetypes.get(filename_finded.split('.')[-1].lower(), default)

    if filename_finded.split('.')[-1].lower() in filetypes:
        with open(filename_finded, mode="rb") as f:
            return Response(f.read(), media_type=content_type)
    else:
        return FileResponse(path=filename_finded, filename=filename_finded.split("$")[-1], media_type=content_type)

if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)