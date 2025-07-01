"""Twitter/X OAuth implementation using authlib"""
import os
from authlib.integrations.starlette_client import OAuth, OAuthError
from starlette.config import Config
from starlette.responses import RedirectResponse
import json
from datetime import datetime, timezone

# OAuth configuration
config = Config('.env')
oauth = OAuth(config)

# Register Twitter OAuth client
oauth.register(
    name='twitter',
    client_id=os.getenv('TWITTER_CLIENT_ID', 'dummy_client_id'),
    client_secret=os.getenv('TWITTER_CLIENT_SECRET', 'dummy_client_secret'),
    access_token_url='https://api.twitter.com/2/oauth2/token',
    access_token_params=None,
    authorize_url='https://twitter.com/i/oauth2/authorize',
    authorize_params=None,
    api_base_url='https://api.twitter.com/2/',
    client_kwargs={
        'scope': 'tweet.read users.read offline.access',
        'code_challenge_method': 'S256',
    },
)

async def create_twitter_login_url(request, redis_client, wallet_address=None):
    """Create Twitter OAuth login URL"""
    # For development without real Twitter API keys
    if os.getenv('TWITTER_CLIENT_ID') == 'dummy_client_id':
        # Return development OAuth URL
        import uuid
        session_id = str(uuid.uuid4())
        
        # Store session data
        session_data = {
            "session_id": session_id,
            "wallet_address": wallet_address,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "state": "pending"
        }
        
        await redis_client.set(
            f"x_auth_session:{session_id}",
            json.dumps(session_data),
            ex=3600  # 1 hour expiry
        )
        
        # Return development auth URL
        return {
            "auth_url": f"{os.getenv('BASE_URL', 'http://localhost:8000')}/v1/auth/x/dev?session_id={session_id}",
            "session_id": session_id,
            "state": "pending"
        }
    
    # Production OAuth flow
    redirect_uri = f"{os.getenv('BASE_URL', 'http://localhost:8000')}/v1/auth/x/callback"
    
    # Store wallet address in session for callback
    if wallet_address:
        request.session['wallet_address'] = wallet_address
    
    return await oauth.twitter.authorize_redirect(request, redirect_uri)

async def handle_twitter_callback(request, redis_client):
    """Handle Twitter OAuth callback"""
    try:
        # For development mode
        if request.query_params.get('dev_mode'):
            session_id = request.query_params.get('session_id')
            username = request.query_params.get('username', 'test_user')
            
            # Get session data
            session_data = await redis_client.get(f"x_auth_session:{session_id}")
            if not session_data:
                return {"error": "Invalid session"}
            
            session = json.loads(session_data)
            
            # Create user data
            x_user_data = {
                "x_id": f"dev_{username}",
                "x_username": username,
                "x_name": f"{username} (Dev)",
                "linked_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Store X account link with wallet
            if session.get("wallet_address"):
                await redis_client.set(
                    f"x_link:{session['wallet_address']}",
                    json.dumps(x_user_data),
                    ex=None  # No expiry
                )
            
            return {
                "status": "success",
                "x_user_data": x_user_data
            }
        
        # Production OAuth flow
        token = await oauth.twitter.authorize_access_token(request)
        
        # Get user info from Twitter
        resp = await oauth.twitter.get('users/me', token=token)
        user_data = resp.json()
        
        # Get wallet address from session
        wallet_address = request.session.get('wallet_address')
        
        # Create user data
        x_user_data = {
            "x_id": user_data['data']['id'],
            "x_username": user_data['data']['username'],
            "x_name": user_data['data']['name'],
            "linked_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Store X account link
        if wallet_address:
            await redis_client.set(
                f"x_link:{wallet_address}",
                json.dumps(x_user_data),
                ex=None  # No expiry
            )
        
        return {
            "status": "success",
            "x_user_data": x_user_data
        }
        
    except OAuthError as error:
        return {"error": str(error)}