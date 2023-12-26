from fastapi import FastAPI, UploadFile, Request
from fastapi.responses import JSONResponse, FileResponse, Response
import uvicorn
from filetypes import *
import aiohttp
import utils
from slowapi.errors import RateLimitExceeded
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from fastapi.middleware.cors import CORSMiddleware
import time
import aiofiles
from prisma import Prisma
import uuid
import os
from datetime import datetime
from dotenv import load_dotenv

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
db = Prisma()
load_dotenv()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware( # Disable CORS
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

file_life_time = 2_592_000 # File life time (unused)
check_period = 86_400#  File check period (unused)


@app.on_event("startup")
async def startup_event():
    await db.connect() # Connecting to database
    print("Connected to Data Base")


@app.get("/favicon.ico") # Favicon handler
def get_favicon():
    return FileResponse(path="1.png") 


@app.post("/api/upload/") # File upload handler
@limiter.limit(f"2/minute")
async def upload_file(file: UploadFile, request: Request, include_ext: bool = False):
    if not file: # Check, if the file is uploaded
        return JSONResponse(content={"status": "error", "message": "No file uploaded"}, status_code=204) 

    if file.filename.find(".") == -1: # Check, if the file has a extension
        return JSONResponse(content={"status": "error", "message": "Bad file extension"}, status_code=400)

    if file.size > 100 * 1024 * 1024:  # 100MB limit
        return JSONResponse(content={"status": "error", "message": "File size exceeds the limit (100MB)"}, status_code=413)

    key = str(uuid.uuid4()) # Generate unique delete key
    ext = "." + file.filename.split(".")[-1] # Get file extension
    fid = utils.generate_token(10) + (ext if include_ext else "") # Generate file url
    fn = str(uuid.uuid4()) + ext  # Generate file name

    async with aiofiles.open(f"uploads/{fn}", "wb") as f: # Save file locally
        await f.write(file.file.read())

    created = await db.file.create({ # Creating a file record
        "created_date": str(datetime.now()),
        "url": fid,
        "filename": f"uploads/{fn}",
        "craeted_at": time.time(),
        "last_watched": time.time(),
        "key": key,
        "type": filetypes.get(ext[1:], default) if ext.lower()[1:] in filetypes else "download",
        "ext": ext,
        "user_filename": file.filename
    })

    return JSONResponse(content={"status": "success", 
                                 "message": "File uploaded successfully", 
                                 "file_url": created.url,
                                 "file_url_full": "https://fu.andcool.ru/file/" + created.url,
                                 "key": created.key,
                                 "ext": created.ext,
                                 "user_filename": created.user_filename}, status_code=200)


@app.get("/file/{url}") # Get file handler
@limiter.limit(f"10/minute")
async def send_file(url: str, request: Request):
    result = await db.file.find_first(where={"url": url}) # Get file by url
    if not result: return JSONResponse(content="File not found!", status_code=404) # if file does'n exists

    await db.file.update(where={"id": result.id}, data={"last_watched": time.time()}) # Update last watched record

    if result.type != "download": # If Ffile extension recognized
        async with aiofiles.open(result.filename, mode="rb") as f:
            return Response(await f.read(), media_type=result.type) # Send file with "Content-type" header
    else: # If file extension doesn't recognized
        return FileResponse(path=result.filename, filename=result.user_filename, media_type=result.type) # Send file as FileResponse


@app.delete("/api/delete/{url}") # File delete handler
async def status(url: str, request: Request, key: str = ""):
    result = await db.file.find_first(where={"url": url}) # Get file record by url
    if not result: return JSONResponse(content={"status": "error", "message": "File not found"}, status_code=404) # if file does'n exists

    if result.key == key: # If provided key matched with key from database record
        os.remove(result.filename) # Delete file
        await db.file.delete(where={"id": result.id}) # Delete file record from database

        async with aiohttp.ClientSession("https://api.cloudflare.com") as session: # Clear file cache from CloudFlare
            async with session.post(f"/client/v4/zones/{os.getenv('ZONE_ID')}/purge_cache", 
                                    json={"files": ["https://fu.andcool.ru/file/" + result.url]},
                                    headers={"Authorization": "Bearer " + os.getenv('KEY')}):
                pass
            
        return JSONResponse(content={"status": "success", "message": "deleted"}, status_code=200)
    else: # If provided key doesn't matched with key from database record
        return JSONResponse(content={"status": "error", "message": "invalid unique key"}, status_code=400) 
    

if __name__ == "__main__": # Start program
    uvicorn.run("main:app", reload=True)
