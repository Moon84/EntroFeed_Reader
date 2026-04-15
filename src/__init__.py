import uvicorn


def run():
    uvicorn.run("src.app:app", host="0.0.0.0", port=8001, reload=True, log_level="debug")
