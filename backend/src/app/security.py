from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
import os

# API_KEY = os.getenv("API_KEY")
API_KEY = "sdfsdfgsdgfsdasfasdasdAAADSDOIUJKJHKJhkjahsdhkjahsdhasdkUYJKJh1232132JKKJhk$$%@!"
API_KEY_NAME = "X-API-Key" # The name of the header we will look for

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key: str = Security(api_key_header)):
    """
    Dependency that checks for the API key in the request header.
    """
    if not API_KEY:
        # This allows the app to run in a test environment without a key
        print("Warning: API_KEY not set, security is disabled.")
        return
        
    if api_key == API_KEY:
        return api_key
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )