import uuid
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from api.db.database import get_db
from api.v1.models.api_key import APIKey
from api.v1.models.user import User
from api.utils.deps import get_authenticated_user
from api.utils.api_key import generate_api_key, hash_api_key
from api.utils.api_key_expiry import parse_expiry_to_datetime
from api.utils.responses import success_response, fail_response

router = APIRouter(prefix="/keys", tags=["API Keys"])


class CreateAPIKeyRequest(BaseModel):
    name: str
    permissions: List[str]
    expiry: str  # 1H, 1D, 1M, 1Y


class RolloverAPIKeyRequest(BaseModel):
    expired_key_id: str
    expiry: str


@router.post("/create")
async def create_api_key(
    request: CreateAPIKeyRequest,
    auth_data: tuple = Depends(get_authenticated_user),
    db: Session = Depends(get_db)
):
    """Create new API key for authenticated user"""
    user, _ = auth_data
    
    # Validate expiry format
    expires_at = parse_expiry_to_datetime(request.expiry)
    if not expires_at:
        raise HTTPException(
            status_code=400, 
            detail="Invalid expiry format. Use: 1H, 1D, 1M, or 1Y"
        )
    
    # Check active API key limit (max 5)
    active_keys = [
        key for key in APIKey.fetch_all(db, user_id=user.id)
        if key.is_active()
    ]
    
    if len(active_keys) >= 5:
        return fail_response(
            status_code=400,
            message="Maximum 5 active API keys allowed per user",
            context={"active_keys_count": len(active_keys)}
        )
    
    # Validate permissions
    valid_permissions = ["deposit", "transfer", "read"]
    for perm in request.permissions:
        if perm not in valid_permissions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid permission: {perm}. Valid: {valid_permissions}"
            )
    
    # Generate API key
    plain_key = generate_api_key()
    hashed_key = hash_api_key(plain_key)
    
    # Create API key record
    api_key = APIKey(
        user_id=user.id,
        name=request.name,
        hashed_key=hashed_key,
        permissions=request.permissions,
        expires_at=expires_at,
        revoked=False
    )
    api_key.insert(db)
    
    return success_response(
        status_code=201,
        message="API key created successfully",
        data={
            "api_key": plain_key,  # Only time we show the plain key
            "expires_at": expires_at.isoformat()
        }
    )


@router.post("/rollover")
async def rollover_api_key(
    request: RolloverAPIKeyRequest,
    auth_data: tuple = Depends(get_authenticated_user),
    db: Session = Depends(get_db)
):
    """Rollover an expired API key with new expiry"""
    user, _ = auth_data
    
    # Find the expired key
    try:
        key_id = uuid.UUID(request.expired_key_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid key ID format")
    
    old_key = APIKey.fetch_one(db, id=key_id, user_id=user.id)
    
    if not old_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    # Verify key is actually expired
    if old_key.is_active():
        return fail_response(
            status_code=400,
            message="Cannot rollover active key. Key must be expired.",
            context={"expires_at": old_key.expires_at.isoformat()}
        )
    
    # Validate new expiry
    new_expires_at = parse_expiry_to_datetime(request.expiry)
    if not new_expires_at:
        raise HTTPException(
            status_code=400,
            detail="Invalid expiry format. Use: 1H, 1D, 1M, or 1Y"
        )
    
    # Check active key limit
    active_keys = [
        key for key in APIKey.fetch_all(db, user_id=user.id)
        if key.is_active()
    ]
    
    if len(active_keys) >= 5:
        return fail_response(
            status_code=400,
            message="Maximum 5 active API keys allowed per user"
        )
    
    # Generate new API key with same permissions
    plain_key = generate_api_key()
    hashed_key = hash_api_key(plain_key)
    
    new_key = APIKey(
        user_id=user.id,
        name=old_key.name,
        hashed_key=hashed_key,
        permissions=old_key.permissions,  # Reuse same permissions
        expires_at=new_expires_at,
        revoked=False
    )
    new_key.insert(db)
    
    return success_response(
        status_code=201,
        message="API key rolled over successfully",
        data={
            "api_key": plain_key,
            "expires_at": new_expires_at.isoformat(),
            "permissions": old_key.permissions
        }
    )