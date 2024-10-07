
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
app = FastAPI()

@app.get("/openapi.yaml", include_in_schema=False)
async def get_openapi_spec():
    return FileResponse("./openapi.yaml")

app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
