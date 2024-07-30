import os
from fastapi import FastAPI,Request,HTTPException,status
from fastapi.responses import JSONResponse
from src.routers import incident # type: ignore
from src.utils import load_options_from_file
import os
import logging

app = FastAPI()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

#Logging config
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app.include_router(incident.router)

@app.on_event("startup")
async def startup_event():
    global options
    try:
        options =  load_options_from_file(os.path.join(os.path.dirname(__file__),"options.json"))
        # logger.info(f"Loading options from: {options}")
        logger.info("Options loaded successfully")
        # print(options)
    except AssertionError as e:
        logger.error(str(e))
        print(str(e))
        raise e
    
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )

@app.get("/")
def root():
    return {"message": "Hello World"}

if __name__ == "__main__":
    import asyncio
    asyncio.run(startup_event())
    
    
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down the FastAPI application")

