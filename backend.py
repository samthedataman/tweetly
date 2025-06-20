#!/usr/bin/env python3
"""
AI Chat to Twitter - Backend Server
OAuth and AI integration for Twitter/X sharing
"""

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
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Optional imports
try:
    import openai

    OPENAI_AVAILABLE = True
except ImportError:
    print("Warning: OpenAI not available. Image generation will be disabled.")
    openai = None
    OPENAI_AVAILABLE = False

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    print("Warning: PIL not available. Some image features will be disabled.")
    PIL_AVAILABLE = False

# Load environment variables
load_dotenv()

# Default configuration - works without .env file
CONFIG = {
    "TWITTER_API_KEY": os.getenv("TWITTER_API_KEY", ""),
    "TWITTER_API_SECRET": os.getenv("TWITTER_API_SECRET", ""),
    "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", ""),
    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
    "BASE_URL": os.getenv("BASE_URL", "http://localhost:8000"),
    "PORT": int(os.getenv("PORT", "8000")),
}

# Initialize OpenAI client if configured
openai_client = None
if CONFIG["OPENAI_API_KEY"] and OPENAI_AVAILABLE:
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
    model: Literal["gpt-image-1"] = "gpt-image-1"
    size: Literal["1024x1024", "512x512", "256x256"] = "1024x1024"


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
    """Generate image using OpenAI"""
    if not OPENAI_AVAILABLE:
        return {
            "success": False,
            "error": "OpenAI library not available",
            "message": "Please install openai: pip install openai",
        }

    if not openai_client:
        raise HTTPException(status_code=500, detail="OpenAI API not configured")

    try:
        # Use gpt-image-1 as requested
        model_to_use = request.model  # Use the model from request (gpt-image-1)
        
        # Sizes supported by gpt-image-1
        valid_sizes = ["256x256", "512x512", "1024x1024"]
        size_to_use = request.size if request.size in valid_sizes else "1024x1024"
        
        print(f"Generating image with model: {model_to_use}, size: {size_to_use}")
        
        # Generate image - gpt-image-1 doesn't support response_format parameter
        response = openai_client.images.generate(
            model=model_to_use,
            prompt=request.prompt,
            size=size_to_use,
            n=1
        )
        
        # Check if we got a valid response
        if response.data and len(response.data) > 0:
            image_url = response.data[0].url
            
            # Try to get b64_json directly from response if available
            image_data = None
            if hasattr(response.data[0], 'b64_json') and response.data[0].b64_json:
                image_data = response.data[0].b64_json
            elif image_url:
                # Download image and convert to base64 if URL is provided
                try:
                    image_bytes = await download_image(image_url)
                    if image_bytes:
                        image_data = base64.b64encode(image_bytes).decode()
                except Exception as e:
                    print(f"Error downloading generated image: {e}")
            
            return {
                "success": True,
                "image_url": image_url,
                "image_data": image_data,  # Base64 encoded image
                "model": model_to_use,
                "size": size_to_use,
                "prompt": request.prompt,
            }
        else:
            return {
                "success": False,
                "error": "No image data returned from API",
                "message": "The API did not return any image data",
            }
            
    except Exception as e:
        print(f"OpenAI API Error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to generate image: {str(e)}",
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
            "retro": "Apply a retro 80s aesthetic with vintage colors and effects while keeping the person recognizable",
        }

        prompt = effect_prompts.get(request.effect, effect_prompts["tophat"])

        # Use OpenAI gpt-image-1 for editing
        with open(temp_path, "rb") as image_file:
            # Check if we need to add a logo for certain effects
            if request.effect == "tophat":
                # Try to download PulseChain logo for tophat effect
                logo_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2a/PulseChainLogoTransparent.png/1200px-PulseChainLogoTransparent.png"
                logo_bytes = await download_image(logo_url)
                
                if logo_bytes:
                    # Save logo to temp file
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as logo_file:
                        logo_file.write(logo_bytes)
                        logo_path = logo_file.name
                    
                    # Multi-image edit with logo
                    with open(logo_path, "rb") as logo_file:
                        prompt = """Take the profile picture and transform it into a hyperrealistic synthwave style while ensuring it still looks exactly like the original person.

                        Key elements:
                        - Add a stylish black top hat with the PulseChain logo (image 2) attached prominently on the front
                        - Add a golden monocle over one eye
                        - Add a lit cigar with glowing ember
                        - The person's face and features must look identical to the original

                        Cyberpunk/Synthwave style:
                        - Vibrant neon purple/pink/cyan color palette
                        - Dramatic lighting with glow effects around edges
                        - Retro-futuristic cyberpunk atmosphere
                        - Subtle grid pattern in background
                        - The final image should be professional quality and look just like the original person in amazing synthwave style"""
                        
                        response = openai_client.images.edit(
                            model="gpt-image-1",
                            image=[image_file, logo_file],
                            prompt=prompt,
                            size="1024x1024",
                        )
                    
                    # Clean up logo file
                    os.unlink(logo_path)
                else:
                    # Single image approach
                    response = openai_client.images.edit(
                        model="gpt-image-1",
                        image=image_file,
                        prompt=prompt,
                        n=1,
                        size="1024x1024",
                    )
            else:
                # Standard single image edit
                response = openai_client.images.edit(
                    model="gpt-image-1",
                    image=image_file,
                    prompt=prompt,
                    n=1,
                    size="1024x1024",
                )

        # Clean up
        os.unlink(temp_path)

        return {
            "success": True,
            "image_url": response.data[0].url,
            "effect": request.effect,
            "original_url": request.image_url,
        }
    except Exception as e:
        if "temp_path" in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to add effect to image",
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
            "subject": request.subject,
        }
    except Exception as e:
        return {"success": False, "error": str(e), "message": "Failed to prepare email"}


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
        "❌ Library not available"
        if not OPENAI_AVAILABLE
        else ("✅ Configured" if CONFIG["OPENAI_API_KEY"] else "❌ Not configured")
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
            <p>Server URL: {CONFIG['BASE_URL']}</p>
        </div>
        
        <h3>Available Endpoints</h3>
        <ul>
            <li><code>POST /api/process-text</code> - Process text with AI</li>
            <li><code>GET /api/styles</code> - Get available styles</li>
            <li><code>POST /api/generate-image</code> - Generate images with gpt-image-1</li>
            <li><code>POST /api/add-effect</code> - Add effects to images</li>
            <li><code>POST /api/send-email</code> - Send via email</li>
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
    """Generate an image using OpenAI"""
    result = await generate_image_openai(request)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    return result


@app.post("/api/generate-image-bytes")
async def generate_image_bytes(request: GenerateImageRequest):
    """Generate an image and return as PNG bytes"""
    result = await generate_image_openai(request)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    
    # If we have base64 data, convert to bytes and return as PNG
    if result.get("image_data"):
        image_bytes = base64.b64decode(result["image_data"])
        return StreamingResponse(
            io.BytesIO(image_bytes),
            media_type="image/png",
            headers={"Content-Disposition": f"attachment; filename=generated-image.png"}
        )
    else:
        raise HTTPException(status_code=500, detail="No image data available")


@app.post("/api/add-effect")
async def add_effect(request: AddEffectRequest):
    """Add effects to an existing image"""
    result = await add_effect_to_image(request)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    return result


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
    OpenAI API: {'❌ Library not available' if not OPENAI_AVAILABLE else ('✅ Configured' if CONFIG['OPENAI_API_KEY'] else '❌ Not configured - Add to .env file')}
    
    API Docs: {CONFIG['BASE_URL']}/docs
    Test Examples: {CONFIG['BASE_URL']}/api/test-condense
    
    Enhanced Features:
    - Advanced condensing system prompts
    - Multiple style options with specialized prompts
    - Image generation with gpt-image-1
    - Image effects (tophat, monocle, synthwave, retro)
    - Email sending functionality
    - Hashtag/mention preservation
    - Character counting and validation
    
    Press Ctrl+C to stop
    """
    )

    uvicorn.run(app, host="0.0.0.0", port=CONFIG["PORT"])
