from fastapi import FastAPI, APIRouter
from fastapi.responses import HTMLResponse
from kiteconnect import KiteConnect
from dotenv import load_dotenv
import os
from pathlib import Path

# load API_KEY and API_SECRET_KEY
load_dotenv()
API_SECRET_KEY = os.getenv("KITE_API_SECRET_KEY")
API_KEY = os.getenv("KITE_API_KEY")

# initialise a FastAPI instance
app = FastAPI()

# initialise kite 
kite = KiteConnect(api_key=API_KEY)

#define route
router = APIRouter()

@router.get("/callback", response_class=HTMLResponse)
async def kite_callback(request_token: str, status: str):
    if status == "success": 
        data = kite.generate_session(request_token=request_token, api_secret=API_SECRET_KEY)
        access_token = data["access_token"]
        # need to find absolute path for .env file
        PROJECT_ROOT = Path(__file__).resolve().parents[4]
        ENV_PATH = PROJECT_ROOT/".env"

        with open(ENV_PATH, 'r') as f:
            lines = f.readlines()

        lines = [line for line in lines if not line.startswith("KITE_ACCESS_TOKEN=")] 
        lines.append(f"KITE_ACCESS_TOKEN={access_token}")

        with open(ENV_PATH, 'w') as f:
            f.writelines(lines)

        print(f"Access token successfully generated: {access_token}")
        return HTMLResponse(f"<h3> Access Token generated successfully.</h3>")

    else:
        print("Login failed")

