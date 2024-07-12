import os
from fastapi import FastAPI,Request,HTTPException,status
from src.routers import incident # type: ignore
from src.utils import load_options_from_file
import json

app = FastAPI()

app.include_router(incident.router)

@app.get("/")
def root():
    return {"message": "Hello World"}

file_path = os.path.join(os.path.dirname(__file__), "options.json")

# Load options at startup
@app.on_event("startup")
async def startup_event():
    global options
    options = await load_options_from_file(file_path)
    print("Loaded options:", json.dumps(options, indent=2))


