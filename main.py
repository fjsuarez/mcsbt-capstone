from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OpenIdConnect
from fastapi.responses import JSONResponse
import firebase_admin
import httpx
from pydantic_settings import BaseSettings
import json

class Settings(BaseSettings):
    PORT: int
    ADMIN_SERVICE_URL: str
    NOTIFICATION_SERVICE_URL: str
    REVIEW_SERVICE_URL: str
    RIDE_SERVICE_URL: str
    USER_SERVICE_URL: str

    class Config:
        env_file = ".env"

settings = Settings()

services = {
    "admin": settings.ADMIN_SERVICE_URL,
    "notifications": settings.NOTIFICATION_SERVICE_URL,
    "reviews": settings.REVIEW_SERVICE_URL,
    "rides": settings.RIDE_SERVICE_URL,
    "users": settings.USER_SERVICE_URL
}

if not firebase_admin._apps:
    cred = firebase_admin.credentials.Certificate("credentials.json")
    firebase_admin.initialize_app(cred)

openid_connect_url = f"https://securetoken.google.com/{cred.project_id}/.well-known/openid-configuration"
security_scheme = OpenIdConnect(openIdConnectUrl=openid_connect_url)

async def forward_request(service_url: str, method: str, path: str, body : dict = None, headers: dict = None):
    async with httpx.AsyncClient() as client:
        url = f"{service_url}{path}"
        response = await client.request(method, url, json=body, headers=headers)
        return response

app = FastAPI(
    root_path="/api",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.api_route(
        "/{service}/{path:path}", 
        methods=["GET", "POST", "PUT", "DELETE", "PATCH"], 
        dependencies=[Depends(security_scheme)],
        operation_id="gateway")
async def gateway(service: str, path: str, request: Request):
    if service not in services:
        raise HTTPException(status_code=404, detail="Service not found")
    service_url = services[service]
    try:
        body = await request.json()
    except json.JSONDecodeError:
        print("Request with no body")
        body = None
    headers = dict(request.headers)
    if headers and "content-length" in headers:
        headers.pop("content-length", None)
    response = await forward_request(service_url, request.method, f"/{path}", body, headers)
    return JSONResponse(status_code=response.status_code, content=response.json())

@app.get("/health", include_in_schema=False)
async def health():
    """Health check endpoint for GKE ingress."""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT, log_level="info")