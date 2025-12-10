import os
import httpx
from fastapi import APIRouter, Request, HTTPException, Depends
from urllib.parse import urlencode
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from api.db.database import get_db
from api.v1.models.user import User
from api.v1.models.wallet import Wallet
from api.utils.security import create_jwt_token
from api.utils.responses import success_response, fail_response

load_dotenv()

router = APIRouter(prefix="/auth", tags=["Authentication"])

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_ENDPOINT = "https://www.googleapis.com/oauth2/v1/userinfo"

@router.get("/google")
async def google_login():
    """Redirect to Google OAuth"""
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent"
    }
    url = f"{GOOGLE_AUTH_ENDPOINT}?{urlencode(params)}"

    return success_response(
        status_code=200,
        message="Redirecting to Google OAuth",
        data={"authorization_url": url}
    )


@router.get("/google/callback")
async def google_callback(
    request: Request,
    db: Session = Depends(get_db)

):
    """Handle Google OAuth callback and return JWT"""
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code not found.")
    
    # Exchange code for tokens
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code"
    }

    async with httpx.AsyncClient() as client:
        token_response = await client.post(GOOGLE_TOKEN_ENDPOINT, data=data)
        token_response.raise_for_status()
        tokens = token_response.json()
        access_token = tokens.get("access_token")
    
        # Fetch user info
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        userinfo_response = await client.get(GOOGLE_USERINFO_ENDPOINT, headers=headers)
        userinfo_response.raise_for_status()
        user_info = userinfo_response.json()
    
    # Check if user exists, else create
    email = user_info.get("email")
    google_id = user_info.get("id")
    full_name = user_info.get("name", email)

    user = User.fetch_one(db, google_id=google_id)

    if not user:
        #create user
        user = User(
            email=email,
            full_name=full_name,
            google_id=google_id
        )
        user.insert(db)

        # Create associated wallet
        wallet = Wallet(user_id=user.id)
        wallet.insert(db)

    # Create JWT token
    jwt_token = create_jwt_token(str(user.id), user.email)
    return success_response(
        status_code=200,
        message="Authentication successful",
        data={
            "jwt_token": jwt_token,
            "user": {
                "id": str(user.id),
                "full_name": user.full_name,
                "email": user.email
            }
        }
    )
