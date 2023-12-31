"""
created by AndcoolSystems, 2023-2024
"""


from fastapi import FastAPI, UploadFile, Request, Header
from fastapi.responses import JSONResponse, FileResponse, Response
from typing import Annotated, Union
import uvicorn
from config import *
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
import jwt
import bcrypt

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
db = Prisma()
load_dotenv()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(  # Disable CORS
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

file_life_time = 2_592_000  # File life time (unused)
check_period = 86_400  # File check period (unused)


@app.on_event("startup")
async def startup_event():
    await db.connect()  # Connecting to database
    print("Connected to Data Base")


"""@app.get("/favicon.ico")  # Favicon handler
def get_favicon():
    return FileResponse(path="1.png") """


async def check_token(Authorization):
    if not Authorization:  # If token doesn't provided
        return None, {"message": "No Authorization header provided", "errorId": -1}
    
    token_header = Authorization.split(" ")
    if len(token_header) != 2:  # If token have unsupported format
        return None, {"message": "Authorization header must have `Bearer <token>` format", "errorId": -2}
    
    try:
        token = jwt.decode(token_header[1], "accessTokenSecret", algorithms=["HS256"])  # Decode token
    except jwt.exceptions.DecodeError:
        return None, {"message": "Invalid access token", "errorId": -4}
    
    if token["ExpiresAt"] < time.time():  # If token expired
        return None, {"message": "Access token expired", "errorId": -3}
    
    token_db = await db.token.find_first(where={"accessToken": token_header[1]})  # Find token in db
    if not token_db:  # If not found
        return None, {"message": "Token not found", "errorId": -5}
    
    return token_db, {}


@app.post("/api/upload")  # File upload handler
@limiter.limit(f"2/minute")
async def upload_file(file: UploadFile, request: Request, include_ext: bool = False, max_uses: int = 0, 
                      Authorization: Annotated[Union[str, None], Header(convert_underscores=False)] = None):
    if not file:  # Check, if the file is uploaded
        return JSONResponse(content={"status": "error", "message": "No file uploaded"}, status_code=400) 

    if file.filename.find(".") == -1:  # Check, if the file has a extension
        return JSONResponse(content={"status": "error", "message": "Bad file extension"}, status_code=400)

    if file.size > 100 * 1024 * 1024:   # 100MB limit
        return JSONResponse(content={"status": "error", "message": "File size exceeds the limit (100MB)"}, status_code=413)
    
    if max_uses > 10000:
        return JSONResponse(content={"status": "error", "message": "Invalid max_uses parameter"}, status_code=400)
    
    user_id = -1
    saved_to_account = False

    token_db, auth_error = await check_token(Authorization)  # Check token
    if token_db:  # If token is okay
        user_id = token_db.user_id
        saved_to_account = True

    key = str(uuid.uuid4())  # Generate unique delete key
    ext = "." + file.filename.split(".")[-1]  # Get file extension
    fid = utils.generate_token(10) + (ext if include_ext else "")  # Generate file url
    fn = str(uuid.uuid4()) + ext   # Generate file name

    async with aiofiles.open(f"uploads/{fn}", "wb") as f:  # Save file locally
        await f.write(file.file.read())

    now = datetime.now()
    created = await db.file.create({  # Creating a file record
        "user_id": user_id,
        "created_date": f"{now.day}.{now.month}.{now.year} {now.hour}:{now.minute}:{now.second}",
        "url": fid,
        "filename": f"uploads/{fn}",
        "craeted_at": time.time(),
        "last_watched": time.time(),
        "key": key,
        "type": filetypes.get(ext[1:], default) if ext.lower()[1:] in filetypes else "download",
        "ext": ext,
        "user_filename": file.filename,
        "max_uses": max_uses
    })

    user_filename = created.user_filename[:50] + ("..."  if len(created.user_filename) > 50 else "")
    return JSONResponse(content={"status": "success", 
                                 "message": "File uploaded successfully", 
                                 "file_url": created.url,
                                 "file_url_full": "https://fu.andcool.ru/file/" + created.url,
                                 "key": created.key,
                                 "ext": created.ext,
                                 "user_filename": user_filename,
                                 "craeted_at": created.craeted_at,
                                 "synced": saved_to_account,
                                 "auth_error": auth_error}, status_code=200)


@app.get("/file/{url}")  # Get file handler
@limiter.limit(f"10/minute")
async def send_file(url: str, request: Request):
    result = await db.file.find_first(where={"url": url})  # Get file by url
    if not result: 
        async with aiofiles.open("404.html", mode="rb") as f:
            return Response(await f.read(), media_type="text/html", status_code=404) # if file does'n exists
        
    print(request.headers.get('CF-IPCountry'))

    if 'sec-fetch-dest' in request.headers:
        if request.headers.get('sec-fetch-dest') == 'document':
            result = await db.file.update(where={"id": result.id}, 
                                  data={"last_watched": time.time(), "uses_number": result.uses_number + 1})  # Update last watched record
    else:
        result = await db.file.update(where={"id": result.id}, 
                                  data={"last_watched": time.time(), "uses_number": result.uses_number + 1})

    if result.max_uses < result.uses_number and result.max_uses != 0:
        await delete_file(result.url, result.key)
        return JSONResponse(content="File not found!", status_code=404)
    
    if result.type != "download":  # If File extension recognized
        async with aiofiles.open(result.filename, mode="rb") as f:
            return Response(await f.read(), media_type=result.type)  # Send file with "Content-type" header
    else:  # If file extension doesn't recognized
        return FileResponse(path=result.filename, filename=result.user_filename, media_type=result.type)  # Send file as FileResponse


@app.delete("/api/delete/{url}")  # File delete handler
async def delete_file(url: str, key: str = ""):
    result = await db.file.find_first(where={"url": url})  # Get file record by url
    if not result: return JSONResponse(content={"status": "error", "message": "File not found"}, status_code=200)  # if file does'n exists

    if result.key == key:  # If provided key matched with key from database record
        os.remove(result.filename)  # Delete file
        await db.file.delete(where={"id": result.id})  # Delete file record from database

        async with aiohttp.ClientSession("https://api.cloudflare.com") as session:  # Clear file cache from CloudFlare
            async with session.post(f"/client/v4/zones/{os.getenv('ZONE_ID')}/purge_cache", 
                                    json={"files": ["https://fu.andcool.ru/file/" + result.url]},
                                    headers={"Authorization": "Bearer " + os.getenv('KEY')}): pass
            
        return JSONResponse(content={"status": "success", "message": "deleted"}, status_code=200)
    else:  # If provided key doesn't matched with key from database record
        return JSONResponse(content={"status": "error", "message": "invalid unique key"}, status_code=400)

@app.get("/api/getFiles")  # get files handler
@limiter.limit(f"10/minute")
async def getFiles(request: Request,
                   Authorization: Annotated[Union[str, None], Header(convert_underscores=False)] = None):
    token_db, auth_error = await check_token(Authorization)  # Check token validity
    if not token_db:  # If token is not valid
        return JSONResponse(content={"status": "error", "auth_error": auth_error}, status_code=401)
    
    files = await db.file.find_many(where={"user_id": token_db.user_id})  # Get all user files from db
    files_response = []
    for file in files:
        files_response.append({
            "file_url": file.url,
            "file_url_full": "https://fu.andcool.ru/file/" + file.url,
            "key": file.key,
            "ext": file.ext,
            "user_filename": file.user_filename,
            "creation_date": file.created_date,
            "craeted_at": file.craeted_at,
            "synced": True
        })
    return JSONResponse(content={"status": "success", "message": "messages got successfully", "data": files_response}, status_code=200)


@app.post("/api/register")  # Registartion handler
@limiter.limit(f"10/minute")
async def register(request: Request):
    body = await request.json()
    if "username" not in body or \
        "password" not in body:  # If request body doesn't have username and password field
        return JSONResponse({"status": "error", "message": "No username/password provided", "errorId": 2}, status_code=400)
    
    user = await db.user.find_first(where={'username': body['username']})  # Find same username in db

    if user:  # If iser already exists
        return JSONResponse({"status": "error", "message": "An account with this name is already registered", "errorId": 1}, status_code=400)

    salt = bcrypt.gensalt()  # Encrypt password
    hashed = bcrypt.hashpw(bytes(str(body['password']), "utf-8"), salt)

    user = await db.user.create(  # Create user record in db
        {
            "username": str(body['username']),
            "password": str(hashed.decode('utf-8'))
        }
    )
    access = jwt.encode({"user_id": int(user.id), "ExpiresAt": time.time() + accesLifeTime}, 
                        "accessTokenSecret", algorithm="HS256")  # Generate token

    await db.token.create({  # Create token record in db
        "accessToken": access,
        'user': {
            'connect': {
                'id': user.id,
            },
        }
    })
    return JSONResponse({"status": "success", "accessToken": access, "username": body['username'], "message": "registred"}, status_code=200)


@app.post("/api/login")  # login handler
@limiter.limit(f"10/minute")
async def login(request: Request):
    body = await request.json()
    if "username" not in body or \
        "password" not in body:  # If request body doesn't have username and password field
        return JSONResponse({"status": "error", "message": "No username/password provided", "errorId": 2}, status_code=400)
    
    user = await db.user.find_first(where={'username': body['username']}, include={"tokens": True})  # Find same username in db
    if not user:  # If user doesn't exists
        return JSONResponse({"status": "error", "message": "User not found", "errorId": 4}, status_code=404)

    if bcrypt.checkpw(bytes(body["password"], "utf-8"), bytes(user.password, "utf-8")):  # If password is correct
        access = jwt.encode({"user_id": int(user.id), "ExpiresAt": time.time() + accesLifeTime}, "accessTokenSecret", algorithm="HS256")
        if len(user.tokens) > 10:  # If user have more than 10 tokens
            await db.token.delete_many(where={"user_id": user.id})
            
        await db.token.create({  # Create token record in db
            "accessToken": access,
            'user': {
                'connect': {
                    'id': user.id,
                }
            }})

        return {"status": "success", 
                "accessToken": access,
                "username": user.username,
                "message": "logged in with password"}
    else:  # If password doesn't match
        return JSONResponse({"status": "error", "message": "Wrong password", "errorId": 3}, status_code=400)


@app.post("/api/refresh_token")  # refresh token handler
@limiter.limit(f"10/minute")
async def login(request: Request):
    body = await request.json()
    if "accessToken" not in body:  # If token doesn't provided
        return JSONResponse({"status": "error", "message": "No access token provided", "errorId": 5}, status_code=400)
    
    token_db, auth_error = await check_token(body["accessToken"])  # Check token validity
    if not token_db:  # If token is not valid
        return JSONResponse(content={"status": "error", "auth_error": auth_error}, status_code=401)
    
    access = jwt.encode({"user_id": int(token_db.user_id), "ExpiresAt": time.time() + accesLifeTime}, 
                        "accessTokenSecret", algorithm="HS256")  # Generate new token
    await db.token.update(where={"id": token_db.id},  # Replace old token
                            data={"accessToken": access})

    return {"status": "success", 
            "accessToken": access,
            "message": "token refreshed"}


@app.post("/api/logout")  # logout handler
@limiter.limit(f"10/minute")
async def login(request: Request,
                Authorization: Annotated[Union[str, None], Header(convert_underscores=False)] = None):
    
    token_db, auth_error = await check_token(Authorization)  # Check token validity
    if not token_db:  # If token is not valid
        return JSONResponse(content={"status": "error", "auth_error": auth_error}, status_code=401)

    await db.token.delete(where={"id": token_db.id})  # Delete token record from db

    return {"status": "success", 
            "message": "logged out"}


if __name__ == "__main__":  # Start program
    uvicorn.run("main:app", reload=True, port=8080)
