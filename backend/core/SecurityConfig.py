from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

def setup_cors(app: FastAPI):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173",
                       "http://localhost:3000",
                       "http://127.0.0.1:5173",
                       "http://127.0.0.1:3000"],
        allow_methods=["*"],
        allow_headers=["*"]
    )