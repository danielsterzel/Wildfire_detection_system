from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.endpoints import router
from backend.core.SecurityConfig import setup_cors

app = FastAPI()

setup_cors(app)
app.include_router(router)


