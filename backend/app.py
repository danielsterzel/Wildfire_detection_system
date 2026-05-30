from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse

from backend.api.endpoints import router
from backend.core.SecurityConfig import setup_cors

app = FastAPI()

setup_cors(app)
app.include_router(router)


# W sumie jedyne co zostało to dodać jakąś logike komunikatów i je wystawiac

@app.get("/")
def home():
    return RedirectResponse(url="http://localhost:5173")