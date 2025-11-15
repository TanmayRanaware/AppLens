"""Authentication routes"""
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from jose import jwt
from datetime import datetime, timedelta
from app.config import settings
from app.auth.github_oauth import get_github_access_token, get_github_user

router = APIRouter()


@router.get("/github/login")
async def github_login():
    """Initiate GitHub OAuth flow"""
    # Add state parameter for security
    import secrets
    state = secrets.token_urlsafe(32)
    
    # Build OAuth URL
    # Note: GitHub OAuth doesn't support forcing account selection
    # Users need to revoke authorization or use incognito mode to switch accounts
    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": settings.github_oauth_redirect_uri_computed,
        "scope": "read:user repo",
        "state": state,
    }
    
    params_str = "&".join([f"{k}={v}" for k, v in params.items()])
    github_oauth_url = f"https://github.com/login/oauth/authorize?{params_str}"
    
    return RedirectResponse(url=github_oauth_url)


@router.get("/github/callback")
async def github_callback(code: str, request: Request, response: Response):
    """Handle GitHub OAuth callback"""
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")
    
    # Exchange code for access token
    access_token = await get_github_access_token(code)
    if not access_token:
        raise HTTPException(status_code=400, detail="Failed to get access token")
    
    # Get user info
    user = await get_github_user(access_token)
    if not user:
        raise HTTPException(status_code=400, detail="Failed to get user info")
    
    # Create JWT token
    jwt_payload = {
        "sub": str(user["id"]),
        "login": user["login"],
        "access_token": access_token,
        "exp": datetime.utcnow() + timedelta(hours=settings.jwt_expiration_hours),
    }
    token = jwt.encode(jwt_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    
    # Set cookie and redirect
    response = RedirectResponse(url=f"{settings.frontend_url}/dashboard")
    response.set_cookie(
        key="applens_token",
        value=token,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        max_age=settings.jwt_expiration_hours * 3600,
    )
    return response


def get_current_user(request: Request) -> dict:
    """Get current user from JWT token"""
    token = request.cookies.get("applens_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.get("/me")
async def get_me(request: Request):
    """Get current authenticated user info"""
    user = get_current_user(request)
    return {
        "id": user.get("sub"),
        "login": user.get("login"),
        "authenticated": True,
    }


@router.post("/logout")
async def logout():
    """Logout user by clearing the authentication cookie"""
    # Clear the cookie by setting it to expire immediately
    response = Response(status_code=200)
    response.set_cookie(
        key="applens_token",
        value="",
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        max_age=0,  # Expire immediately
        path="/",
    )
    return response

