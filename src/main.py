import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from src.routers import incident  # type: ignore
from src.utils import initialize_options
from src.helperFunctions.slack_utils import test_slack_integration
import os
import logging
from fastapi.logger import logger as fastapi_logger

app = FastAPI()


app.include_router(incident.router)


@app.on_event("startup")
async def startup_event():
    await initialize_options()


@app.get("/")
def root():
    return {"message": "Hello World"}


if __name__ == "__main__":
    import asyncio

    asyncio.run(startup_event())
    asyncio.run(test_slack_integration())

"""
Below Code was used for testing purposes but still is kept for future debugging purposes
    
"""

# @app.exception_handler(Exception)
# async def global_exception_handler(request: Request, exc: Exception):
#     logging.error(f"Unexpected error: {exc}")
#     return JSONResponse(
#         status_code=500,
#         content={"detail": "Internal Server Error"},
#     )


# options = load_options_from_file(os.path.join(os.path.dirname(__file__), "options.json"))

# Configure logging
# logging.basicConfig(level=logging.DEBUG)
# fastapi_logger.setLevel(logging.DEBUG)
