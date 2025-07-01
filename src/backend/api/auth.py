"""Authentication utilities for Contextly backend"""
import os
import jwt
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from fastapi import HTTPException, Header, Depends
from web3 import Web3
from eth_account.messages import encode_defunct

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# JWT configuration
JWT_SECRET = os.getenv("JWT_SECRET", "contextly-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24 * 7  # 1 week

def verify_wallet_signature(wallet: str, signature: str, message: str) -> bool:
    """Verify Ethereum wallet signature"""
    try:
        logger.info(f"🔐 Verifying signature for wallet: {wallet}")
        w3 = Web3()
        
        # Encode the message
        encoded_message = encode_defunct(text=message)
        
        # Recover the address from signature
        recovered_address = w3.eth.account.recover_message(
            encoded_message, signature=signature
        )
        
        # Compare addresses (case-insensitive)
        is_valid = recovered_address.lower() == wallet.lower()
        
        if is_valid:
            logger.info(f"✅ Signature valid for wallet: {wallet}")
        else:
            logger.warning(f"❌ Invalid signature for wallet: {wallet}")
            
        return is_valid
    except Exception as e:
        logger.error(f"❌ Signature verification error: {str(e)}")
        return False

def create_access_token(wallet: str, user_id: str) -> str:
    """Create JWT access token for authenticated wallet"""
    payload = {
        "wallet": wallet,
        "user_id": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    logger.info(f"🎫 Created JWT token for wallet: {wallet}")
    return token

def verify_access_token(token: str) -> Dict[str, Any]:
    """Verify and decode JWT access token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        logger.info(f"✅ Valid token for wallet: {payload.get('wallet')}")
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("❌ Token expired")
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        logger.warning(f"❌ Invalid token: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(
    authorization: Optional[str] = Header(None),
    x_wallet_address: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """Get current authenticated user from JWT token or wallet header"""
    
    # Log all auth attempts
    logger.info(f"🔍 Auth attempt - Authorization: {bool(authorization)}, X-Wallet-Address: {x_wallet_address}")
    
    # Try JWT token first
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        
        # Skip obviously invalid temporary tokens
        if token.startswith("temp_token_"):
            logger.warning(f"❌ Rejecting temporary token: {token[:20]}...")
            raise HTTPException(
                status_code=401,
                detail="Invalid temporary token. Please reconnect your wallet."
            )
        
        try:
            user_data = verify_access_token(token)
            logger.info(f"✅ Authenticated via JWT: {user_data.get('wallet')}")
            return user_data
        except HTTPException:
            pass  # Fall through to wallet header
    
    # Try wallet address header (for backwards compatibility)
    if x_wallet_address and x_wallet_address != "anonymous":
        logger.info(f"⚠️ Using legacy wallet header auth: {x_wallet_address}")
        return {
            "wallet": x_wallet_address,
            "user_id": f"legacy_{x_wallet_address}",
            "legacy": True
        }
    
    logger.warning("❌ No valid authentication found")
    raise HTTPException(
        status_code=401,
        detail="Not authenticated. Please provide Bearer token or X-Wallet-Address header"
    )

async def get_optional_user(
    authorization: Optional[str] = Header(None),
    x_wallet_address: Optional[str] = Header(None)
) -> Optional[Dict[str, Any]]:
    """Get current user if authenticated, otherwise return None"""
    try:
        return await get_current_user(authorization, x_wallet_address)
    except HTTPException:
        return None