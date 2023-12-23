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
import psutil
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

file_life_time = 2_592_000
check_period = 86_400


@app.on_event("startup")
async def startup_event():
    await db.connect()
    print("Connected to Data Base")


@app.post("/api/upload/")
@limiter.limit(f"2/minute")
async def upload_file(file: UploadFile, request: Request, include_ext: bool = False):
    if not file:
        return JSONResponse(content={"status": "error", "message": "No file uploaded"}, status_code=204)

    if file.filename.find(".") == -1:
        return JSONResponse(content={"status": "error", "message": "Bad file extension"}, status_code=400)

    if file.size > 100 * 1024 * 1024:  # 10MB limit
        return JSONResponse(content={"status": "error", "message": "File size exceeds the limit (100MB)"}, status_code=413)

    key = str(uuid.uuid4())
    ext = "." + file.filename.split(".")[-1]
    fid = utils.generate_token(10) + (ext if include_ext else "")
    fn = str(uuid.uuid4()) + ext 

    async with aiofiles.open(f"uploads/{fn}", "wb") as f:
        await f.write(file.file.read())

    created = await db.file.create({
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


@app.get("/file/{url}")
@limiter.limit(f"10/minute")
async def send_file(url: str, request: Request):
    result = await db.file.find_first(where={"url": url})
    if not result: return JSONResponse(content="File not found!", status_code=404)
    await db.file.update(where={"id": result.id}, data={"last_watched": time.time()})

    if result.type != "download":
        async with aiofiles.open(result.filename, mode="rb") as f:
            return Response(await f.read(), media_type=result.type)
    else:
        return FileResponse(path=result.filename, filename=result.user_filename, media_type=result.type)


@app.get("/api/status/")
@limiter.limit(f"10/minute")
async def status(request: Request):
    disk_info = psutil.disk_usage("d://")
    disk_usage = utils.calculate_size(disk_info.used)
    disk_total = utils.calculate_size(disk_info.total)
    

    return JSONResponse(content={"status": "success", 
                                 "message": "pong",
                                 "cpu_percent": psutil.cpu_percent(),
                                 "ram_percent": psutil.virtual_memory().percent,
                                 "disk_usage": disk_usage,
                                 "disk_total": disk_total,
                                 "disk_percent": (disk_info.used * 100) / disk_info.total}, status_code=200)


@app.delete("/api/delete/{url}")
async def status(url: str, request: Request, key: str = ""):
    result = await db.file.find_first(where={"url": url})
    if not result: return JSONResponse(content={"status": "error", "message": "File not found"}, status_code=404)
    if result.key == key:
        os.remove(result.filename)
        await db.file.delete(where={"id": result.id})

        async with aiohttp.ClientSession("https://api.cloudflare.com") as session:
            async with session.post(f"/client/v4/zones/{os.getenv('ZONE_ID')}/purge_cache", 
                                    json={"files": ["https://fu.andcool.ru/file/" + result.url]},
                                    headers={"Authorization": "Bearer " + os.getenv('KEY')}) as response:
                pass
        
        return JSONResponse(content={"status": "success", "message": "deleted"}, status_code=200)
    else:
        return JSONResponse(content={"status": "error", "message": "invalid unique key"}, status_code=400)
    

if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)
