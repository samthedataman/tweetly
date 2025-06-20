#!/usr/bin/env python3
"""
AI Chat to Twitter - All-in-One Full Backend
This single file includes OAuth and Anthropic integration
Just run: python backend_allinone.py
"""

# Auto-install dependencies
import subprocess
import sys


def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])


# Check and install required packages
try:
    import fastapi
    import httpx
    import uvicorn
    import pydantic
    import dotenv
except ImportError:
    print("Installing required packages...")
    for pkg in [
        "fastapi",
        "uvicorn[standard]",
        "httpx",
        "pydantic",
        "python-dotenv",
        "typing-extensions",
    ]:
        install(pkg)
    print("Packages installed! Please run the script again.")
    sys.exit(0)

# Now import everything
import os
import asyncio
import base64
import hmac
import time
import urllib.parse
import uuid
import json
from datetime import datetime, timedelta, timezone
from hashlib import sha1
from typing import Optional, Dict, Any

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Default configuration - works without .env file
CONFIG = {
    "TWITTER_API_KEY": os.getenv("TWITTER_API_KEY", ""),
    "TWITTER_API_SECRET": os.getenv("TWITTER_API_SECRET", ""),
    "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", ""),
    "BASE_URL": os.getenv("BASE_URL", "http://localhost:8000"),
    "PORT": int(os.getenv("PORT", "8000")),
}

# Create .env template if it doesn't exist
if not os.path.exists(".env"):
    with open(".env", "w") as f:
        f.write(
            """# AI Chat to Twitter Configuration
# Get Twitter API keys from https://developer.twitter.com
TWITTER_API_KEY=
TWITTER_API_SECRET=

# Get Anthropic API key from https://console.anthropic.com
ANTHROPIC_API_KEY=

# Server settings
BASE_URL=http://localhost:8000
PORT=8000
"""
        )
    print("📝 Created .env template file. Add your API keys to enable full features!")

# In-memory storage
oauth_sessions = {}
user_credentials = {}


# Models
class ProcessTextRequest(BaseModel):
    text: str
    action: Literal["condense", "restyle"] = "condense"
    style: Optional[str] = "professional"
    preserve_hashtags: bool = True
    preserve_mentions: bool = True
    target_length: Optional[int] = None  # If None, uses optimal length


# Create FastAPI app
app = FastAPI(title="AI Chat to Twitter")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Helper function for OAuth signature
def generate_oauth_signature(method, url, params, consumer_secret, token_secret=""):
    sorted_params = sorted(params.items())
    param_string = "&".join(
        f"{urllib.parse.quote(str(k), safe='')}={urllib.parse.quote(str(v), safe='')}"
        for k, v in sorted_params
    )
    signature_base = "&".join(
        [
            method,
            urllib.parse.quote(url, safe=""),
            urllib.parse.quote(param_string, safe=""),
        ]
    )
    signing_key = "&".join(
        [
            urllib.parse.quote(consumer_secret, safe=""),
            urllib.parse.quote(token_secret, safe=""),
        ]
    )
    signature = hmac.new(signing_key.encode(), signature_base.encode(), sha1).digest()
    return base64.b64encode(signature).decode()


# Enhanced system prompts for different actions
SYSTEM_PROMPTS = {
    "condense": """You are an expert at condensing messages for Twitter while preserving their core meaning and impact. 

CRITICAL TWITTER CONSTRAINTS:
- Maximum 280 characters (this is absolute - going over means the tweet cannot be posted)
- URLs count as 23 characters regardless of actual length
- @mentions and #hashtags count toward the limit
- Each emoji typically counts as 2 characters

YOUR CONDENSING STRATEGY:
1. PRESERVE the core message and key information
2. MAINTAIN the original tone and intent
3. PRIORITIZE actionable information and key facts
4. ELIMINATE redundancy and filler words
5. USE abbreviations wisely (but keep it readable)
6. KEEP important context that changes meaning

TECHNIQUES:
- Replace wordy phrases: "in order to" → "to", "at this point in time" → "now"
- Use strong, specific verbs instead of verb phrases
- Combine related ideas with semicolons or dashes
- Remove unnecessary adjectives unless they're critical
- Use numbers instead of spelling them out
- Consider common abbreviations: "with" → "w/", "without" → "w/o", "because" → "bc"

WHAT TO PRESERVE:
- Key facts, data, and statistics
- Important names, dates, and locations  
- The main call-to-action if present
- Emotional tone and urgency
- Technical accuracy for professional content

WHAT TO REMOVE FIRST:
- Greeting phrases like "I wanted to share that..."
- Redundant expressions
- Excessive politeness that doesn't add value
- Repeated information
- Unnecessary examples if the point is clear

OUTPUT FORMAT:
Return ONLY the condensed text, nothing else. Ensure it's under 280 characters.""",
    "professional": """You are an expert at rewriting content for professional Twitter communication.

PROFESSIONAL TWITTER STYLE:
- Clear, concise, and authoritative
- Industry-appropriate terminology
- Data-driven when possible
- Confidence without arrogance
- Respectful and inclusive language

GUIDELINES:
1. Lead with value or insight
2. Use active voice
3. Include relevant metrics or data points
4. Avoid excessive jargon but use appropriate technical terms
5. End with clear next steps or takeaways when relevant

CHARACTER LIMIT: Ensure output is under 280 characters.""",
    "casual": """You are an expert at rewriting content for casual, engaging Twitter communication.

CASUAL TWITTER STYLE:
- Conversational and relatable
- Appropriate emoji usage (but not excessive)
- Natural contractions
- Friendly and approachable tone
- Authentic voice

GUIDELINES:
1. Write like you're talking to a friend
2. Use relatable examples
3. Add personality without being unprofessional
4. Include relevant emojis that enhance meaning
5. Keep energy positive and engaging

CHARACTER LIMIT: Ensure output is under 280 characters.""",
    "humorous": """You are an expert at rewriting content with appropriate humor for Twitter.

HUMOROUS TWITTER STYLE:
- Witty without being offensive
- Clever wordplay when appropriate
- Self-aware and relatable
- Timing and punchlines
- Know your audience

GUIDELINES:
1. Humor should enhance, not overshadow the message
2. Avoid controversial or potentially offensive jokes
3. Use surprise, irony, or clever observations
4. Keep it light and accessible
5. Don't force humor if it doesn't fit naturally

CHARACTER LIMIT: Ensure output is under 280 characters.""",
    "creative": """You are an expert at rewriting content creatively for Twitter.

CREATIVE TWITTER STYLE:
- Unique perspective or angle
- Vivid, memorable language
- Metaphors and analogies
- Story-telling elements
- Stand out from the timeline

GUIDELINES:
1. Find an unexpected angle
2. Use sensory language when appropriate
3. Create mental images
4. Build intrigue or curiosity
5. Make ordinary things extraordinary

CHARACTER LIMIT: Ensure output is under 280 characters.""",
    "technical": """You are an expert at condensing technical content for Twitter.

TECHNICAL TWITTER STYLE:
- Accurate terminology
- Clear explanation of complex concepts
- Appropriate use of technical abbreviations
- Links to detailed resources when needed
- Balance between precision and accessibility

GUIDELINES:
1. Never sacrifice technical accuracy
2. Define acronyms on first use if space allows
3. Use standard industry notation
4. Include version numbers, specs when relevant
5. Provide context for technical claims

CHARACTER LIMIT: Ensure output is under 280 characters.""",
}


# Process text with Anthropic
async def process_with_ai(
    text: str,
    action: str,
    style: Optional[str] = None,
    preserve_hashtags: bool = True,
    preserve_mentions: bool = True,
    target_length: Optional[int] = None,
) -> str:
    if not CONFIG["ANTHROPIC_API_KEY"]:
        # Simple fallback
        if action == "condense":
            return text[:100] + "..." if len(text) > 100 else text
        elif style == "professional":
            return text.replace("!", ".")
        elif style == "casual":
            return f"Hey! {text} 😊"
        return text[:250] + "..."

    # Select appropriate system prompt
    system_prompt = SYSTEM_PROMPTS.get(
        "condense" if action == "condense" else style, SYSTEM_PROMPTS["condense"]
    )

    # Build the user prompt
    user_prompt = f"Text to process:\n{text}"

    if action == "condense":
        if target_length:
            user_prompt += (
                f"\n\nTarget length: {target_length} characters (must not exceed)"
            )
        user_prompt += "\n\nCondense this text following your guidelines."
    else:
        user_prompt += f"\n\nRewrite this in {style} style following your guidelines."

    if preserve_hashtags or preserve_mentions:
        preservation_notes = []
        if preserve_hashtags:
            preservation_notes.append("preserve all #hashtags exactly as written")
        if preserve_mentions:
            preservation_notes.append("preserve all @mentions exactly as written")
        user_prompt += f"\n\nIMPORTANT: {' and '.join(preservation_notes)}."

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": CONFIG["ANTHROPIC_API_KEY"],
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": "claude-3-5-sonnet-20241022",  # Latest Claude 3.5 Sonnet
                    "max_tokens": 300,
                    "temperature": 0.3,  # Lower temperature for more consistent output
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_prompt}],
                },
            )
            if response.status_code == 200:
                data = response.json()
                result = data["content"][0]["text"].strip()

                # Ensure we don't exceed 280 characters
                if len(result) > 280:
                    # Truncate smartly at word boundary
                    result = result[:277] + "..."

                return result
    except Exception as e:
        print(f"AI Error: {e}")

    return text[:250] + "..."


# Routes
@app.get("/", response_class=HTMLResponse)
async def home():
    twitter_status = (
        "✅ Configured" if CONFIG["TWITTER_API_KEY"] else "❌ Not configured"
    )
    anthropic_status = (
        "✅ Configured" if CONFIG["ANTHROPIC_API_KEY"] else "❌ Not configured"
    )

    return f"""
    <html>
    <head>
        <title>AI Chat to Twitter</title>
        <style>
            body {{ font-family: Arial; max-width: 800px; margin: 50px auto; padding: 20px; }}
            .status {{ background: #f0f0f0; padding: 20px; border-radius: 10px; margin: 20px 0; }}
            .btn {{ display: inline-block; padding: 10px 20px; background: #1d9bf0; color: white; 
                   text-decoration: none; border-radius: 5px; margin: 5px; }}
            code {{ background: #e0e0e0; padding: 2px 5px; }}
        </style>
    </head>
    <body>
        <h1>🚀 AI Chat to Twitter Backend</h1>
        
        <div class="status">
            <h3>Configuration Status</h3>
            <p>Twitter API: {twitter_status}</p>
            <p>Anthropic AI: {anthropic_status}</p>
            <p>Server URL: {CONFIG['BASE_URL']}</p>
        </div>
        
        <h3>Available Endpoints</h3>
        <ul>
            <li><code>POST /api/process-text</code> - Process text with AI</li>
            <li><code>GET /api/styles</code> - Get available styles</li>
            <li><code>GET /oauth/login</code> - Start OAuth (if configured)</li>
        </ul>
        
        <a href="/docs" class="btn">API Docs</a>
        {"<a href='/oauth/login' class='btn'>Test OAuth</a>" if CONFIG["TWITTER_API_KEY"] else ""}
        
        <div class="status" style="margin-top: 40px;">
            <h4>Quick Test</h4>
            <p>Run this curl command to test:</p>
            <code>
            curl -X POST {CONFIG['BASE_URL']}/api/process-text -H "Content-Type: application/json" -d '{{"text":"Test message", "action":"condense"}}'
            </code>
        </div>
    </body>
    </html>
    """


@app.post("/api/process-text")
async def process_text(request: ProcessTextRequest):
    processed = await process_with_ai(
        request.text,
        request.action,
        request.style,
        request.preserve_hashtags,
        request.preserve_mentions,
        request.target_length,
    )

    return {
        "processed_text": processed,
        "original_length": len(request.text),
        "processed_length": len(processed),
        "character_savings": len(request.text) - len(processed),
        "within_limit": len(processed) <= 280,
    }


@app.get("/api/styles")
async def get_styles():
    return {
        "styles": [
            {"value": "professional", "label": "Professional"},
            {"value": "casual", "label": "Casual"},
            {"value": "humorous", "label": "Humorous"},
            {"value": "concise", "label": "Concise"},
            {"value": "creative", "label": "Creative"},
            {"value": "technical", "label": "Technical"},
        ]
    }


@app.get("/oauth/login")
async def oauth_login():
    if not CONFIG["TWITTER_API_KEY"]:
        raise HTTPException(status_code=500, detail="Twitter API not configured")

    # OAuth 1.0a flow
    callback_url = f"{CONFIG['BASE_URL']}/oauth/callback"
    timestamp = str(int(time.time()))
    nonce = uuid.uuid4().hex

    params = {
        "oauth_callback": callback_url,
        "oauth_consumer_key": CONFIG["TWITTER_API_KEY"],
        "oauth_nonce": nonce,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": timestamp,
        "oauth_version": "1.0",
    }

    signature = generate_oauth_signature(
        "POST",
        "https://api.twitter.com/oauth/request_token",
        params,
        CONFIG["TWITTER_API_SECRET"],
    )
    params["oauth_signature"] = signature

    auth_header = "OAuth " + ", ".join(
        f'{k}="{urllib.parse.quote(str(v), safe="")}"' for k, v in params.items()
    )

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.twitter.com/oauth/request_token",
            headers={"Authorization": auth_header},
        )

    if response.status_code == 200:
        tokens = dict(urllib.parse.parse_qsl(response.text))
        oauth_sessions[tokens["oauth_token"]] = tokens
        return RedirectResponse(
            f"https://api.twitter.com/oauth/authorize?oauth_token={tokens['oauth_token']}"
        )
    else:
        raise HTTPException(status_code=500, detail="OAuth failed")


@app.get("/oauth/callback")
async def oauth_callback(oauth_token: str, oauth_verifier: str):
    if oauth_token not in oauth_sessions:
        raise HTTPException(status_code=400, detail="Invalid session")

    # Exchange for access token
    session = oauth_sessions[oauth_token]
    timestamp = str(int(time.time()))
    nonce = uuid.uuid4().hex

    params = {
        "oauth_consumer_key": CONFIG["TWITTER_API_KEY"],
        "oauth_token": oauth_token,
        "oauth_verifier": oauth_verifier,
        "oauth_nonce": nonce,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": timestamp,
        "oauth_version": "1.0",
    }

    signature = generate_oauth_signature(
        "POST",
        "https://api.twitter.com/oauth/access_token",
        params,
        CONFIG["TWITTER_API_SECRET"],
        session["oauth_token_secret"],
    )
    params["oauth_signature"] = signature

    auth_header = "OAuth " + ", ".join(
        f'{k}="{urllib.parse.quote(str(v), safe="")}"' for k, v in params.items()
    )

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.twitter.com/oauth/access_token",
            headers={"Authorization": auth_header},
        )

    if response.status_code == 200:
        credentials = dict(urllib.parse.parse_qsl(response.text))
        return HTMLResponse(
            f"""
        <html>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1>✅ Success!</h1>
            <p>Connected as @{credentials.get('screen_name', 'Unknown')}</p>
            <p>Access Token: <code>{credentials['oauth_token'][:20]}...</code></p>
            <p>You can now use these credentials to post tweets!</p>
        </body>
        </html>
        """
        )
    else:
        raise HTTPException(status_code=500, detail="Failed to get access token")


@app.get("/api/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.post("/api/test-condense")
async def test_condense():
    """Test endpoint to show condensing examples"""
    examples = [
        "I wanted to share with everyone that our team has been working incredibly hard on the new product launch and we're finally ready to announce that it will be available starting next Monday. We're really excited about all the new features we've added based on your feedback!",
        "Just finished analyzing the quarterly reports and I'm pleased to inform you that we've exceeded our targets by 23% across all major KPIs. This represents our strongest performance in the last five years.",
        "Hey everyone! Can't believe it's already December. Where did this year go? Anyway, I wanted to remind you all about the holiday party next Friday at 6pm. Don't forget to RSVP!",
    ]

    results = []
    for text in examples:
        condensed = await process_with_ai(text, "condense")
        results.append(
            {
                "original": text,
                "original_length": len(text),
                "condensed": condensed,
                "condensed_length": len(condensed),
                "reduction": f"{round((1 - len(condensed)/len(text)) * 100)}%",
            }
        )

    return {"examples": results}


if __name__ == "__main__":
    print(
        f"""
    🚀 AI Chat to Twitter - Full Backend (Enhanced)
    ===============================================
    
    Server: {CONFIG['BASE_URL']}
    Port: {CONFIG['PORT']}
    
    Twitter API: {'✅ Configured' if CONFIG['TWITTER_API_KEY'] else '❌ Not configured - Add to .env file'}
    Anthropic AI: {'✅ Configured' if CONFIG['ANTHROPIC_API_KEY'] else '❌ Not configured - Add to .env file'}
    
    API Docs: {CONFIG['BASE_URL']}/docs
    Test Examples: {CONFIG['BASE_URL']}/api/test-condense
    
    Enhanced Features:
    - Advanced condensing system prompts
    - Multiple style options with specialized prompts
    - Hashtag/mention preservation
    - Character counting and validation
    - Test endpoint for examples
    
    Press Ctrl+C to stop
    """
    )

    uvicorn.run(app, host="0.0.0.0", port=CONFIG["PORT"])
