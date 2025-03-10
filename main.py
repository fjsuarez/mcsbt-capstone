from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.responses import Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
import httpx
from pydantic_settings import BaseSettings

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

# Initialize Firebase Admin if not already initialized.
if not firebase_admin._apps:
    cred = credentials.Certificate("credentials.json")
    firebase_admin.initialize_app(cred)

security_scheme = HTTPBearer()

def verify_jwt(credentials: HTTPAuthorizationCredentials = Depends(security_scheme)):
    token = credentials.credentials
    try:
        decoded_token = firebase_auth.verify_id_token(token)
        return decoded_token
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired auth token"
        )

async def proxy_request(request: Request, base_url: str, new_path: str = None):
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
    
    content_type = resp.headers.get("Content-Type", "")
    body = resp.text
    return Response(content=body, status_code=resp.status_code, media_type=content_type)

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

# Protect the gateway endpoints by adding the verify_jwt dependency.
@app.api_route("/users/login", methods=["POST"])
async def login(request: Request):
    # Proxy the login request to the user service without JWT verification.
    return await proxy_request(request, settings.USER_SERVICE_URL)

@app.api_route("/users/signup", methods=["POST"])
async def signup(request: Request):
    # Proxy the signup request to the user service without JWT verification.
    return await proxy_request(request, settings.USER_SERVICE_URL)

# Apply JWT verification for other /users endpoints.
@app.api_route("/users/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"], operation_id="users_gateway_operation")
async def users_gateway(path: str, request: Request, token_data=Depends(verify_jwt)):
    new_path = "/" + path
    return await proxy_request(request, settings.USER_SERVICE_URL, new_path=new_path)

@app.api_route("/rides/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"], operation_id="rides_gateway_operation")
async def rides_gateway(path: str, request: Request, token_data=Depends(verify_jwt)):
    new_path = "/" + path
    return await proxy_request(request, settings.RIDE_SERVICE_URL, new_path=new_path)

@app.api_route("/notifications/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"], operation_id="notifications_gateway_operation")
async def notifications_gateway(path: str, request: Request, token_data=Depends(verify_jwt)):
    new_path = "/" + path
    return await proxy_request(request, settings.NOTIFICATION_SERVICE_URL, new_path=new_path)

@app.api_route("/reviews/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"], operation_id="reviews_gateway_operation")
async def reviews_gateway(path: str, request: Request, token_data=Depends(verify_jwt)):
    new_path = "/" + path
    return await proxy_request(request, settings.REVIEW_SERVICE_URL, new_path=new_path)

@app.api_route("/admin/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"], operation_id="admin_gateway_operation")
async def admin_gateway(path: str, request: Request, token_data=Depends(verify_jwt)):
    new_path = "/" + path
    return await proxy_request(request, settings.ADMIN_SERVICE_URL, new_path=new_path)

@app.get("/healthz", include_in_schema=False, root_path="")
async def root_healthz():
    """Health check endpoint for GKE ingress."""
    return {"status": "ok"}

@app.get("/healthz", include_in_schema=False)
async def healthz():
    """Health check endpoint for GKE ingress."""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)