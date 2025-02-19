from fastapi import FastAPI, Request, HTTPException
import httpx
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PORT : int
    ADMIN_SERVICE_URL : str
    NOTIFICATION_SERVICE_URL : str
    REVIEW_SERVICE_URL : str
    RIDE_SERVICE_URL : str
    USER_SERVICE_URL : str

    class Config:
        env_file = ".env"

settings = Settings()

app = FastAPI()

async def proxy_request(request: Request, base_url: str, new_path: str = None):
    # Use new_path if provided; otherwise use the full request path
    path = new_path if new_path is not None else request.url.path
    url = f"{base_url}{path}"
    if request.url.query:
        url = f"{url}?{request.url.query}"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.request(
                request.method,
                url,
                headers=request.headers,
                content=await request.body(),
                timeout=10.0
            )
        except httpx.RequestError as exc:
            raise HTTPException(status_code=500, detail=str(exc))
    return resp.json(), resp.status_code

@app.api_route("/users/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def users_gateway(path: str, request: Request):
    new_path = "/" + path
    return await proxy_request(request, settings.USER_SERVICE_URL, new_path=new_path)

@app.api_route("/rides/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def rides_gateway(path: str, request: Request):
    new_path = "/" + path
    return await proxy_request(request, settings.RIDE_SERVICE_URL, new_path=new_path)

@app.api_route("/notifications/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def notifications_gateway(path: str, request: Request):
    new_path = "/" + path
    return await proxy_request(request, settings.NOTIFICATION_SERVICE_URL, new_path=new_path)

@app.api_route("/reviews/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def reviews_gateway(path: str, request: Request):
    new_path = "/" + path
    return await proxy_request(request, settings.REVIEW_SERVICE_URL, new_path=new_path)

@app.api_route("/admin/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def admin_gateway(path: str, request: Request):
    new_path = "/" + path
    return await proxy_request(request, settings.ADMIN_SERVICE_URL, new_path=new_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)