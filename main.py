# Python
from fastapi import FastAPI, Request, HTTPException
import httpx

app = FastAPI()

# Base URLs for your microservices (adjust ports as needed)
USER_SERVICE_URL = "http://localhost:8001"
RIDE_SERVICE_URL = "http://localhost:8002"
NOTIFICATION_SERVICE_URL = "http://localhost:8003"
REVIEW_SERVICE_URL = "http://localhost:8004"
ADMIN_SERVICE_URL = "http://localhost:8005"

async def proxy_request(request: Request, base_url: str):
    # Build the proxied URL by combining base URL and the original request path and query
    url = f"{base_url}{request.url.path}"
    if request.url.query:
        url = f"{url}?{request.url.query}"
    # Forward the request to the microservice
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
    return await proxy_request(request, USER_SERVICE_URL)

@app.api_route("/rides/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def rides_gateway(path: str, request: Request):
    return await proxy_request(request, RIDE_SERVICE_URL)

@app.api_route("/notifications/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def notifications_gateway(path: str, request: Request):
    return await proxy_request(request, NOTIFICATION_SERVICE_URL)

@app.api_route("/reviews/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def reviews_gateway(path: str, request: Request):
    return await proxy_request(request, REVIEW_SERVICE_URL)

@app.api_route("/admin/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def admin_gateway(path: str, request: Request):
    return await proxy_request(request, ADMIN_SERVICE_URL)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)