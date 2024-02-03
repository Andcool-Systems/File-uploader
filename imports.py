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
import random

rate_limit_exceeded_handler = _rate_limit_exceeded_handler