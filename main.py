"""
created by AndcoolSystems, 2023-2024
"""

from fastapi.responses import JSONResponse, FileResponse, Response, RedirectResponse
from config import filetypes, default, accessLifeTime, accessLifeTimeBot, pattern
from slowapi import Limiter, _rate_limit_exceeded_handler
from fastapi import FastAPI, UploadFile, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from typing import Annotated, Union
from dotenv import load_dotenv
from datetime import datetime
from prisma import Prisma
import aiofiles
import uvicorn
import aiohttp
import bcrypt
import random
import utils
import time
import uuid
import json
import jwt
import os
import re


def custom_key_func(request: Request):
    if get_remote_address(request) == os.getenv("SERVER_IP"):
        return "bots"
    return "user"


def dynamic_limit_provider(key: str):
    if key == "bots":
        return "1000/minute"
    return "10/minute"


def dynamic_limit_provider_upload(key: str):
    if key == "bots":
        return "500/minute"
    return "2/minute"


limiter = Limiter(key_func=custom_key_func)
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


@app.on_event("startup")
async def startup_event():
    await db.connect()  # Connecting to database
    print("Connected to Data Base")


@app.get("/api")  # root api endpoint
@limiter.limit(dynamic_limit_provider)
async def api(request: Request):
    return JSONResponse(
        content={
            "status": "success",
            "message": "File uploader RESTful API",
            "docs": "https://github.com/Andcool-Systems/File-uploader/blob/main/README.md",
        },
        status_code=200,
    )


async def check_token(Authorization: str, user_agent: str):
    if not Authorization:  # If token doesn't provided
        return None, {"message": "No Authorization header provided", "errorId": -1}

    token_header = Authorization.split(" ")
    if len(token_header) != 2:  # If token have unsupported format
        return None, {
            "message": "Authorization header must have `Bearer <token>` format",
            "errorId": -2,
        }

    try:
        token = jwt.decode(token_header[1], "accessTokenSecret", algorithms=["HS256"])  # Decode token
    except jwt.exceptions.DecodeError:
        return None, {"message": "Invalid access token", "errorId": -4}

    token_db = await db.token.find_first(where={"accessToken": token_header[1]}, include={"user": True})  # Find token in db

    if not token_db:  # If not found
        return None, {"message": "Token not found", "errorId": -5}

    if token["ExpiresAt"] < time.time():  # If token expired
        await db.token.delete(where={"id": token_db.id})
        return None, {"message": "Access token expired", "errorId": -3}
    
    if user_agent != token_db.fingerprint and token_db.fingerprint != "None":
        await db.token.delete(where={"id": token_db.id})
        return None, {"message": "Invalid fingerprint", "errorId": -6}

    return token_db, {}


@app.get("/invite/{group_id}")  # invite page handler
async def invite(group_id: str, request: Request):
    async with aiofiles.open("accept_invite.html", mode="rb") as f:
        return Response(await f.read(), media_type="text/html", status_code=200)


@app.post("/api/upload/{group_id}")  # File upload handler
@limiter.limit(dynamic_limit_provider_upload)
async def upload_file(
    group_id: str,
    file: UploadFile,
    request: Request,
    include_ext: bool = False,
    max_uses: int = 0,
    Authorization: Annotated[Union[str, None], Header(convert_underscores=False)] = None,
    user_agent: Union[str, None] = Header(default=None)
):

    if not file:  # Check, if the file is uploaded
        return JSONResponse(
            content={"status": "error", "message": "No file uploaded"}, status_code=400
        )

    if file.size > 100 * 1024 * 1024:  # 100MB limit
        return JSONResponse(
            content={
                "status": "error",
                "message": "File size exceeds the limit (100MB)",
            },
            status_code=413,
        )

    if max_uses > 10000:
        return JSONResponse(
            content={"status": "error", "message": "Invalid max_uses parameter"},
            status_code=400,
        )

    saved_to_account = False
    user_id = -1

    token_db, auth_error = await check_token(Authorization, user_agent)  # Check token
    if token_db:  # If token is okay
        saved_to_account = True
        user_id = token_db.user.id

    if group_id != "private":
        if not token_db:  # If token is not valid
            return JSONResponse(
                content={
                    "status": "error",
                    "message": "Auth error",
                    "auth_error": auth_error,
                },
                status_code=401,
            )
        if not group_id.isnumeric():
            return JSONResponse(
                content={"status": "error", "message": "Invalid group id"},
                status_code=400,
            )

        group = await db.group.find_first(
            where={"group_id": group_id}, include={"members": True}
        )
        if not group:
            return JSONResponse(
                content={"status": "error", "message": "Group not found"},
                status_code=404,
            )
        if token_db.user not in group.members:
            return JSONResponse(
                content={"status": "error", "message": "You are not in the group"},
                status_code=403,
            )
    else:
        group_id = -1

    file_data = file.file.read()
    try:
        is_url = re.match(pattern, file_data.decode("utf-8"))
    except Exception:
        is_url = False
        
    key = str(uuid.uuid4())  # Generate unique delete key
    ext = ("." + file.filename.split(".")[-1].lower()) if file.filename.find(".") != -1 else ""  # Get file extension
    fid = utils.generate_token(10) + (ext if include_ext else "")  # Generate file url
    fn = str(uuid.uuid4()) + ext  # Generate file name

    if not is_url:
        async with aiofiles.open(f"uploads/{fn}", "wb") as f:  # Save file locally
            await f.write(file_data)

    now = datetime.now()
    filetype = filetypes.get(ext[1:], default) if ext and ext.lower()[1:] in filetypes else "download"
    created = await db.file.create(
        {  # Creating a file record
            "user_id": user_id,
            "group_id": int(group_id),
            "created_date": f"{now.day}.{now.month}.{now.year} {now.hour}:{now.minute}:{now.second}",
            "url": fid,
            "filename": f"uploads/{fn}" if not is_url else file_data.decode("utf-8"),
            "craeted_at": time.time(),
            "last_watched": time.time(),
            "key": key,
            "type": filetype if not is_url else "redirect",
            "ext": ext,
            "size": file.size,
            "user_filename": file.filename,
            "max_uses": max_uses,
        }
    )

    user_filename = created.user_filename[:50] + (
        "..." if len(created.user_filename) > 50 else ""
    )
    return JSONResponse(
        content={
            "status": "success",
            "message": "File uploaded successfully",
            "file_url": created.url,
            "file_url_full": "https://fu.andcool.ru/file/" + created.url,
            "key": created.key,
            "ext": created.ext,
            "size": utils.calculate_size(file.size),
            "user_filename": user_filename,
            "username": None if not token_db and group_id != "private" else token_db.user.username,
            "craeted_at": created.craeted_at,
            "synced": saved_to_account,
            "auth_error": auth_error,
        },
        status_code=200,
    )


@app.get("/file/{url}")  # Get file handler
@app.get("/f/{url}")
@limiter.limit(dynamic_limit_provider)
async def send_file(url: str, request: Request):
    result = await db.file.find_first(where={"url": url})  # Get file by url

    if not result or (not os.path.isfile(result.filename) and result.type != "redirect"):
        async with aiofiles.open("404.html", mode="rb") as f:
            return Response(
                await f.read(), media_type="text/html", status_code=404
            )  # if file does'n exists
    
    if result.type == "redirect":
        return RedirectResponse(result.filename, status_code=301)

    print(request.headers.get("CF-IPCountry"))

    if "sec-fetch-dest" in request.headers:
        if request.headers.get("sec-fetch-dest") == "document":
            result = await db.file.update(
                where={"id": result.id},
                data={
                    "last_watched": time.time(),
                    "uses_number": result.uses_number + 1,
                },
            )  # Update last watched record
    else:
        result = await db.file.update(
            where={"id": result.id},
            data={"last_watched": time.time(), "uses_number": result.uses_number + 1},
        )

    if result.max_uses < result.uses_number and result.max_uses != 0:
        await delete_file(result.url, result.key)
        return JSONResponse(content="File not found!", status_code=404)

    if result.type == "download":  # If File extension doesn't recognized
        return FileResponse(
            path=result.filename, filename=result.user_filename, media_type=result.type
        )  # Send file as FileResponse

    async with aiofiles.open(result.filename, mode="rb") as f:
        return Response(
            await f.read(), media_type=result.type
        )  # Send file with "Content-type" header


@app.get("/api/delete/{url}")  # File delete handler
async def delete_file(url: str, key: str = ""):
    result = await db.file.find_first(where={"url": url})  # Get file record by url
    if not result:
        return JSONResponse(
            content={"status": "error", "message": "File not found"}, status_code=404
        )  # if file does'n exists
    try:
        if result.key == key:  # If provided key matched with key from database record
            await db.file.delete(
                where={"id": result.id}
            )  # Delete file record from database

            async with aiohttp.ClientSession("https://api.cloudflare.com") as session:  # Clear file cache from CloudFlare
                async with session.post(f"/client/v4/zones/{os.getenv('ZONE_ID')}/purge_cache",
                    json={"files": ["https://fu.andcool.ru/file/" + result.url]},
                    headers={"Authorization": "Bearer " + os.getenv("KEY")}):
                    pass
            os.remove(result.filename)  # Delete file

            return JSONResponse(
                content={"status": "success", "message": "deleted"}, status_code=200
            )
        else:  # If provided key doesn't matched with key from database record
            return JSONResponse(
                content={"status": "error", "message": "invalid unique key"},
                status_code=400,
            )
    except Exception:
        return JSONResponse(
            content={"status": "success", "message": "deleted"}, status_code=200
        )


@app.get("/api/getFiles/{group_id}")  # get files handler
@app.get("/api/get_files/{group_id}")  # get files handler
@limiter.limit(dynamic_limit_provider)
async def getFiles(
    group_id: str,
    request: Request,
    Authorization: Annotated[Union[str, None], Header(convert_underscores=False)] = None,
    user_agent: Union[str, None] = Header(default=None)
):
    
    username = None
    if group_id != "private":
        token_db, auth_error = await check_token(Authorization, user_agent)  # Check token validity
        if token_db:
            user = await db.user.find_first(where={"id": token_db.user_id})
            username = user.username

        if not group_id.isnumeric():
            return JSONResponse(
                content={"status": "error", "message": "Invalid group id"},
                status_code=400,
            )

        group = await db.group.find_first(where={"group_id": group_id}, include={"members": True})
        if not group:
            return JSONResponse(
                content={"status": "error", "message": "Group not found"},
                status_code=404,
            )

        files = await db.file.find_many(where={"group_id": group_id})

    else:
        token_db, auth_error = await check_token(Authorization, user_agent)  # Check token validity
        if not token_db:  # If token is not valid
            return JSONResponse(
                content={
                    "status": "error",
                    "message": "Auth error",
                    "auth_error": auth_error,
                },
                status_code=401,
            )

        user = await db.user.find_first(where={"id": token_db.user_id})  # Get user files from db
        files = await db.file.find_many(where={"user_id": user.id, "group_id": -1})  # Get all user files from db
        username = user.username


    files_response = []
    for file in files:
        user_filename = file.user_filename[:50] + ("..." if len(file.user_filename) > 50 else "")
        usr = (await db.user.find_first(where={"id": file.user_id})).username if username else None
        files_response.append(
            {
                "file_url": file.url,
                "file_url_full": "https://fu.andcool.ru/file/" + file.url,
                "key": file.key if username else None,
                "ext": file.ext,
                "user_filename": user_filename,
                "creation_date": file.created_date,
                "created_at": file.craeted_at,
                "size": utils.calculate_size(file.size),
                "username": usr,
                "synced": True,
            }
        )
    return JSONResponse(
        content={
            "status": "success",
            "message": "messages got successfully",
            "username": username,
            "is_group_owner": (
                None if group_id == "private" or not username else group.admin_id == token_db.user_id
            ),
            "data": files_response,
        },
        status_code=200,
    )


@app.post("/api/register")  # Registration handler
@limiter.limit(dynamic_limit_provider)
async def register(request: Request, bot: bool = False, user_agent: Union[str, None] = Header(default=None)):
    try:
        body = await request.json()
    except json.decoder.JSONDecodeError:
        return JSONResponse(
            {
                "status": "error",
                "message": "No username/password provided",
                "errorId": 2,
            },
            status_code=400,
        )
    if ("username" not in body or "password" not in body):  # If request body doesn't have username and password field
        return JSONResponse(
            {
                "status": "error",
                "message": "No username/password provided",
                "errorId": 2,
            },
            status_code=400,
        )

    user = await db.user.find_first(
        where={"username": body["username"]}
    )  # Find same username in db

    if user:  # If user already exists
        return JSONResponse(
            {
                "status": "error",
                "message": "An account with this name is already registered",
                "errorId": 1,
            },
            status_code=400,
        )

    salt = bcrypt.gensalt()  # Encrypt password
    hashed = bcrypt.hashpw(bytes(str(body["password"]), "utf-8"), salt)

    user = await db.user.create(  # Create user record in db
        {"username": str(body["username"]), "password": str(hashed.decode("utf-8"))}
    )
    access = jwt.encode(
        {
            "user_id": int(user.id),
            "ExpiresAt": time.time() + (accessLifeTime if not bot else accessLifeTimeBot),
        },
        "accessTokenSecret",
        algorithm="HS256",
    )  # Generate token

    await db.token.create(
        {  # Create token record in db
            "accessToken": access,
            "fingerprint": user_agent,
            "user": {
                "connect": {
                    "id": user.id,
                },
            },
        }
    )
    return JSONResponse(
        {
            "status": "success",
            "accessToken": access,
            "username": body["username"],
            "message": "registered",
        },
        status_code=200,
    )


@app.get("/api/login/token")  # login by token handler
@limiter.limit(dynamic_limit_provider)
async def login_token(request: Request, 
                      Authorization: Annotated[Union[str, None], Header(convert_underscores=False)] = None, 
                      user_agent: Union[str, None] = Header(default=None)):
    token_db, auth_error = await check_token(Authorization, user_agent)  # Check token validity
    if not token_db:  # If token is not valid
        return JSONResponse(
            content={
                "status": "error",
                "message": "Auth error",
                "auth_error": auth_error,
            },
            status_code=401,
    )
    return JSONResponse({"status": "success",
                         "message": "Logged in by token",
                         "username": token_db.user.username,
                         "accessToken": token_db.accessToken})


@app.post("/api/login/discord/{code}")  # login handler
@limiter.limit(dynamic_limit_provider)
async def login_discord(code: str, 
                request: Request,
                user_agent: Union[str, None] = Header(default=None)):
    
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': "https://fu.andcool.ru/login/discord"
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    auth = aiohttp.BasicAuth(login=os.getenv("DISCORD_CLIENT_ID"), password=os.getenv("DISCORD_CLIENT_SECRET"))

    response_json = {}
    async with aiohttp.ClientSession() as session:
        async with session.post('https://discord.com/api/v10/oauth2/token', data=data, headers=headers, auth=auth) as response:
            response_json = await response.json()
            if response.status != 200:
                return JSONResponse({"status": "error", "message": "Internal error, please, log in again"}, status_code=401)

            async with session.get('https://discord.com/api/users/@me', 
                                   headers={"Authorization": f"{response_json['token_type']} {response_json['access_token']}"}) as response_second:
                if response_second.status != 200:
                    return JSONResponse({"status": "error", "message": "Invalid token, please, log in again"}, status_code=401)
                response_user_json = await response_second.json()
                user_check = await db.user.find_first(where={"discord_uid": response_user_json["id"]})

                if not user_check:
                    user = await db.user.create(  # Create user record in db
                        {"username": str(response_user_json["global_name"]), 
                         "password": "None", 
                         "discord_uid": response_user_json["id"]}
                    )
                    access = jwt.encode(
                        {
                            "user_id": int(user.id),
                            "ExpiresAt": time.time() + accessLifeTime,
                        },
                        "accessTokenSecret",
                        algorithm="HS256",
                    )  # Generate token

                    await db.token.create(
                        {  # Create token record in db
                            "accessToken": access,
                            "fingerprint": user_agent,
                            "user": {
                                "connect": {
                                    "id": user.id,
                                },
                            },
                        }
                    )
                else:
                    access = jwt.encode(
                        {
                            "user_id": int(user_check.id),
                            "ExpiresAt": time.time() + accessLifeTime,
                        },
                        "accessTokenSecret",
                        algorithm="HS256",
                    )  # Generate token

                    await db.token.create(
                        {  # Create token record in db
                            "accessToken": access,
                            "fingerprint": user_agent,
                            "user": {
                                "connect": {
                                    "id": user_check.id,
                                },
                            },
                        }
                    )
                
                return JSONResponse(
                    {
                        "status": "success",
                        "accessToken": access,
                        "username": response_user_json["global_name"],
                        "message": "registred" if not user_check else "logged in",
                    },
                    status_code=200,
                )


@app.post("/api/login")  # login handler
@limiter.limit(dynamic_limit_provider)
async def login(request: Request, bot: bool = False, user_agent: Union[str, None] = Header(default=None)):
    try:
        body = await request.json()
    except json.decoder.JSONDecodeError:
        return JSONResponse(
            {
                "status": "error",
                "message": "No username/password provided",
                "errorId": 2,
            },
            status_code=400,
        )
    if ("username" not in body or "password" not in body):  # If request body doesn't have username and password field
        return JSONResponse(
            {
                "status": "error",
                "message": "No username/password provided",
                "errorId": 2,
            },
            status_code=400,
        )
    
    if not body["username"] or not body["password"]:
        return JSONResponse(
            {
                "status": "error",
                "message": "No username/password provided",
                "errorId": 2,
            },
            status_code=400,
        )

    user = await db.user.find_first(
        where={'AND': [
                    {"username": body["username"]},
                    {'NOT':[{"password": "None"}]}
                ]
            }, include={"tokens": True}
    )  # Find same username in db
    if not user:  # If user doesn't exists
        return JSONResponse(
            {"status": "error", "message": "User not found", "errorId": 4},
            status_code=404,
        )

    if bcrypt.checkpw(bytes(body["password"], "utf-8"), bytes(user.password, "utf-8")):  # If password is correct
        access = jwt.encode(
            {
                "user_id": int(user.id),
                "ExpiresAt": time.time()
                + (accessLifeTime if not bot else accessLifeTimeBot),
            },
            "accessTokenSecret",
            algorithm="HS256",
        )

        await db.token.create(
            {  # Create token record in db
                "accessToken": access,
                "fingerprint": user_agent,
                "user": {
                    "connect": {
                        "id": user.id,
                    }
                },
            }
        )

        return {
            "status": "success",
            "accessToken": access,
            "username": user.username,
            "message": "logged in with password",
        }
    else:  # If password doesn't match
        return JSONResponse(
            {"status": "error", "message": "Wrong password", "errorId": 3},
            status_code=403,
        )


@app.post("/api/refresh_token")  # refresh token handler
@limiter.limit(dynamic_limit_provider)
async def refresh_token(request: Request, user_agent: Union[str, None] = Header(default=None)):
    body = await request.json()
    if "accessToken" not in body:  # If token doesn't provided
        return JSONResponse(
            {"status": "error", "message": "No access token provided", "errorId": 5},
            status_code=400,
        )

    token_db, auth_error = await check_token(body["accessToken"], user_agent)  # Check token validity
    if not token_db:  # If token is not valid
        return JSONResponse(
            content={
                "status": "error",
                "message": "Auth error",
                "auth_error": auth_error,
            },
            status_code=401,
        )

    access = jwt.encode(
        {"user_id": int(token_db.user_id), "ExpiresAt": time.time() + accessLifeTime},
        "accessTokenSecret",
        algorithm="HS256",
    )  # Generate new token
    await db.token.update(where={"id": token_db.id}, 
                          data={"accessToken": access}  # Replace old token
    )

    return {"status": "success", "accessToken": access, "message": "token refreshed"}


@app.post("/api/logout")  # logout handler
@limiter.limit(dynamic_limit_provider)
async def logout(
    request: Request,
    Authorization: Annotated[Union[str, None], Header(convert_underscores=False)] = None,
    user_agent: Union[str, None] = Header(default=None)
):

    token_db, auth_error = await check_token(Authorization, user_agent)  # Check token validity
    if not token_db:  # If token is not valid
        return JSONResponse(
            content={
                "status": "error",
                "message": "Auth error",
                "auth_error": auth_error,
            },
            status_code=401,
        )

    await db.token.delete(where={"id": token_db.id})  # Delete token record from db

    return {"status": "success", "message": "logged out"}


@app.post("/api/transfer")  # transfer handler
@limiter.limit(dynamic_limit_provider)
async def transfer(
    request: Request,
    Authorization: Annotated[Union[str, None], Header(convert_underscores=False)] = None,
    user_agent: Union[str, None] = Header(default=None)
):

    token_db, auth_error = await check_token(Authorization, user_agent)  # Check token validity
    if not token_db:  # If token is not valid
        return JSONResponse(
            content={
                "status": "error",
                "message": "Auth error",
                "auth_error": auth_error,
            },
            status_code=401,
        )

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            content={"status": "error", "message": "Couldn't parse request body"},
            status_code=400,
        )

    if "data" not in body:
        return JSONResponse(
            content={"status": "error", "message": "No `data` field in request body"},
            status_code=400,
        )

    non_success = []
    for requested_file in body["data"]:
        try:
            file = await db.file.find_first(where={"url": requested_file["file_url"]})
            if not file or file.key != requested_file["key"]:
                non_success.append(requested_file)
                continue

            await db.file.update(
                where={"id": file.id}, data={"user_id": token_db.user_id}
            )
        except Exception:
            non_success.append(requested_file)

    return {"status": "success", "message": "transferred", "unsuccess": non_success}


# --------------------------------------Groups------------------------------------------


@app.post("/api/create_group")  # create group handler
@limiter.limit(dynamic_limit_provider)
async def create_group(
    request: Request,
    Authorization: Annotated[Union[str, None], Header(convert_underscores=False)] = None,
    user_agent: Union[str, None] = Header(default=None)
):

    body = await request.json()
    if "group_name" not in body:  # If token doesn't provided
        return JSONResponse(
            {"status": "error", "message": "No `group_name` provided"}, status_code=400
        )

    token_db, auth_error = await check_token(Authorization, user_agent)  # Check token validity
    if not token_db:  # If token is not valid
        return JSONResponse(
            content={
                "status": "error",
                "message": "Auth error",
                "auth_error": auth_error,
            },
            status_code=401,
        )

    if len(body["group_name"]) > 50:
        return JSONResponse(
            content={
                "status": "error",
                "message": "Group name length exceeded (50 chars)",
            },
            status_code=400,
        )
    group = await db.group.create(
        data={
            "name": body["group_name"],
            "group_id": random.randint(10000000, 99999999),
            "admin_id": token_db.user_id,
            "members": {
                "connect": {"id": token_db.user_id},
            },
        }
    )
    return {
        "status": "success",
        "message": "created",
        "name": group.name,
        "group_id": group.group_id,
    }


@app.delete("/api/delete_group/{group_id}")  # delete group handler
@limiter.limit(dynamic_limit_provider)
async def delete_group(
    group_id: int,
    request: Request,
    Authorization: Annotated[Union[str, None], Header(convert_underscores=False)] = None,
    user_agent: Union[str, None] = Header(default=None)
):

    token_db, auth_error = await check_token(Authorization, user_agent)  # Check token validity
    if not token_db:  # If token is not valid
        return JSONResponse(
            content={
                "status": "error",
                "message": "Auth error",
                "auth_error": auth_error,
            },
            status_code=401,
        )

    group = await db.group.find_first(where={"group_id": group_id})
    if not group:
        return JSONResponse(
            {"status": "error", "message": "Group not found"}, status_code=404
        )

    if group.admin_id != token_db.user_id:
        return JSONResponse(
            {
                "status": "error",
                "message": "You dont have any permissions to delete this group",
            },
            status_code=403,
        )

    await db.group.delete(where={"id": group.id})

    return {"status": "success", "message": "deleted"}


@app.get("/api/generate_invite/{group_id}")  # generate invite handler
@limiter.limit(dynamic_limit_provider)
async def generate_invite(
    group_id: int,
    request: Request,
    Authorization: Annotated[Union[str, None], Header(convert_underscores=False)] = None,
    user_agent: Union[str, None] = Header(default=None)
):

    token_db, auth_error = await check_token(Authorization, user_agent)  # Check token validity
    if not token_db:  # If token is not valid
        return JSONResponse(
            content={
                "status": "error",
                "message": "Auth error",
                "auth_error": auth_error,
            },
            status_code=401,
        )

    group = await db.group.find_first(where={"group_id": group_id})
    if not group:
        return JSONResponse(
            {"status": "error", "message": "Group not found"}, status_code=404
        )

    if group.admin_id != token_db.user_id:
        return JSONResponse(
            {
                "status": "error",
                "message": "You dont have any permissions",
            },
            status_code=403,
        )

    invite = await db.invitements.create(
        data={"data": utils.generate_token(15), "group": {"connect": {"id": group.id}}}
    )

    return {
        "status": "success",
        "message": "created",
        "invite_link": f"https://fu.andcool.ru/invite/{invite.data}",
    }


@app.post("/api/join/{invite_link}")  # join handler
@limiter.limit(dynamic_limit_provider)
async def join_group(
    invite_link: str,
    request: Request,
    Authorization: Annotated[Union[str, None], Header(convert_underscores=False)] = None,
    user_agent: Union[str, None] = Header(default=None)
):

    token_db, auth_error = await check_token(Authorization, user_agent)  # Check token validity
    if not token_db:  # If token is not valid
        return JSONResponse(
            content={
                "status": "error",
                "message": "Auth error",
                "auth_error": auth_error,
            },
            status_code=401,
        )

    invite = await db.invitements.find_first(
        where={"data": invite_link}, include={"group": True}
    )
    if not invite:
        return JSONResponse(
            {"status": "error", "message": "Invite link not found"}, status_code=404
        )

    group = await db.group.find_first(
        where={"id": invite.group_id}, include={"members": True}
    )
    if token_db.user in group.members:
        return JSONResponse(
            {"status": "error", "message": "You are already in the group"},
            status_code=400,
        )

    await db.group.update(
        data={
            "members": {
                "connect": {"id": token_db.user_id},
            }
        },
        where={"id": group.id},
    )

    await db.invitements.delete(where={"id": invite.id})

    return {
        "status": "success",
        "message": "Joined",
        "name": group.name,
        "group_id": group.group_id,
    }


@app.get("/api/invite_info/{invite_link}")  # invite info handler
@limiter.limit(dynamic_limit_provider)
async def invite_link(
    invite_link: str,
    request: Request,
    Authorization: Annotated[Union[str, None], Header(convert_underscores=False)] = None,
    user_agent: Union[str, None] = Header(default=None)
):

    token_db, auth_error = await check_token(Authorization, user_agent)  # Check token validity
    if not token_db:  # If token is not valid
        return JSONResponse(
            content={
                "status": "error",
                "message": "Auth error",
                "auth_error": auth_error,
            },
            status_code=401,
        )

    invite = await db.invitements.find_first(
        where={"data": invite_link}, include={"group": True}
    )
    if not invite:
        return JSONResponse(
            {"status": "error", "message": "Invite link not found"}, status_code=404
        )

    return {
        "status": "success",
        "message": "Info got successfully",
        "name": invite.group.name,
        "group_id": invite.group.group_id,
    }


@app.post("/api/leave/{group_id}")  # leave handler
@limiter.limit(dynamic_limit_provider)
async def leave_group(
    group_id: int,
    request: Request,
    Authorization: Annotated[Union[str, None], Header(convert_underscores=False)] = None,
    user_agent: Union[str, None] = Header(default=None)
):

    token_db, auth_error = await check_token(Authorization, user_agent)  # Check token validity
    if not token_db:  # If token is not valid
        return JSONResponse(
            content={
                "status": "error",
                "message": "Auth error",
                "auth_error": auth_error,
            },
            status_code=401,
        )

    group = await db.group.find_first(
        where={"group_id": group_id}, include={"members": True}
    )
    if not group:
        return JSONResponse(
            {"status": "error", "message": "Group not found"}, status_code=404
        )

    if token_db.user not in group.members:
        return JSONResponse(
            {"status": "error", "message": "You are not in the group"}, status_code=400
        )

    await db.group.update(
        data={"members": {"disconnect": {"id": token_db.user_id}}},
        where={"id": group.id},
    )

    return {"status": "success", "message": "leaved"}


@app.get("/api/get_groups")  # get groups handler
@limiter.limit(dynamic_limit_provider)
async def get_groups(
    request: Request,
    Authorization: Annotated[Union[str, None], Header(convert_underscores=False)] = None,
    user_agent: Union[str, None] = Header(default=None)
):

    token_db, auth_error = await check_token(Authorization, user_agent)  # Check token validity
    if not token_db:  # If token is not valid
        return JSONResponse(
            content={
                "status": "error",
                "message": "Auth error",
                "auth_error": auth_error,
            },
            status_code=401,
        )

    user = await db.user.find_first(
        where={"id": token_db.user_id}, include={"groups": True}
    )
    groups = []
    for group in user.groups:
        groups.append(
            {
                "name": group.name,
                "group_id": group.group_id,
            }
        )
    return {"status": "success", "message": "groups got successfully", "groups": groups}


if __name__ == "__main__":  # Start program
    uvicorn.run("main:app", reload=True, port=8080)
