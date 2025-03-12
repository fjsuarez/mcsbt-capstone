from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import Response
from fastapi.security import HTTPBearer
import firebase_admin
from firebase_admin import credentials, auth
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

# This is where token verification happens:
async def verify_jwt(request: Request):
    authorization = request.headers.get("Authorization")
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    try:
        # Debug info
        print("Auth header received:", authorization[:15] + "...")
        
        # Clean the token - remove 'Bearer ' prefix if present
        token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
        
        # Verify token with Firebase
        decoded_token = auth.verify_id_token(token)
        print("Token verified successfully, uid:", decoded_token.get('uid'))
        return decoded_token
    except Exception as e:
        print(f"Token verification error: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

async def proxy_request(request: Request, base_url: str, new_path: str = None, headers: dict = None):
    """Proxy the request to the specified service."""
    path = new_path if new_path is not None else request.url.path
    
    # Prepare request headers
    request_headers = dict(request.headers)
    if headers:
        request_headers.update(headers)
    
    # Remove host header to avoid conflicts
    if "host" in request_headers:
        del request_headers["host"]
        
    target_url = f"{base_url}{path}"
    
    try:
        body = await request.body()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=request_headers,
                content=body,
                params=request.query_params,
                follow_redirects=True
            )
            
        # Return the response from the service
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.headers.get("content-type")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error proxying request: {str(e)}")

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
    headers = dict(request.headers)
    headers["X-User-ID"] = token_data.get('uid', '')
    
    new_path = "/" + path
    return await proxy_request(request, settings.USER_SERVICE_URL, new_path=new_path, headers=headers)

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

@app.get("/healthz", include_in_schema=False)
async def healthz():
    """Health check endpoint for GKE ingress."""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)