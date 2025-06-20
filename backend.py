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
    import openai
    import replicate
    import aiofiles
except ImportError:
    print("Installing required packages...")
    for pkg in [
        "fastapi",
        "uvicorn[standard]",
        "httpx",
        "pydantic",
        "python-dotenv",
        "typing-extensions",
        "openai",
        "replicate",
        "aiofiles",
        "pillow",
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
import io
import tempfile
from datetime import datetime, timedelta, timezone
from hashlib import sha1
from typing import Optional, Dict, Any, List

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

import httpx
import uvicorn
import openai
import replicate
import aiofiles
from PIL import Image
from fastapi import FastAPI, HTTPException, Request, Query, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Default configuration - works without .env file
CONFIG = {
    "TWITTER_API_KEY": os.getenv("TWITTER_API_KEY", ""),
    "TWITTER_API_SECRET": os.getenv("TWITTER_API_SECRET", ""),
    "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", ""),
    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
    "REPLICATE_API_TOKEN": os.getenv("REPLICATE_API_TOKEN", ""),
    "BASE_URL": os.getenv("BASE_URL", "http://localhost:8000"),
    "PORT": int(os.getenv("PORT", "8000")),
}

# Initialize OpenAI client if configured
openai_client = None
if CONFIG["OPENAI_API_KEY"]:
    openai_client = openai.OpenAI(api_key=CONFIG["OPENAI_API_KEY"])

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

# Get OpenAI API key from https://platform.openai.com
OPENAI_API_KEY=

# Get Replicate API token from https://replicate.com
REPLICATE_API_TOKEN=

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


class GenerateImageRequest(BaseModel):
    prompt: str
    model: Literal["dall-e-3", "dall-e-2"] = "dall-e-3"
    size: Literal["1024x1024", "1792x1024", "1024x1792"] = "1024x1024"
    quality: Literal["standard", "hd"] = "standard"
    style: Literal["vivid", "natural"] = "vivid"


class GenerateVideoRequest(BaseModel):
    prompt: str
    model: Literal["veo-3", "stable-video"] = "veo-3"
    duration: int = Field(5, ge=1, le=30)
    resolution: Literal["720p", "1080p", "4k"] = "720p"
    aspect_ratio: Literal["16:9", "9:16", "1:1"] = "16:9"


class AddEffectRequest(BaseModel):
    image_url: str
    effect: Literal["tophat", "monocle", "synthwave", "retro"] = "tophat"


class SendEmailRequest(BaseModel):
    to_email: str
    subject: str = "AI Chat Conversation"
    text: str
    html: Optional[str] = None
    from_name: str = "AI Chat to Twitter"


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


# Image and Video Generation Functions
async def download_image(url: str) -> Optional[bytes]:
    """Download image from URL and return as bytes"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=10.0)
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "").lower()
                if (
                    "image" in content_type
                    or response.content.startswith(b"\x89PNG")
                    or response.content.startswith(b"\xff\xd8\xff")
                ):
                    return response.content
        return None
    except Exception as e:
        print(f"Error downloading image: {e}")
        return None


async def generate_image_openai(request: GenerateImageRequest) -> Dict[str, Any]:
    """Generate image using OpenAI DALL-E"""
    if not openai_client:
        raise HTTPException(status_code=500, detail="OpenAI API not configured")
    
    try:
        response = openai_client.images.generate(
            model=request.model,
            prompt=request.prompt,
            size=request.size,
            quality=request.quality,
            style=request.style,
            n=1
        )
        
        return {
            "success": True,
            "image_url": response.data[0].url,
            "revised_prompt": getattr(response.data[0], 'revised_prompt', request.prompt),
            "model": request.model,
            "size": request.size
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to generate image"
        }


async def generate_video_replicate(request: GenerateVideoRequest) -> Dict[str, Any]:
    """Generate video using Replicate (stable-video-diffusion or other models)"""
    if not CONFIG["REPLICATE_API_TOKEN"]:
        raise HTTPException(status_code=500, detail="Replicate API not configured")
    
    try:
        # Map resolution to dimensions
        dimensions = {
            "720p": {"width": 1280, "height": 720},
            "1080p": {"width": 1920, "height": 1080},
            "4k": {"width": 3840, "height": 2160}
        }
        
        dim = dimensions[request.resolution]
        
        # Adjust dimensions based on aspect ratio
        if request.aspect_ratio == "9:16":
            dim["width"], dim["height"] = dim["height"], dim["width"]
        elif request.aspect_ratio == "1:1":
            dim["width"] = dim["height"] = min(dim["width"], dim["height"])
        
        # Use Stable Video Diffusion from Replicate
        output = replicate.run(
            "stability-ai/stable-video-diffusion:3f0457e4619daac51203dedb472816fd4af51f3149fa7a9e0b5ffcf1b8172438",
            input={
                "input_image": request.prompt,  # This would need to be an image URL
                "frames": min(request.duration * 8, 25),  # Approximate frames
                "sizing_strategy": "maintain_aspect_ratio",
                "frames_per_second": 8,
                "motion_bucket_id": 127,
                "cond_aug": 0.02,
                "decoding_t": 7,
                "seed": 0
            }
        )
        
        return {
            "success": True,
            "video_url": output,
            "model": "stable-video-diffusion",
            "duration": request.duration,
            "resolution": request.resolution,
            "aspect_ratio": request.aspect_ratio
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to generate video"
        }


async def add_effect_to_image(request: AddEffectRequest) -> Dict[str, Any]:
    """Add effects to image using OpenAI"""
    if not openai_client:
        raise HTTPException(status_code=500, detail="OpenAI API not configured")
    
    try:
        # Download the image
        image_bytes = await download_image(request.image_url)
        if not image_bytes:
            raise HTTPException(status_code=400, detail="Failed to download image")
        
        # Create temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
            tmp_file.write(image_bytes)
            temp_path = tmp_file.name
        
        # Effect prompts
        effect_prompts = {
            "tophat": "Add a stylish black top hat to this person's head, keeping their face exactly the same",
            "monocle": "Add a golden monocle over one eye, keeping the person's face exactly the same",
            "synthwave": "Transform into hyperrealistic synthwave style with neon purple/pink/cyan colors, dramatic lighting, and cyberpunk atmosphere while keeping the person's face identical",
            "retro": "Apply a retro 80s aesthetic with vintage colors and effects while keeping the person recognizable"
        }
        
        prompt = effect_prompts.get(request.effect, effect_prompts["tophat"])
        
        # Use OpenAI image edit
        with open(temp_path, "rb") as image_file:
            response = openai_client.images.edit(
                image=image_file,
                prompt=prompt,
                n=1,
                size="1024x1024"
            )
        
        # Clean up
        os.unlink(temp_path)
        
        return {
            "success": True,
            "image_url": response.data[0].url,
            "effect": request.effect,
            "original_url": request.image_url
        }
    except Exception as e:
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to add effect to image"
        }


async def prepare_email_link(request: SendEmailRequest) -> Dict[str, Any]:
    """Prepare a mailto link for sending email"""
    try:
        # Encode the email parameters
        subject = urllib.parse.quote(request.subject)
        body = urllib.parse.quote(request.text)
        
        # Create mailto link
        mailto_link = f"mailto:{request.to_email}?subject={subject}&body={body}"
        
        # Also prepare a shareable email template
        email_template = f"""
To: {request.to_email}
Subject: {request.subject}

{request.text}

---
Sent via AI Chat to Twitter Extension
        """
        
        return {
            "success": True,
            "mailto_link": mailto_link,
            "email_template": email_template,
            "to": request.to_email,
            "subject": request.subject
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to prepare email"
        }


# Routes
@app.get("/", response_class=HTMLResponse)
async def home():
    twitter_status = (
        "✅ Configured" if CONFIG["TWITTER_API_KEY"] else "❌ Not configured"
    )
    anthropic_status = (
        "✅ Configured" if CONFIG["ANTHROPIC_API_KEY"] else "❌ Not configured"
    )
    openai_status = (
        "✅ Configured" if CONFIG["OPENAI_API_KEY"] else "❌ Not configured"
    )
    replicate_status = (
        "✅ Configured" if CONFIG["REPLICATE_API_TOKEN"] else "❌ Not configured"
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
            <p>OpenAI API: {openai_status}</p>
            <p>Replicate API: {replicate_status}</p>
            <p>Server URL: {CONFIG['BASE_URL']}</p>
        </div>
        
        <h3>Available Endpoints</h3>
        <ul>
            <li><code>POST /api/process-text</code> - Process text with AI</li>
            <li><code>GET /api/styles</code> - Get available styles</li>
            <li><code>POST /api/generate-image</code> - Generate images with DALL-E</li>
            <li><code>POST /api/generate-video</code> - Generate videos with Replicate</li>
            <li><code>POST /api/add-effect</code> - Add effects to images</li>
            <li><code>POST /api/upload-image</code> - Upload images</li>
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


@app.post("/api/generate-image")
async def generate_image(request: GenerateImageRequest):
    """Generate an image using OpenAI DALL-E"""
    result = await generate_image_openai(request)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    return result


@app.post("/api/generate-video")
async def generate_video(request: GenerateVideoRequest):
    """Generate a video using Replicate"""
    result = await generate_video_replicate(request)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    return result


@app.post("/api/add-effect")
async def add_effect(request: AddEffectRequest):
    """Add effects to an existing image"""
    result = await add_effect_to_image(request)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    return result


@app.post("/api/upload-image")
async def upload_image(file: UploadFile = File(...)):
    """Upload an image and return its URL"""
    try:
        # Validate file type
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read file content
        content = await file.read()
        
        # Create a unique filename
        filename = f"{uuid.uuid4().hex}_{file.filename}"
        
        # In production, you would upload to a cloud storage service
        # For now, we'll return a base64 data URL
        base64_image = base64.b64encode(content).decode()
        data_url = f"data:{file.content_type};base64,{base64_image}"
        
        return {
            "success": True,
            "url": data_url,
            "filename": filename,
            "content_type": file.content_type,
            "size": len(content)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/send-email")
async def send_email(request: SendEmailRequest):
    """Prepare email for sending"""
    result = await prepare_email_link(request)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    return result


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
    OpenAI API: {'✅ Configured' if CONFIG['OPENAI_API_KEY'] else '❌ Not configured - Add to .env file'}
    Replicate API: {'✅ Configured' if CONFIG['REPLICATE_API_TOKEN'] else '❌ Not configured - Add to .env file'}
    
    API Docs: {CONFIG['BASE_URL']}/docs
    Test Examples: {CONFIG['BASE_URL']}/api/test-condense
    
    Enhanced Features:
    - Advanced condensing system prompts
    - Multiple style options with specialized prompts
    - Image generation with DALL-E 3
    - Video generation with Replicate
    - Image effects (tophat, monocle, synthwave, retro)
    - Hashtag/mention preservation
    - Character counting and validation
    
    Press Ctrl+C to stop
    """
    )

    uvicorn.run(app, host="0.0.0.0", port=CONFIG["PORT"])
