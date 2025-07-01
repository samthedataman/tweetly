#!/usr/bin/env python3
"""
Contextly.ai Enhanced Backend with LanceDB, GraphRAG, and Advanced Features
"""

import os
import asyncio
import json
import uuid
import base64
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Tuple

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal
from collections import defaultdict
import re
import random
import urllib.parse

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Header, Depends, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import jwt
import httpx
from openai import AsyncOpenAI
import lancedb
from web3 import Web3
from eth_account.messages import encode_defunct
from auth import (
    verify_wallet_signature,
    create_access_token,
    get_current_user,
    get_optional_user,
    logger as auth_logger,
)
import numpy as np
import pandas as pd
import networkx as nx
from sklearn.cluster import HDBSCAN
import tiktoken
from sentence_transformers import SentenceTransformer
import torch

# Load environment variables
load_dotenv()

# Configuration
CONFIG = {
    "LANCEDB_URI": os.getenv("LANCEDB_URI"),
    "LANCEDB_API_KEY": os.getenv("LANCEDB_API_KEY"),
    "UPSTASH_REDIS_REST_URL": os.getenv("UPSTASH_REDIS_REST_URL"),
    "UPSTASH_REDIS_REST_TOKEN": os.getenv("UPSTASH_REDIS_REST_TOKEN"),
    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
    "JWT_SECRET": os.getenv("JWT_SECRET", "contextly-secret-key"),
    "PORT": int(os.getenv("PORT", "8000")),
    "EMBEDDING_MODEL": "text-embedding-3-small",
    "EMBEDDING_DIM": 1536,
}

# Initialize services
app = FastAPI(title="Contextly.ai Enhanced API", version="3.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# LanceDB table references will be initialized on startup
users_table = None
sessions_table = None
journeys_table = None
graphs_table = None
graph_embeddings_table = None
summaries_table = None
screenshots_table = None
artifacts_table = None

# User cache to prevent duplicate creation
user_cache = {}  # wallet -> user_data

# Initialize LanceDB Cloud connection
try:
    if CONFIG["LANCEDB_URI"] and CONFIG["LANCEDB_API_KEY"]:
        lance_db = lancedb.connect(
            uri=CONFIG["LANCEDB_URI"],
            api_key=CONFIG["LANCEDB_API_KEY"],
            region="us-east-1",
        )
        print(f"✅ LanceDB connected to: {CONFIG['LANCEDB_URI']}")
    else:
        print("⚠️ LanceDB credentials missing, using fallback")
        lance_db = None
except Exception as e:
    print(f"⚠️ LanceDB connection failed: {e}, using fallback")
    lance_db = None

# OpenAI client
openai_client = AsyncOpenAI(api_key=CONFIG["OPENAI_API_KEY"])

# Web3 for wallet verification
w3 = Web3()

# Sentence transformer for fast embeddings
try:
    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    print("✅ Sentence transformer model loaded")
except Exception as e:
    print(f"⚠️ Failed to load sentence transformer: {e}")
    embedder = None

# Enhanced token counting with platform-specific encodings
def get_encoding_for_platform(platform: str):
    """Get appropriate tokenizer encoding for different platforms"""
    platform_encodings = {
        "claude": "gpt-4",      # Claude uses similar tokenization to GPT-4
        "chatgpt": "gpt-4",     # Direct GPT-4 tokenization
        "gpt-4": "gpt-4",       # Direct GPT-4 tokenization
        "gemini": "gpt-4",      # Use GPT-4 as fallback for Gemini
        "default": "gpt-4"
    }
    
    model_name = platform_encodings.get(platform.lower(), "gpt-4")
    return tiktoken.encoding_for_model(model_name)

# Legacy encoding for backward compatibility
encoding = tiktoken.encoding_for_model("gpt-4")

def count_tokens(text: str, platform: str = "default") -> dict:
    """Enhanced token counting with detailed metrics"""
    try:
        enc = get_encoding_for_platform(platform)
        tokens = enc.encode(text)
        
        return {
            "total_tokens": len(tokens),
            "platform": platform,
            "encoding_used": "gpt-4",  # For now, all use GPT-4 encoding
            "text_length": len(text),
            "tokens_per_char": len(tokens) / len(text) if text else 0
        }
    except Exception as e:
        print(f"⚠️ Token counting error: {e}")
        # Fallback to simple estimation
        return {
            "total_tokens": len(text) // 4,  # Rough estimation: ~4 chars per token
            "platform": platform,
            "encoding_used": "fallback",
            "text_length": len(text),
            "tokens_per_char": 0.25
        }


# Upstash Redis client
class UpstashRedis:
    def __init__(self, url: str, token: str):
        self.url = url
        self.headers = {"Authorization": f"Bearer {token}"}

    async def get(self, key: str) -> Optional[str]:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.url}/get/{key}", headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                return data.get("result")
            return None

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        params = {"EX": ex} if ex else {}
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.url}/set/{key}",
                headers=self.headers,
                json={"value": value, **params},
            )
            return response.status_code == 200

    async def incr(self, key: str) -> int:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.url}/incr/{key}", headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                return data.get("result", 0)
            return 0

    async def expire(self, key: str, seconds: int) -> bool:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.url}/expire/{key}/{seconds}", headers=self.headers
            )
            return response.status_code == 200


# Initialize Redis client with fallback
class FallbackRedisClient:
    def __init__(self):
        self.redis_available = False
        self.memory_store = {}
        try:
            # Try to initialize actual Redis
            if CONFIG["UPSTASH_REDIS_REST_URL"] and CONFIG["UPSTASH_REDIS_REST_TOKEN"]:
                self.redis_client = UpstashRedis(
                    CONFIG["UPSTASH_REDIS_REST_URL"], CONFIG["UPSTASH_REDIS_REST_TOKEN"]
                )
                self.redis_available = True
                print("✅ Redis client initialized")
            else:
                print("⚠️ Redis not configured, using in-memory fallback")
        except Exception as e:
            print(f"⚠️ Redis initialization failed, using in-memory fallback: {e}")

    async def get(self, key: str):
        if self.redis_available:
            try:
                return await self.redis_client.get(key)
            except Exception as e:
                print(f"Redis get failed: {e}")
                return self.memory_store.get(key)
        return self.memory_store.get(key)

    async def set(self, key: str, value: str, ex: Optional[int] = None):
        if self.redis_available:
            try:
                return await self.redis_client.set(key, value, ex)
            except Exception as e:
                print(f"Redis set failed: {e}")

        # Fallback to memory store
        self.memory_store[key] = value
        return True

    async def incr(self, key: str):
        if self.redis_available:
            try:
                return await self.redis_client.incr(key)
            except Exception as e:
                print(f"Redis incr failed: {e}")

        # Fallback to memory store
        current = int(self.memory_store.get(key, "0"))
        self.memory_store[key] = str(current + 1)
        return current + 1
    
    async def expire(self, key: str, seconds: int):
        """Set expiration time for a key"""
        if self.redis_available:
            try:
                return await self.redis_client.expire(key, seconds)
            except Exception as e:
                print(f"Redis expire failed: {e}")
        # In-memory fallback doesn't support expiration
        return True


redis_client = FallbackRedisClient()


# Enhanced Pydantic Models
class Message(BaseModel):
    id: str
    conversation_id: str  # ADD THIS - for tracking conversations across sessions
    session_id: str
    role: Literal["user", "assistant"]
    text: str
    timestamp: int
    platform: Literal["claude", "chatgpt", "gemini"]
    artifacts: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None


class WalletRegistration(BaseModel):
    wallet: str
    signature: str
    message: str
    chainId: int = 1


class ConversationMessage(BaseModel):
    message: Message
    conversation_id: str  # ADD THIS - for tracking conversations across sessions
    session_id: str
    wallet: str


class Screenshot(BaseModel):
    screenshot: str  # Base64 encoded
    url: str
    title: str
    timestamp: int


class JourneyBatch(BaseModel):
    screenshots: List[Screenshot]
    session_id: str
    wallet: str


# GraphRAG Models
class Entity(BaseModel):
    name: str
    type: str
    description: Optional[str] = None
    attributes: Dict[str, Any] = {}


class Relationship(BaseModel):
    source: str
    target: str
    type: str
    weight: float = 1.0
    attributes: Dict[str, Any] = {}


class GraphChunk(BaseModel):
    chunk_id: str
    text: str
    entities: List[Entity]
    relationships: List[Relationship]
    metadata: Dict[str, Any] = {}


class ConversationSummary(BaseModel):
    session_id: str
    title: str
    summary: str
    key_points: List[str]
    topics: List[str]
    action_items: List[str]
    timestamp: int
    message_count: int
    platform: str


class SummarizeRequest(BaseModel):
    session_id: str
    messages: List[Message]
    mode: Literal["brief", "detailed", "progressive"] = "brief"
    max_length: Optional[int] = 500


class TitleRequest(BaseModel):
    session_id: str
    messages: List[Message]
    style: Literal["descriptive", "topical", "creative"] = "descriptive"
    include_emoji: bool = True


class ConversationListRequest(BaseModel):
    wallet: str
    platform: Optional[str] = None
    limit: int = 50
    offset: int = 0
    sort_by: Literal["recent", "relevant", "length"] = "recent"
    search_query: Optional[str] = None


# GPT-4o structured output models
class JourneyAction(BaseModel):
    step: int
    action: str
    context: str
    url: str


class JourneyAnalysis(BaseModel):
    journey_id: str = Field(default_factory=lambda: f"journey_{uuid.uuid4().hex[:12]}")
    summary: str = Field(description="Brief summary of what the user is doing")
    intent: str = Field(description="Primary goal or intent")
    actions: List[JourneyAction] = Field(description="Sequence of actions taken")
    patterns: List[str] = Field(description="Identified patterns or workflows")
    category: Literal["research", "shopping", "coding", "writing", "browsing", "other"]
    quality_score: float = Field(
        ge=0.0, le=1.0, description="Quality score from 0 to 1"
    )


class TransferRequest(BaseModel):
    session_id: str
    from_platform: Literal["claude", "chatgpt", "gemini"]
    to_platform: Literal["claude", "chatgpt", "gemini"]
    mode: Literal["smart", "full", "graph-enhanced"] = "smart"
    messages: List[Message]


# Knowledge Graph structured outputs
class KnowledgeGraphSummary(BaseModel):
    entities: List[Entity]
    relationships: List[Relationship]
    communities: List[Dict[str, Any]]
    main_topics: List[str]
    key_insights: List[str]


# Authentication Models
class AuthHeader(BaseModel):
    wallet: Optional[str] = None
    signature: Optional[str] = None
    message: Optional[str] = None
    x_auth_token: Optional[str] = None
    session_id: Optional[str] = None


class AuthenticatedUser(BaseModel):
    user_id: str
    wallet: Optional[str] = None
    x_id: Optional[str] = None
    x_username: Optional[str] = None
    method: Literal["wallet", "x", "session"]
    session_id: str
    total_earnings: float = 0.0


def dict_to_authenticated_user(user_dict: dict) -> AuthenticatedUser:
    """Convert a dict from get_current_user to AuthenticatedUser object"""
    return AuthenticatedUser(
        user_id=user_dict.get("user_id", ""),
        wallet=user_dict.get("wallet"),
        x_id=user_dict.get("x_id"),
        x_username=user_dict.get("x_username"),
        method=user_dict.get("method", "wallet"),
        session_id=user_dict.get("session_id", str(uuid.uuid4())),
        total_earnings=user_dict.get("total_earnings", 0.0),
    )


async def get_current_user_obj(
    current_user: dict = Depends(get_current_user),
) -> AuthenticatedUser:
    """Get current user as AuthenticatedUser object"""
    return dict_to_authenticated_user(current_user)


# Dependency injection for authentication
async def get_current_user_legacy(
    authorization: Optional[str] = Header(None),
    x_wallet_address: Optional[str] = Header(None),
    x_wallet_signature: Optional[str] = Header(None),
    x_auth_token: Optional[str] = Header(None),
    x_session_id: Optional[str] = Header(None),
) -> AuthenticatedUser:
    """
    Authenticate user via wallet signature or X auth token.
    Returns authenticated user object with session tracking.
    """

    # Try session-based auth first
    if x_session_id:
        session_data = await redis_client.get(f"session:{x_session_id}")
        if session_data:
            session = json.loads(session_data)
            return AuthenticatedUser(**session)

    # Try wallet authentication
    if x_wallet_address and x_wallet_signature:
        # Default message if not provided
        message = f"Sign this message to authenticate with Contextly: {datetime.now(timezone.utc).date()}"

        if verify_wallet_signature(x_wallet_address, x_wallet_signature, message):
            # Get or create user
            user = await find_user_by_wallet(x_wallet_address)
            if not user:
                raise HTTPException(
                    status_code=404, detail="User not found. Please register first."
                )

            # Create session
            session_id = str(uuid.uuid4())
            auth_user = AuthenticatedUser(
                user_id=user["_id"],
                wallet=x_wallet_address,
                method="wallet",
                session_id=session_id,
                total_earnings=user.get("total_earnings", 0.0),
            )

            # Store session
            await redis_client.set(
                f"session:{session_id}",
                json.dumps(auth_user.dict()),
                ex=86400,  # 24 hours
            )

            return auth_user

    # Try X authentication
    if x_auth_token:
        # Validate X auth token
        token_data = await redis_client.get(f"x_token:{x_auth_token}")
        if token_data:
            x_data = json.loads(token_data)

            # Create session
            session_id = str(uuid.uuid4())
            auth_user = AuthenticatedUser(
                user_id=x_data["x_id"],
                x_id=x_data["x_id"],
                x_username=x_data["x_username"],
                method="x",
                session_id=session_id,
                total_earnings=x_data.get("total_earnings", 0.0),
            )

            # Store session
            await redis_client.set(
                f"session:{session_id}",
                json.dumps(auth_user.dict()),
                ex=86400,  # 24 hours
            )

            return auth_user

    # Try authorization header
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        try:
            # Decode JWT token
            payload = jwt.decode(token, CONFIG["JWT_SECRET"], algorithms=["HS256"])

            # Create session
            session_id = str(uuid.uuid4())
            auth_user = AuthenticatedUser(
                user_id=payload["user_id"],
                wallet=payload.get("wallet"),
                x_id=payload.get("x_id"),
                method=payload.get("method", "wallet"),
                session_id=session_id,
                total_earnings=payload.get("total_earnings", 0.0),
            )

            # Store session
            await redis_client.set(
                f"session:{session_id}",
                json.dumps(auth_user.dict()),
                ex=86400,  # 24 hours
            )

            return auth_user

        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid authentication token")

    raise HTTPException(
        status_code=401,
        detail="Authentication required. Provide wallet signature, X auth token, or session ID.",
    )


# Session tracking decorator
async def track_session_activity(
    user: AuthenticatedUser, activity_type: str, data: Dict[str, Any] = {}
):
    """Track user activity in their session"""
    activity = {
        "user_id": user.user_id,
        "session_id": user.session_id,
        "activity_type": activity_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }

    # Store activity
    activity_key = f"activity:{user.session_id}:{int(datetime.now().timestamp())}"
    await redis_client.set(activity_key, json.dumps(activity), ex=86400 * 7)  # 7 days

    # Update session last activity
    session_data = await redis_client.get(f"session:{user.session_id}")
    if session_data:
        session = json.loads(session_data)
        session["last_activity"] = datetime.now(timezone.utc).isoformat()
        await redis_client.set(
            f"session:{user.session_id}", json.dumps(session), ex=86400  # Reset TTL
        )


# Helper functions
# verify_wallet_signature moved to auth.py


async def get_embedding(text: str, model: str = "openai") -> List[float]:
    """Get embedding for text using specified model"""
    try:
        if model == "openai":
            if not CONFIG.get("OPENAI_API_KEY"):
                print("⚠️ OpenAI API key not configured")
                return [0.0] * CONFIG["EMBEDDING_DIM"]
            response = await openai_client.embeddings.create(
                model=CONFIG["EMBEDDING_MODEL"], input=text
            )
            return response.data[0].embedding
        else:
            # Use sentence transformer for faster local embeddings
            if embedder is None:
                print("⚠️ Sentence transformer not available, using zero vector")
                return [0.0] * 384  # Sentence transformer uses 384 dimensions
            embedding = embedder.encode(text)
            return embedding.tolist()
    except Exception as e:
        print(f"Embedding error: {e}")
        # Return appropriate dimension based on model
        dim = CONFIG["EMBEDDING_DIM"] if model == "openai" else 384
        return [0.0] * dim


def anonymize_text(text: str) -> str:
    """Remove PII from text"""
    # Email addresses
    text = re.sub(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL]", text
    )
    # Phone numbers
    text = re.sub(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "[PHONE]", text)
    # Credit cards
    text = re.sub(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", "[CARD]", text)
    # SSN
    text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[SSN]", text)
    # URLs (preserve domain)
    text = re.sub(r"https?://([^/\s]+)[^\s]*", r"[URL:\1]", text)

    return text


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Chunk text for processing with overlap"""
    tokens = encoding.encode(text)
    chunks = []

    for i in range(0, len(tokens), chunk_size - overlap):
        chunk_tokens = tokens[i : i + chunk_size]
        chunk_text = encoding.decode(chunk_tokens)
        chunks.append(chunk_text)

    return chunks


async def extract_entities_relationships(
    text: str,
) -> Tuple[List[Entity], List[Relationship]]:
    """Extract entities and relationships from text using GPT-4"""
    system_prompt = """Extract entities and their relationships from the text.
    Entities should include: people, organizations, concepts, technologies, projects, etc.
    Relationships should describe how entities are connected.
    Be specific and accurate."""

    response = await openai_client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
        response_format=GraphChunk,
        temperature=0.3,
        max_tokens=2000,
    )

    chunk = response.choices[0].message.parsed
    return chunk.entities, chunk.relationships


def build_knowledge_graph(
    entities: List[Entity], relationships: List[Relationship]
) -> nx.Graph:
    """Build NetworkX graph from entities and relationships"""
    G = nx.Graph()

    # Add nodes
    for entity in entities:
        G.add_node(
            entity.name,
            type=entity.type,
            description=entity.description,
            **entity.attributes,
        )

    # Add edges
    for rel in relationships:
        G.add_edge(
            rel.source, rel.target, type=rel.type, weight=rel.weight, **rel.attributes
        )

    return G


def detect_communities(G: nx.Graph) -> List[List[str]]:
    """Detect communities in the graph"""
    if len(G.nodes()) < 2:
        return [[node] for node in G.nodes()]

    # Convert to undirected for community detection
    G_undirected = G.to_undirected()

    # Use Louvain community detection
    from networkx.algorithms import community

    communities = list(community.greedy_modularity_communities(G_undirected))

    return [list(comm) for comm in communities]


async def generate_community_summary(community: List[str], G: nx.Graph) -> str:
    """Generate summary for a community of entities"""
    # Get subgraph for community
    subgraph = G.subgraph(community)

    # Build description
    entities_desc = []
    for node in community[:10]:  # Limit to first 10 nodes
        node_data = G.nodes[node]
        entities_desc.append(f"- {node} ({node_data.get('type', 'unknown')})")

    # Get relationships
    edges_desc = []
    for u, v, data in subgraph.edges(data=True):
        edges_desc.append(f"- {u} -> {v} ({data.get('type', 'related')})")

    prompt = f"""Summarize this community of related entities:

Entities:
{chr(10).join(entities_desc)}

Relationships:
{chr(10).join(edges_desc[:10])}

Provide a concise summary of what this community represents and its main theme."""

    response = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
        temperature=0.3,
    )

    return response.choices[0].message.content


# Initialize LanceDB tables
async def init_lancedb():
    """Initialize LanceDB tables with enhanced schema"""
    global users_table, sessions_table, journeys_table, graphs_table, graph_embeddings_table, summaries_table, screenshots_table, artifacts_table

    if not lance_db:
        print("⚠️ LanceDB not available, skipping table initialization")
        return

    try:
        # Get existing tables - handle generator properly
        existing_tables = list(lance_db.table_names())
        print(f"📋 Found existing LanceDB tables: {existing_tables}")

        # Users table with enhanced token tracking
        if "users" not in existing_tables:
            initial_user = [
                {
                    "user_id": "init",
                    "wallet": "0x0",
                    "x_id": None,
                    "x_username": None,
                    "chain_id": 1,
                    "created": int(datetime.now().timestamp()),
                    "total_earnings": 0.0,
                    "conversation_count": 0,
                    "journey_count": 0,
                    "graph_nodes_created": 0,
                    # Enhanced token tracking fields
                    "total_tokens": 0,
                    "tokens_by_platform": {},  # {"claude": 1234, "chatgpt": 567}
                    "tokens_by_role": {"user": 0, "assistant": 0},
                    "daily_tokens": {},  # {"2024-01-01": 150, "2024-01-02": 200}
                    "last_token_update": None,
                }
            ]
            try:
                lance_db.create_table("users", data=initial_user)
                print("✅ Created users table")
            except Exception as e:
                print(f"⚠️ Could not create users table: {e}")
            print("✅ Created users table")

        # Sessions table
        if "sessions" not in existing_tables:
            initial_session = [
                {
                    "session_id": "init",
                    "user_id": "init",
                    "wallet": "0x0",
                    "platform": "claude",
                    "start_time": datetime.now().isoformat(),
                    "end_time": "",
                    "message_count": 0,
                    "total_tokens": 0,
                    "ctxt_earned": 0.0,
                    "quality_average": 0.0,
                    "topics": [],
                    "is_active": True,
                }
            ]
            try:
                lance_db.create_table("sessions", data=initial_session)
                print("✅ Created sessions table")
            except Exception as e:
                print(f"⚠️ Could not create sessions table: {e}")
            print("✅ Created sessions table")

        # Enhanced conversations table with multimodal support
        if "conversations_v2" not in existing_tables:
            initial_data = [
                {
                    "id": "init",
                    "session_id": "init",
                    "platform": "claude",
                    "role": "user",
                    "wallet": "0x0",
                    "text": "Initial message",
                    "text_vector": np.zeros(CONFIG["EMBEDDING_DIM"]).tolist(),
                    "summary_vector": np.zeros(384).tolist(),
                    "timestamp": int(datetime.now().timestamp()),
                    "token_count": 0,
                    "has_artifacts": False,
                    "topics": [],
                    "entities": "{}",
                    "coherence_score": 0.0,
                    "quality_tier": 1,
                    "earned_amount": 0.0,
                    "contribution_id": "",
                    "blockchain_tx": "",
                }
            ]

            try:
                lance_db.create_table("conversations_v2", data=initial_data)
                print("✅ Created conversations_v2 table")
            except Exception as e:
                print(f"⚠️ Could not create conversations_v2 table: {e}")
            print("✅ Created enhanced conversations table")

        # Knowledge graph embeddings table
        if "graph_embeddings" not in existing_tables:
            initial_graph = [
                {
                    "entity_id": "init",
                    "entity_name": "Initial Entity",
                    "entity_type": "concept",
                    "embedding": np.zeros(384).tolist(),
                    "community_id": 0,
                    "centrality_score": 0.0,
                    "timestamp": int(datetime.now().timestamp()),
                }
            ]

            try:
                lance_db.create_table("graph_embeddings", data=initial_graph)
                print("✅ Created graph_embeddings table")
            except Exception as e:
                print(f"⚠️ Could not create graph_embeddings table: {e}")
            print("✅ Created graph embeddings table")

        # Journey embeddings with enhanced metadata
        if "journeys_v2" not in existing_tables:
            initial_journey = [
                {
                    "journey_id": "init",
                    "wallet": "0x0",
                    "summary": "Initial journey",
                    "summary_vector": np.zeros(CONFIG["EMBEDDING_DIM"]).tolist(),
                    "intent": "test",
                    "category": "other",
                    "quality_score": 0.0,
                    "action_count": 0,
                    "duration_seconds": 0,
                    "timestamp": int(datetime.now().timestamp()),
                }
            ]

            try:
                lance_db.create_table("journeys_v2", data=initial_journey)
                print("✅ Created journeys_v2 table")
            except Exception as e:
                print(f"⚠️ Could not create journeys_v2 table: {e}")
            print("✅ Created enhanced journeys table")

        # Graphs table for storing full graph data
        if "graphs" not in existing_tables:
            initial_graph_doc = [
                {
                    "graph_id": "init",
                    "session_id": "init",
                    "wallet": "0x0",
                    "entities": [],
                    "relationships": [],
                    "communities": [],
                    "metrics": {},
                    "created": int(datetime.now().timestamp()),
                }
            ]
            try:
                lance_db.create_table("graphs", data=initial_graph_doc)
                print("✅ Created graphs table")
            except Exception as e:
                print(f"⚠️ Could not create graphs table: {e}")
            print("✅ Created graphs table")

        # Summaries table
        if "summaries" not in existing_tables:
            initial_summary = [
                {
                    "session_id": "init",
                    "summary": "Initial summary",
                    "key_points": [],
                    "action_items": [],
                    "topics": [],
                    "mode": "brief",
                    "timestamp": int(datetime.now().timestamp()),
                    "message_count": 0,
                    "platform": "claude",
                }
            ]
            try:
                lance_db.create_table("summaries", data=initial_summary)
                print("✅ Created summaries table")
            except Exception as e:
                print(f"⚠️ Could not create summaries table: {e}")
            print("✅ Created summaries table")

        # Screenshots table for automation features
        if "screenshots" not in existing_tables:
            initial_screenshot = [
                {
                    "id": "init",
                    "user_id": "init",
                    "wallet": "0x0",
                    "screenshot_hash": "init",
                    "url": "https://example.com",
                    "title": "Initial screenshot",
                    "analysis": "Initial analysis",
                    "quality_score": 7,
                    "earnings": 0.0,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "session_id": "init",
                    "vector": [0.0] * 384,  # Placeholder embedding
                }
            ]
            try:
                lance_db.create_table("screenshots", data=initial_screenshot)
                print("✅ Created screenshots table")
            except Exception as e:
                print(f"⚠️ Could not create screenshots table: {e}")
            print("✅ Created screenshots table")

        # Artifacts table for page captures
        if "artifacts" not in existing_tables:
            initial_artifact = [
                {
                    "id": "init",
                    "user_id": "init",
                    "wallet": "0x0",
                    "url": "https://example.com",
                    "title": "Initial artifact",
                    "html_hash": "init",
                    "text_preview": "Initial text",
                    "metadata": "{}",
                    "analysis": "Initial analysis",
                    "value_score": 7,
                    "earnings": 0.0,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "session_id": "init",
                    "vector": [0.0] * 384,  # Placeholder embedding
                }
            ]
            try:
                lance_db.create_table("artifacts", data=initial_artifact)
                print("✅ Created artifacts table")
            except Exception as e:
                print(f"⚠️ Could not create artifacts table: {e}")

        # Refresh the table list after creating new tables
        existing_tables = list(lance_db.table_names())
        print(f"📋 Updated table list: {existing_tables}")

        # Open all tables with error handling
        try:
            users_table = (
                lance_db.open_table("users") if "users" in existing_tables else None
            )
            sessions_table = (
                lance_db.open_table("sessions")
                if "sessions" in existing_tables
                else None
            )
            journeys_table = (
                lance_db.open_table("journeys_v2")
                if "journeys_v2" in existing_tables
                else None
            )
            graphs_table = (
                lance_db.open_table("graphs") if "graphs" in existing_tables else None
            )
            graph_embeddings_table = (
                lance_db.open_table("graph_embeddings")
                if "graph_embeddings" in existing_tables
                else None
            )
            summaries_table = (
                lance_db.open_table("summaries")
                if "summaries" in existing_tables
                else None
            )
            screenshots_table = (
                lance_db.open_table("screenshots")
                if "screenshots" in existing_tables
                else None
            )
            artifacts_table = (
                lance_db.open_table("artifacts")
                if "artifacts" in existing_tables
                else None
            )

            active_tables = [
                name
                for name, table in [
                    ("users", users_table),
                    ("sessions", sessions_table),
                    ("journeys_v2", journeys_table),
                    ("graphs", graphs_table),
                    ("graph_embeddings", graph_embeddings_table),
                    ("summaries", summaries_table),
                    ("screenshots", screenshots_table),
                    ("artifacts", artifacts_table),
                ]
                if table is not None
            ]

            print(f"📊 Active LanceDB tables: {active_tables}")
            
            # Verify table methods are available
            if users_table is not None:
                # Test if to_pandas method works using safe wrapper
                test_df = safe_table_to_pandas(users_table, "users")
                if test_df is not None:
                    print(f"✅ Users table supports to_pandas() method")
                else:
                    print(f"⚠️ Users table does not support to_pandas() method, will use search API")

        except Exception as e:
            print(f"⚠️ Error opening tables: {e}")
            users_table = sessions_table = journeys_table = graphs_table = (
                graph_embeddings_table
            ) = summaries_table = screenshots_table = artifacts_table = None

    except Exception as e:
        print(f"LanceDB init error: {e}")


# LanceDB helper functions
def safe_table_to_pandas(table, table_name: str = "table"):
    """Safely convert LanceDB table to pandas DataFrame with fallback"""
    try:
        return table.to_pandas()
    except NotImplementedError:
        print(f"⚠️ {table_name}.to_pandas() not implemented, returning None")
        return None
    except Exception as e:
        print(f"❌ Error converting {table_name} to pandas: {e}")
        return None


async def find_user_by_wallet(wallet: str):
    """Find user by wallet address"""
    # Check cache first
    if wallet in user_cache:
        print(f"✅ Found user in cache for wallet: {wallet}")
        return user_cache[wallet]
    
    if users_table is None:
        print(f"⚠️ Users table not initialized")
        return None
    
    try:
        # For remote LanceDB, we can't easily query by non-vector fields
        # This is a current limitation - just return None to trigger user creation
        print(f"🔍 Searching for user with wallet: {wallet}")
        print(f"⚠️ Remote LanceDB doesn't support efficient non-vector queries")
        print(f"ℹ️ Checking cache instead...")
        return None
        
    except Exception as e:
        print(f"❌ Error in find_user_by_wallet: {e}")
        return None


async def find_user_by_id(user_id: str):
    """Find user by ID"""
    if users_table is None:
        print(f"⚠️ Users table not initialized")
        return None
    try:
        # Query LanceDB for user by ID
        print(f"🔍 Searching for user with ID: {user_id}")
        
        # For remote LanceDB, we can't easily query by non-vector fields
        # This is a current limitation - just return None to trigger user creation
        print(f"⚠️ Remote LanceDB doesn't support efficient non-vector queries")
        print(f"ℹ️ Returning None - user will be created if needed")
        return None
            
    except Exception as e:
        print(f"❌ Error finding user by ID: {e}")
        import traceback
        traceback.print_exc()
        return None


async def create_user(user_data: dict):
    """Create new user"""
    if users_table is None:
        raise Exception("Users table not initialized")
    try:
        print(f"📝 Creating new user: {user_data.get('wallet')}")
        print(f"   User data: {json.dumps(user_data, indent=2)}")
        
        # Ensure all required fields are present
        user_record = {
            "_id": user_data.get("_id", str(uuid.uuid4())),
            "wallet": user_data.get("wallet"),
            "chainId": user_data.get("chainId", 1),
            "created": user_data.get("created", datetime.now().isoformat()),
            "totalEarnings": user_data.get("totalEarnings", 0.0),
            "conversationCount": user_data.get("conversationCount", 0),
            "journeyCount": user_data.get("journeyCount", 0),
            "graphNodesCreated": user_data.get("graphNodesCreated", 0),
            "x_username": user_data.get("x_username", ""),
            "x_id": user_data.get("x_id", ""),
            "auth_method": user_data.get("auth_method", "wallet"),
            "last_active": user_data.get("last_active", datetime.now().isoformat()),
            # Token tracking fields
            "total_tokens": user_data.get("total_tokens", 0),
            "tokens_by_platform": user_data.get("tokens_by_platform", {}),
            "tokens_by_role": user_data.get("tokens_by_role", {"user": 0, "assistant": 0}),
            "daily_tokens": user_data.get("daily_tokens", {}),
            "last_token_update": datetime.now().isoformat()
        }
        
        # Check if user already exists in cache before adding to DB
        if user_record["wallet"] in user_cache:
            print(f"⚠️ User already exists in cache, skipping creation")
            return user_cache[user_record["wallet"]]
        
        # Add to LanceDB
        try:
            users_table.add([user_record])
            print(f"✅ User created successfully: {user_record['_id']}")
        except Exception as db_error:
            print(f"⚠️ Database error (possibly duplicate): {db_error}")
            # Even if DB fails, we can use the record
        
        # Add to cache
        user_cache[user_record["wallet"]] = user_record
        print(f"💾 Added user to cache: {user_record['wallet']}")
        
        return user_record
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        import traceback
        traceback.print_exc()
        raise e


async def update_user_token_count(wallet: str, token_metrics: dict, role: str):
    """Update user's token tracking with new message tokens"""
    if wallet not in user_cache:
        print(f"⚠️ User not in cache for token update: {wallet}")
        return
    
    user = user_cache[wallet]
    platform = token_metrics.get("platform", "unknown")
    tokens = token_metrics.get("total_tokens", 0)
    today = datetime.now().date().isoformat()
    
    # Update total tokens
    user["total_tokens"] = user.get("total_tokens", 0) + tokens
    
    # Update tokens by platform
    tokens_by_platform = user.get("tokens_by_platform", {})
    tokens_by_platform[platform] = tokens_by_platform.get(platform, 0) + tokens
    user["tokens_by_platform"] = tokens_by_platform
    
    # Update tokens by role (user vs assistant)
    tokens_by_role = user.get("tokens_by_role", {"user": 0, "assistant": 0})
    tokens_by_role[role] = tokens_by_role.get(role, 0) + tokens
    user["tokens_by_role"] = tokens_by_role
    
    # Update daily tokens
    daily_tokens = user.get("daily_tokens", {})
    daily_tokens[today] = daily_tokens.get(today, 0) + tokens
    user["daily_tokens"] = daily_tokens
    
    # Update timestamp
    user["last_token_update"] = datetime.now().isoformat()
    
    # Update cache
    user_cache[wallet] = user
    
    print(f"📊 Updated user tokens: {wallet} (+{tokens} {role} tokens from {platform})")
    print(f"   Total: {user['total_tokens']} | Today: {daily_tokens.get(today, 0)}")
    
    return user


async def update_user_earnings(
    user_id: str,
    earnings_delta: float,
    conversation_delta: int = 0,
    journey_delta: int = 0,
    graph_nodes_delta: int = 0,
):
    """Update user earnings and stats"""
    user = await find_user_by_id(user_id)
    if user:
        user["total_earnings"] += earnings_delta
        user["conversation_count"] += conversation_delta
        user["journey_count"] += journey_delta
        user["graph_nodes_created"] += graph_nodes_delta
        # LanceDB doesn't support direct updates, so we need to use a workaround
        # For now, we'll rely on Redis for real-time updates
        return user
    return None


async def find_session(session_id: str):
    """Find session by ID"""
    if sessions_table is None:
        return None
    try:
        # For remote LanceDB, get all and filter locally
        try:
            # TODO: Implement proper remote table querying
            # For now, return None for remote tables
            pass
        except:
            pass
        return None
    except:
        return None


async def upsert_session(
    session_id: str,
    wallet: str,
    platform: str,
    topics: list = None,
    message_count_inc: int = 0,
    token_count_inc: int = 0,
    earnings_inc: float = 0.0,
):
    """Create or update session in LanceDB"""
    if sessions_table is None:
        raise Exception("Sessions table not initialized")

    try:
        # For remote LanceDB, we'll assume session doesn't exist
        # TODO: Implement proper session lookup for remote tables
        existing = []

        if existing:
            # Update existing session - LanceDB requires delete and re-insert
            session = existing[0]
            session["message_count"] += message_count_inc
            session["total_tokens"] += token_count_inc
            session["ctxt_earned"] += earnings_inc
            if topics:
                session["topics"] = list(set(session["topics"] + topics))
            session["end_time"] = datetime.now().isoformat()

            # Delete old record and add updated one
            sessions_table.delete(f"session_id = '{session_id}'")
            sessions_table.add([session])
        else:
            # Create new session
            new_session = {
                "session_id": session_id,
                "user_id": wallet,  # Use wallet as user_id for now
                "wallet": wallet,
                "platform": platform,
                "start_time": datetime.now().isoformat(),
                "end_time": "",
                "message_count": message_count_inc,
                "total_tokens": token_count_inc,
                "ctxt_earned": earnings_inc,
                "quality_average": 0.0,
                "topics": topics or [],
                "is_active": True,
            }
            sessions_table.add([new_session])

        return True
    except Exception as e:
        print(f"Error upserting session: {e}")
        return False


async def count_user_sessions(wallet: str):
    """Count sessions for a user"""
    if sessions_table is None:
        return 0
    try:
        # For remote LanceDB, we'll return 0 for now
        # TODO: Implement proper counting for remote tables
        return 0
    except Exception as e:
        print(f"Error counting user sessions: {e}")
        return 0


# Routes
@app.get("/")
async def home():
    return {
        "service": "Contextly.ai Enhanced API",
        "version": "3.0.0",
        "status": "operational",
        "features": {
            "vector_db": "LanceDB Cloud with advanced indexing",
            "graph_rag": "Knowledge graph construction and querying",
            "summarization": "Intelligent conversation summarization",
            "multimodal": "Support for text, code, and images",
            "cache": "Upstash Redis",
        },
    }


@app.post("/v1/wallet/disconnect")
async def disconnect_wallet(current_user: AuthenticatedUser = Depends(get_current_user_obj)):
    """Handle wallet disconnection - log the event"""
    
    auth_logger.info(f"🔌 Wallet disconnecting: {current_user.wallet}")
    
    # Log the disconnection event
    if users_table is not None:
        try:
            # Update last_active timestamp
            user = await find_user_by_id(current_user.user_id)
            if user:
                user["last_disconnected"] = datetime.now().isoformat()
                # Note: Can't update in remote LanceDB easily, so just log
                print(f"📊 User {current_user.wallet} disconnected at {user['last_disconnected']}")
        except Exception as e:
            print(f"⚠️ Error logging disconnect: {e}")
    
    return {
        "success": True,
        "message": "Wallet disconnected successfully",
        "wallet": current_user.wallet
    }


@app.post("/v1/wallet/register")
async def register_wallet(registration: WalletRegistration):
    """Register wallet with signature verification and return JWT token"""

    auth_logger.info(f"📝 Wallet registration attempt: {registration.wallet}")

    if not verify_wallet_signature(
        registration.wallet, registration.signature, registration.message
    ):
        auth_logger.warning(f"❌ Invalid signature for wallet: {registration.wallet}")
        raise HTTPException(status_code=401, detail="Invalid signature")

    existing = await find_user_by_wallet(registration.wallet)

    if not existing:
        # Use deterministic ID based on wallet address
        user_id = f"user_{registration.wallet[-8:].lower()}"
        user_doc = {
            "_id": user_id,
            "wallet": registration.wallet,
            "x_id": None,
            "x_username": None,
            "chainId": registration.chainId,
            "created": str(datetime.now().isoformat()),
            "totalEarnings": 0.0,
            "conversationCount": 0,
            "journeyCount": 0,
            "graphNodesCreated": 0,
            "auth_method": "wallet",
            "last_active": str(datetime.now().isoformat()),
            # Enhanced token tracking fields
            "total_tokens": 0,
            "tokens_by_platform": {},
            "tokens_by_role": {"user": 0, "assistant": 0},
            "daily_tokens": {},
            "last_token_update": None,
        }
        await create_user(user_doc)

        # Create JWT token for new user
        token = create_access_token(user_doc["wallet"], user_doc["_id"])
        auth_logger.info(f"✅ New wallet registered: {registration.wallet}")

        return {
            "success": True,
            "userId": user_doc["_id"],
            "message": "Wallet registered successfully",
            "token": token,
            "wallet": user_doc["wallet"],
        }

    # Create JWT token for existing user
    user_id = existing.get("user_id") or existing.get("_id")
    token = create_access_token(existing["wallet"], user_id)
    auth_logger.info(f"✅ Existing wallet authenticated: {registration.wallet}")

    return {
        "success": True,
        "userId": user_id,
        "message": "Wallet already registered",
        "token": token,
        "wallet": existing["wallet"],
    }


@app.post("/v1/conversations/message")
async def store_message(
    data: ConversationMessage,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """Store message with enhanced processing and authentication"""

    # Log incoming message details with enhanced debugging
    print(f"\n{'='*60}")
    print(f"🔵 INCOMING MESSAGE CAPTURE:")
    print(f"{'='*60}")
    print(f"📋 ConversationMessage Data:")
    print(f"  - Conversation ID: {data.conversation_id}")
    print(f"  - Session ID: {data.session_id}")
    print(f"  - Wallet: {data.wallet}")
    print(f"\n📨 Message Object:")
    print(f"  - Message ID: {data.message.id}")
    print(f"  - Message Conversation ID: {data.message.conversation_id}")
    print(f"  - Message Session ID: {data.message.session_id}")
    print(f"  - Platform: {data.message.platform}")
    print(f"  - Role: {data.message.role}")
    print(f"  - Timestamp: {data.message.timestamp}")
    print(f"  - Raw Text Length: {len(data.message.text)} chars")
    print(f"  - Raw Text Preview: {data.message.text[:200]}...")
    print(f"{'='*60}\n")

    # Log authentication
    auth_logger.info(
        f"📝 Message store request from wallet: {current_user.get('wallet')}"
    )

    # Verify user owns this wallet/session
    if current_user.get("wallet") and data.wallet != current_user.get("wallet"):
        raise HTTPException(
            status_code=403, detail="Cannot store messages for another wallet"
        )

    user = await find_user_by_wallet(data.wallet)
    if not user:
        # Auto-create user if not exists
        print(f"🆕 User not found for wallet {data.wallet}, creating new user...")
        # Use deterministic ID based on wallet address
        user_id = f"user_{data.wallet[-8:].lower()}"
        user_doc = {
            "_id": user_id,
            "wallet": data.wallet,
            "chainId": 1,  # Default to Ethereum mainnet
            "created": datetime.now().isoformat(),
            "totalEarnings": 0.0,
            "conversationCount": 0,
            "journeyCount": 0,
            "graphNodesCreated": 0,
            "x_username": "",
            "x_id": "",
            "auth_method": "wallet",
            "last_active": datetime.now().isoformat(),
            # Enhanced token tracking fields
            "total_tokens": 0,
            "tokens_by_platform": {},
            "tokens_by_role": {"user": 0, "assistant": 0},
            "daily_tokens": {},
            "last_token_update": None,
        }
        try:
            user = await create_user(user_doc)
            print(f"✅ Auto-created user for wallet: {data.wallet}")
        except Exception as e:
            print(f"❌ Failed to auto-create user: {e}")
            # Try to find again in case of race condition
            user = await find_user_by_wallet(data.wallet)
            if not user:
                raise HTTPException(status_code=500, detail="Could not create or find user")

    # Anonymize message
    anonymized_text = anonymize_text(data.message.text)

    # Enhanced token counting with platform-specific metrics
    token_metrics = count_tokens(data.message.text, data.message.platform)
    token_count = token_metrics["total_tokens"]

    # Get embeddings (both OpenAI and sentence transformer)
    text_embedding = await get_embedding(anonymized_text, "openai")
    summary_embedding = await get_embedding(anonymized_text[:500], "sentence")

    # Extract topics using simple keyword extraction
    topics = extract_topics(anonymized_text)

    # Open conversations table and add message to LanceDB
    try:
        if lance_db is None:
            raise HTTPException(status_code=503, detail="Database not available")

        conversations_table = lance_db.open_table("conversations_v2")

        # Add message to LanceDB
        new_message = {
            "id": data.message.id,
            "conversation_id": data.message.conversation_id,  # ADD THIS - now reading from message
            "session_id": data.session_id,
            "user_id": user.get("_id", f"user_{data.wallet[-8:]}"),  # Add user_id field
            "platform": data.message.platform,
            "role": data.message.role,  # Store user or assistant role
            "wallet": data.wallet,
            "text": anonymized_text,  # Raw text is stored here
            "text_vector": text_embedding
            or [0.0] * 1536,  # Default OpenAI embedding size
            "summary_vector": summary_embedding
            or [0.0] * 384,  # Default MiniLM embedding size
            "timestamp": data.message.timestamp,
            "token_count": token_count,
            "token_metrics": token_metrics,  # Enhanced token details
            "has_artifacts": (
                bool(data.message.artifacts)
                if hasattr(data.message, "artifacts")
                else False
            ),
            "topics": topics,
            "entities": "{}",  # JSON string as per schema
            "coherence_score": 0.85,  # Default value
            "quality_tier": 2,  # Default value
            "earned_amount": 0.0,  # Will be calculated
            "contribution_id": "",  # Default empty
            "blockchain_tx": "",  # Default empty
        }

        # Log the message being stored
        print(f"📝 Storing message to LanceDB:")
        print(f"  - ID: {new_message['id']}")
        print(f"  - Conversation: {new_message['conversation_id']}")  # ADD THIS
        print(f"  - Session: {new_message['session_id']}")
        print(f"  - Platform: {new_message['platform']}")
        print(f"  - Role: {new_message['role']}")
        print(f"  - Text Length: {len(new_message['text'])} chars")
        print(f"  - Raw Text Preview: {new_message['text'][:100]}...")
        print(f"  - Tokens: {new_message['token_count']}")
        print(f"  - Topics: {new_message['topics']}")

        conversations_table.add([new_message])
        print(f"\n{'='*60}")
        print(f"✅ SUCCESSFULLY STORED MESSAGE TO LANCEDB")
        print(f"{'='*60}")
        print(f"📍 Storage Details:")
        print(f"  - Message ID: {data.message.id}")
        print(f"  - Conversation ID: {new_message['conversation_id']}")
        print(f"  - Session ID: {new_message['session_id']}")
        print(f"  - Table: conversations_v2")
        print(f"  - Token Count: {new_message['token_count']}")
        print(f"  - Topics: {new_message['topics']}")
        print(f"{'='*60}\n")

        # Update user token tracking with enhanced metrics
        await update_user_token_count(
            wallet=data.wallet,
            token_metrics=token_metrics,
            role=data.message.role
        )

    except Exception as e:
        print(f"❌ Error storing message to LanceDB: {e}")
        # Continue with the rest of the function even if LanceDB fails
        # This ensures the user still gets earnings and session updates

    # Schedule background graph construction
    background_tasks.add_task(
        process_message_for_graph,
        data.message.id,
        anonymized_text,
        data.session_id,
        data.wallet,
    )

    # Calculate earnings
    base_rate = 0.001
    quality_multiplier = 1.5 if token_count > 100 else 1.0
    artifact_bonus = 0.0005 if data.message.artifacts else 0
    earned = (base_rate * quality_multiplier) + artifact_bonus

    # Update user stats and track earnings
    await update_user_earnings(user["_id"], earned, conversation_delta=1)

    # Update session earnings
    if isinstance(current_user, dict):
        current_user["total_earnings"] = current_user.get("total_earnings", 0) + earned
        session_id = current_user.get("session_id", data.session_id)
        await redis_client.set(
            f"session:{session_id}", json.dumps(current_user), ex=86400  # 24 hours
        )
    else:
        current_user.total_earnings += earned
        await redis_client.set(
            f"session:{current_user.session_id}",
            json.dumps(current_user.dict()),
            ex=86400,  # 24 hours
        )

    # Track CTXT earnings by session
    session_id = (
        current_user.get("session_id", data.session_id)
        if isinstance(current_user, dict)
        else current_user.session_id
    )
    earnings_key = f"earnings:session:{session_id}"
    await redis_client.incr(earnings_key)
    await redis_client.expire(earnings_key, 86400 * 30)  # 30 days

    # Update session with enhanced metadata
    await upsert_session(
        session_id=data.session_id,
        wallet=data.wallet,
        platform=data.message.platform,
        topics=topics,
        message_count_inc=1,
        token_count_inc=token_count,
        earnings_inc=earned,
    )

    # Update daily earnings
    today_key = f"earnings:{data.wallet}:{datetime.now().date()}"
    await redis_client.incr(today_key)
    await redis_client.expire(today_key, 86400 * 7)

    return {
        "success": True,
        "earned": earned,
        "message": f"Earned {earned:.4f} CTXT",
        "topics": topics,
        "token_count": token_count,
    }


@app.post("/v1/conversations/summarize")
async def summarize_conversation(request: SummarizeRequest):
    """Generate intelligent summary for conversation"""

    # Check cache first
    cache_key = f"summary:{request.session_id}:{request.mode}"
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    # Prepare messages for summarization
    if request.mode == "progressive":
        # Progressive summarization for very long conversations
        summary = await progressive_summarization(request.messages, request.max_length)
    else:
        # Standard summarization
        conversation_text = format_messages_for_summary(request.messages)

        system_prompt = get_summary_system_prompt(request.mode)

        response = await openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Summarize this conversation (max {request.max_length} chars):\n\n{conversation_text[:4000]}",
                },
            ],
            temperature=0.3,
            max_tokens=1000,
        )

        summary = response.choices[0].message.content

    # Extract key points and action items
    analysis = await analyze_conversation_content(request.messages)

    # Generate embedding for summary
    summary_embedding = await get_embedding(summary)

    # Store summary
    summary_doc = {
        "session_id": request.session_id,
        "summary": summary,
        "key_points": analysis["key_points"],
        "action_items": analysis["action_items"],
        "topics": analysis["topics"],
        "mode": request.mode,
        "timestamp": int(datetime.now().timestamp()),
        "message_count": len(request.messages),
        "platform": request.messages[0].platform if request.messages else "unknown",
    }

    # Store summary in LanceDB
    if summaries_table is not None:
        summaries_table.add([summary_doc])

    # Cache for 1 hour
    await redis_client.set(cache_key, json.dumps(summary_doc), ex=3600)

    return summary_doc


@app.post("/v1/conversations/title")
async def generate_title(request: TitleRequest):
    """Generate meaningful title for conversation"""

    # Prepare context
    first_messages = request.messages[:10]
    context = "\n".join([f"{m.role}: {m.text[:200]}" for m in first_messages])

    style_prompts = {
        "descriptive": "Create a clear, descriptive title that captures the main topic",
        "topical": "Create a topic-focused title highlighting the subject matter",
        "creative": "Create an engaging, creative title that captures the essence",
    }

    emoji_instruction = (
        "Include one relevant emoji at the start."
        if request.include_emoji
        else "Do not include emojis."
    )

    prompt = f"""{style_prompts[request.style]} of this conversation. {emoji_instruction}
    Title should be 3-7 words. Be specific and informative.
    
    Conversation start:
    {context}"""

    response = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=50,
    )

    title = response.choices[0].message.content.strip()

    # Update session with title
    await upsert_session(
        {"_id": request.session_id},
        {"$set": {"title": title, "titleGeneratedAt": datetime.now(timezone.utc)}},
    )

    return {"session_id": request.session_id, "title": title, "style": request.style}


@app.post("/v1/conversations/list")
async def list_conversations(request: ConversationListRequest):
    """Get conversation list with titles and summaries for dropdown"""

    # Build query
    query = {"wallet": request.wallet}
    if request.platform:
        query["platform"] = request.platform

    # Get sessions with pagination
    sort_order = (
        [("lastMessage", -1)] if request.sort_by == "recent" else [("messageCount", -1)]
    )

    sessions = []
    if sessions_table is not None:
        try:
            # For sessions table, we need to handle LanceDB Cloud limitations
            # Get all sessions and filter locally
            all_sessions = []
            # For remote LanceDB, we'll return empty for now
            # TODO: Implement proper remote table querying
            all_sessions = []
            # Apply offset locally
            sessions = all_sessions[request.offset :]
        except Exception as e:
            print(f"Error fetching sessions: {e}")
            sessions = []

    # Get summaries for sessions
    session_ids = [s["_id"] for s in sessions]
    summaries = []
    if summaries_table is not None:
        try:
            # For remote LanceDB, return empty for now
            # TODO: Implement proper remote table querying
            summaries = []
        except Exception as e:
            print(f"Error fetching summaries: {e}")
            summaries = []

    summary_map = {s["session_id"]: s for s in summaries}

    # Search filter if provided
    if request.search_query:
        # Vector search in conversations
        search_embedding = await get_embedding(request.search_query)
        conversations_table = lance_db.open_table("conversations_v2")

        search_results = (
            conversations_table.search(
                search_embedding, vector_column_name="text_vector"
            )
            .where(f"wallet = '{request.wallet}'")
            .limit(100)
            .to_list()
        )

        # Get unique session IDs from search
        search_session_ids = {r["session_id"] for r in search_results}

        # Filter sessions
        sessions = [s for s in sessions if s["_id"] in search_session_ids]

    # Format response
    conversations = []
    for session in sessions:
        summary = summary_map.get(session["_id"], {})

        conversation = {
            "session_id": session["_id"],
            "title": session.get(
                "title", f"Conversation on {session.get('platform', 'Unknown')}"
            ),
            "platform": session.get("platform", "unknown"),
            "last_message": session.get(
                "lastMessage", datetime.now(timezone.utc)
            ).isoformat(),
            "message_count": session.get("messageCount", 0),
            "summary_preview": summary.get("summary", "No summary available")[:150]
            + "...",
            "topics": session.get("allTopics", [])[:5],
            "has_action_items": len(summary.get("action_items", [])) > 0,
            "token_count": session.get("totalTokens", 0),
        }

        conversations.append(conversation)

    return {
        "conversations": conversations,
        "total": await count_user_sessions(query["wallet"]),
        "offset": request.offset,
        "limit": request.limit,
    }


# New Models for Export and Sharing
class ExportRequest(BaseModel):
    session_id: str
    format: Literal["txt", "pdf", "markdown", "clipboard"]
    include_metadata: bool = True


class ShareRequest(BaseModel):
    session_id: str
    recipient: str  # email or phone number
    format: Literal["txt", "markdown"] = "txt"
    include_metadata: bool = False


class ConversationHistoryResponse(BaseModel):
    conversations: List[Dict[str, Any]]
    total: int
    platforms: List[str]


@app.get("/v1/conversations/{session_id}/export/{format}")
async def export_conversation(
    session_id: str,
    format: Literal["txt", "pdf", "markdown"],
    current_user: dict = Depends(get_current_user),
    include_metadata: bool = True,
):
    """Export conversation in specified format"""

    if not lance_db:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        # Get conversation messages
        conversations_table = lance_db.open_table("conversations_v2")
        # TODO: Implement proper remote table querying
        # For now, return empty list for remote tables
        messages = []
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve conversation: {str(e)}"
        )

    if not messages:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Sort messages by timestamp
    messages = sorted(messages, key=lambda x: x.get("timestamp", ""))

    # Generate content based on format
    if format == "txt":
        content = generate_txt_export(messages, include_metadata)
        media_type = "text/plain"
        filename = f"conversation_{session_id}.txt"
    elif format == "markdown":
        content = generate_markdown_export(messages, include_metadata)
        media_type = "text/markdown"
        filename = f"conversation_{session_id}.md"
    elif format == "pdf":
        content = await generate_pdf_export(messages, include_metadata)
        media_type = "application/pdf"
        filename = f"conversation_{session_id}.pdf"

    from fastapi.responses import Response

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.post("/v1/conversations/{session_id}/export/clipboard")
async def export_to_clipboard(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    format: Literal["txt", "markdown"] = "txt",
):
    """Prepare conversation content for clipboard"""

    conversations_table = lance_db.open_table("conversations_v2")
    # TODO: Implement proper remote table querying
    # For now, return empty list for remote tables
    messages = []

    if not messages:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = sorted(messages, key=lambda x: x.get("timestamp", ""))

    if format == "txt":
        content = generate_txt_export(messages, include_metadata=False)
    else:
        content = generate_markdown_export(messages, include_metadata=False)

    return {"content": content, "format": format}


@app.post("/v1/conversations/{session_id}/share/email")
async def share_via_email(
    session_id: str,
    request: ShareRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """Share conversation via email"""

    conversations_table = lance_db.open_table("conversations_v2")
    # TODO: Implement proper remote table querying
    # For now, return empty list for remote tables
    messages = []

    if not messages:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Add background task to send email
    background_tasks.add_task(
        send_conversation_email,
        messages,
        request.recipient,
        request.format,
        request.include_metadata,
    )

    return {"status": "Email queued for delivery", "recipient": request.recipient}


@app.post("/v1/conversations/{session_id}/share/sms")
async def share_via_sms(
    session_id: str,
    request: ShareRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """Share conversation via SMS"""

    conversations_table = lance_db.open_table("conversations_v2")
    # TODO: Implement proper remote table querying
    # For now, return empty list for remote tables
    messages = []

    if not messages:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # SMS has character limits, so we'll send a summary
    summary_content = generate_txt_export(
        messages[:3], include_metadata=False
    )  # First 3 messages
    if len(summary_content) > 160:
        summary_content = summary_content[:157] + "..."

    # Add background task to send SMS
    background_tasks.add_task(send_conversation_sms, summary_content, request.recipient)

    return {"status": "SMS queued for delivery", "recipient": request.recipient}


@app.get("/v1/conversations/history")
async def get_conversation_history(
    current_user: dict = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0,
    platform: Optional[str] = None,
):
    """Get user's conversation history across all platforms"""

    conversations_table = lance_db.open_table("conversations_v2")

    # Build query
    query_conditions = [f"wallet = '{current_user['wallet']}'"]
    if platform:
        query_conditions.append(f"platform = '{platform}'")

    where_clause = " AND ".join(query_conditions)

    # Get conversations - for remote LanceDB, get all and filter locally
    try:
        # TODO: Implement proper remote table querying
        # For now, return empty DataFrame for remote tables
        import pandas as pd

        df = pd.DataFrame()
        # Apply limit and offset
        # df = df.tail(limit + offset).head(limit) if offset > 0 else df.tail(limit)
        results = df.to_dict("records")
    except Exception as e:
        print(f"Error querying conversations: {e}")
        results = []

    # Group by session_id and get latest message from each
    session_groups = defaultdict(list)
    for msg in results:
        session_groups[msg["session_id"]].append(msg)

    conversations = []
    platforms = set()

    for session_id, messages in session_groups.items():
        if len(conversations) >= limit:
            break

        # Sort messages by timestamp
        messages = sorted(messages, key=lambda x: x.get("timestamp", ""))
        latest_msg = messages[-1]
        first_msg = messages[0]

        platforms.add(latest_msg.get("platform", "unknown"))

        # Generate preview
        preview = first_msg.get("text", "")[:100]
        if len(first_msg.get("text", "")) > 100:
            preview += "..."

        conversations.append(
            {
                "session_id": session_id,
                "platform": latest_msg.get("platform", "unknown"),
                "title": generate_conversation_title(messages),
                "preview": preview,
                "message_count": len(messages),
                "last_updated": latest_msg.get("timestamp"),
                "created_at": first_msg.get("timestamp"),
                "estimated_tokens": sum(
                    len(encoding.encode(msg.get("text", ""))) for msg in messages
                ),
            }
        )

    # Sort by last_updated
    conversations = sorted(
        conversations, key=lambda x: x.get("last_updated", ""), reverse=True
    )

    return ConversationHistoryResponse(
        conversations=conversations[offset : offset + limit],
        total=len(session_groups),
        platforms=list(platforms),
    )


# Helper functions for export formats
def generate_txt_export(messages: List[Dict], include_metadata: bool = True) -> str:
    """Generate plain text export"""
    lines = []

    if include_metadata and messages:
        lines.append(f"Conversation Export")
        lines.append(f"Platform: {messages[0].get('platform', 'Unknown')}")
        lines.append(f"Date: {messages[0].get('timestamp', 'Unknown')}")
        lines.append(f"Messages: {len(messages)}")
        lines.append("=" * 50)
        lines.append("")

    for msg in messages:
        role = msg.get("role", "unknown").upper()
        text = msg.get("text", "")
        timestamp = msg.get("timestamp", "")

        if include_metadata and timestamp:
            lines.append(f"[{timestamp}] {role}:")
        else:
            lines.append(f"{role}:")

        lines.append(text)
        lines.append("")

    return "\n".join(lines)


def generate_markdown_export(
    messages: List[Dict], include_metadata: bool = True
) -> str:
    """Generate Markdown export"""
    lines = []

    if include_metadata and messages:
        lines.append("# Conversation Export")
        lines.append("")
        lines.append(f"**Platform:** {messages[0].get('platform', 'Unknown')}")
        lines.append(f"**Date:** {messages[0].get('timestamp', 'Unknown')}")
        lines.append(f"**Messages:** {len(messages)}")
        lines.append("")
        lines.append("---")
        lines.append("")

    for i, msg in enumerate(messages):
        role = msg.get("role", "unknown").title()
        text = msg.get("text", "")
        timestamp = msg.get("timestamp", "")

        if include_metadata and timestamp:
            lines.append(f"## {role} - {timestamp}")
        else:
            lines.append(f"## {role}")

        lines.append("")
        lines.append(text)
        lines.append("")

    return "\n".join(lines)


async def generate_pdf_export(
    messages: List[Dict], include_metadata: bool = True
) -> bytes:
    """Generate PDF export using ReportLab"""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib.colors import HexColor
        from io import BytesIO

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=letter, topMargin=1 * inch, bottomMargin=1 * inch
        )
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=20,
            textColor=HexColor("#2563eb"),
            alignment=1,  # Center alignment
            spaceAfter=30,
        )

        message_header_style = ParagraphStyle(
            "MessageHeader",
            parent=styles["Heading3"],
            fontSize=12,
            textColor=HexColor("#374151"),
            spaceBefore=15,
            spaceAfter=5,
        )

        message_body_style = ParagraphStyle(
            "MessageBody",
            parent=styles["Normal"],
            fontSize=10,
            leftIndent=20,
            spaceAfter=10,
        )

        story = []

        # Add title and metadata
        story.append(Paragraph("Contextly Conversation Export", title_style))

        if include_metadata and messages:
            story.append(
                Paragraph(
                    f"<b>Platform:</b> {messages[0].get('platform', 'Unknown')}",
                    styles["Normal"],
                )
            )
            story.append(
                Paragraph(
                    f"<b>Export Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    styles["Normal"],
                )
            )
            story.append(
                Paragraph(f"<b>Total Messages:</b> {len(messages)}", styles["Normal"])
            )
            story.append(Spacer(1, 20))

        # Add messages
        for i, msg in enumerate(messages):
            role = msg.get("role", "unknown").title()
            text = msg.get("text", "").replace("\n", "<br/>")
            timestamp = msg.get("timestamp", "")

            # Message header
            if include_metadata and timestamp:
                header_text = f"{role} - {timestamp}"
            else:
                header_text = role

            story.append(Paragraph(header_text, message_header_style))

            # Message content
            story.append(Paragraph(text, message_body_style))

            # Add separator line except for last message
            if i < len(messages) - 1:
                story.append(Spacer(1, 10))

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    except ImportError:
        # Fallback if reportlab not available
        content = generate_txt_export(messages, include_metadata)
        return content.encode("utf-8")


def generate_conversation_title(messages: List[Dict]) -> str:
    """Generate a title for conversation history"""
    if not messages:
        return "Empty Conversation"

    first_msg = messages[0]
    text = first_msg.get("text", "")

    # Simple title generation - take first few words
    words = text.split()[:6]
    title = " ".join(words)

    if len(words) >= 6:
        title += "..."

    return title or "Untitled Conversation"


async def send_conversation_email(
    messages: List[Dict], recipient: str, format: str, include_metadata: bool
):
    """Background task to send conversation via email"""
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail, Attachment
        import base64

        api_key = os.getenv("SENDGRID_API_KEY")
        from_email = os.getenv("SENDGRID_FROM_EMAIL", "noreply@contextly.ai")

        if not api_key:
            print("⚠️ SendGrid API key not configured, skipping email")
            return

        # Generate content based on format
        if format == "txt":
            content = generate_txt_export(messages, include_metadata)
            subject = "Your Contextly Conversation Export (Text)"
            filename = (
                f"contextly_conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            )
        elif format == "pdf":
            content_bytes = await generate_pdf_export(messages, include_metadata)
            content = base64.b64encode(content_bytes).decode()
            subject = "Your Contextly Conversation Export (PDF)"
            filename = (
                f"contextly_conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            )
        else:  # markdown
            content = generate_markdown_export(messages, include_metadata)
            subject = "Your Contextly Conversation Export (Markdown)"
            filename = (
                f"contextly_conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            )

        # Create email
        message = Mail(
            from_email=from_email,
            to_emails=recipient,
            subject=subject,
            html_content=f"""
            <h2>Your Contextly Conversation Export</h2>
            <p>Hi there!</p>
            <p>Your conversation export from Contextly is ready. Please find the attached file with your conversation history.</p>
            <p><strong>Export Details:</strong></p>
            <ul>
                <li>Format: {format.upper()}</li>
                <li>Messages: {len(messages)}</li>
                <li>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</li>
            </ul>
            <p>Thank you for using Contextly!</p>
            <p>Best regards,<br>The Contextly Team</p>
            """,
        )

        # Add attachment
        if format == "pdf":
            attachment = Attachment(
                file_content=content,
                file_type="application/pdf",
                file_name=filename,
                disposition="attachment",
            )
        else:
            attachment = Attachment(
                file_content=base64.b64encode(content.encode()).decode(),
                file_type="text/plain" if format == "txt" else "text/markdown",
                file_name=filename,
                disposition="attachment",
            )

        message.attachment = attachment

        # Send email
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)

        if response.status_code == 202:
            print(f"📧 Email sent successfully to {recipient}")
        else:
            print(f"❌ Email failed with status: {response.status_code}")

    except ImportError:
        print("⚠️ SendGrid not available, falling back to console log")
        print(f"📧 Would send conversation to {recipient} in {format} format")
    except Exception as e:
        print(f"❌ Email sending failed: {str(e)}")


async def send_conversation_sms(content: str, recipient: str):
    """Background task to send conversation via SMS"""
    try:
        from twilio.rest import Client

        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        from_number = os.getenv("TWILIO_FROM_NUMBER")

        if not all([account_sid, auth_token, from_number]):
            print("⚠️ Twilio credentials not configured, skipping SMS")
            return

        client = Client(account_sid, auth_token)

        # Ensure content fits SMS limit (160 chars including header)
        header = "Contextly Export: "
        max_content = 160 - len(header) - 3  # -3 for "..."

        if len(content) > max_content:
            sms_content = header + content[:max_content] + "..."
        else:
            sms_content = header + content

        message = client.messages.create(
            body=sms_content, from_=from_number, to=recipient
        )

        print(f"📱 SMS sent successfully to {recipient}. SID: {message.sid}")

    except ImportError:
        print("⚠️ Twilio not available, falling back to console log")
        print(f"📱 Would send SMS to {recipient}: {content[:50]}...")
    except Exception as e:
        print(f"❌ SMS sending failed: {str(e)}")


@app.get("/v1/conversations/{session_id}/full")
async def get_full_conversation(
    session_id: str, current_user: dict = Depends(get_current_user)
):
    """Get full conversation for insertion into chat"""

    conversations_table = lance_db.open_table("conversations_v2")
    # TODO: Implement proper remote table querying
    # For now, return empty list for remote tables
    messages = []

    if not messages:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Sort messages by timestamp
    messages = sorted(messages, key=lambda x: x.get("timestamp", ""))

    return {
        "session_id": session_id,
        "messages": messages,
        "platform": messages[0].get("platform") if messages else None,
        "message_count": len(messages),
        "estimated_tokens": sum(
            len(encoding.encode(msg.get("text", ""))) for msg in messages
        ),
    }


@app.post("/v1/graph/build")
async def build_conversation_graph(session_id: str, wallet: str):
    """Build knowledge graph from conversation"""

    # Verify user
    user = await find_user_by_wallet(wallet)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get all messages for session
    conversations_table = lance_db.open_table("conversations_v2")
    # TODO: Implement proper remote table querying
    # For now, return empty list for remote tables
    messages = []

    if not messages:
        raise HTTPException(status_code=404, detail="No messages found")

    # Build graph
    all_entities = []
    all_relationships = []

    for msg in messages:
        if msg["role"] == "assistant":  # Focus on AI responses for richer content
            # Extract entities and relationships
            entities, relationships = await extract_entities_relationships(msg["text"])
            all_entities.extend(entities)
            all_relationships.extend(relationships)

    # Build NetworkX graph
    G = build_knowledge_graph(all_entities, all_relationships)

    # Detect communities
    communities = detect_communities(G)

    # Generate community summaries
    community_summaries = []
    for i, community in enumerate(communities):
        summary = await generate_community_summary(community, G)
        community_summaries.append(
            {"id": i, "entities": community, "summary": summary, "size": len(community)}
        )

    # Calculate graph metrics
    metrics = {
        "node_count": G.number_of_nodes(),
        "edge_count": G.number_of_edges(),
        "community_count": len(communities),
        "density": nx.density(G),
        "avg_degree": (
            sum(dict(G.degree()).values()) / G.number_of_nodes()
            if G.number_of_nodes() > 0
            else 0
        ),
    }

    # Store graph embeddings
    graph_table = lance_db.open_table("graph_embeddings")

    for node in G.nodes():
        node_data = G.nodes[node]
        node_text = (
            f"{node} {node_data.get('type', '')} {node_data.get('description', '')}"
        )
        embedding = await get_embedding(node_text, "sentence")

        graph_table.add(
            [
                {
                    "entity_id": f"{session_id}_{node}",
                    "entity_name": node,
                    "entity_type": node_data.get("type", "unknown"),
                    "embedding": embedding,
                    "community_id": next(
                        (i for i, comm in enumerate(communities) if node in comm), -1
                    ),
                    "centrality_score": nx.degree_centrality(G).get(node, 0),
                    "timestamp": int(datetime.now().timestamp()),
                }
            ]
        )

    # Store graph in MongoDB
    graph_doc = {
        "_id": f"graph_{session_id}",
        "session_id": session_id,
        "wallet": wallet,
        "entities": [e.dict() for e in all_entities],
        "relationships": [r.dict() for r in all_relationships],
        "communities": community_summaries,
        "metrics": metrics,
        "created": datetime.now(timezone.utc),
    }

    # Store graph in LanceDB
    if graphs_table is not None:
        graphs_table.add([graph_doc])

    # Update user stats
    await update_user_earnings(user["_id"], 0.0, graph_nodes_delta=G.number_of_nodes())

    return {
        "success": True,
        "graph_id": graph_doc["_id"],
        "metrics": metrics,
        "communities": len(communities),
        "main_entities": [
            n for n, d in sorted(G.degree(), key=lambda x: x[1], reverse=True)
        ][:10],
    }


@app.post("/v1/graph/query")
async def query_knowledge_graph(
    query: str, session_id: Optional[str] = None, wallet: Optional[str] = None
):
    """Query knowledge graph with natural language"""

    try:
        # Get query embedding
        query_embedding = await get_embedding(query, "sentence")
    except Exception as e:
        print(f"❌ Failed to get embedding: {e}")
        return {"results": [], "error": f"Failed to process query: {str(e)}"}

    # Search in graph embeddings
    if graph_embeddings_table is None:
        return {"results": [], "message": "Graph embeddings not available"}

    try:
        search_query = graph_embeddings_table.search(query_embedding).limit(20)

        if session_id:
            # Escape session_id to prevent SQL injection
            safe_session_id = session_id.replace("'", "''")
            search_query = search_query.where(f"entity_id LIKE '{safe_session_id}_%'")

        results = search_query.to_list()
    except Exception as e:
        print(f"❌ Error searching graph embeddings: {e}")
        return {"results": [], "error": f"Search failed: {str(e)}"}

    if not results:
        return {"results": [], "message": "No relevant entities found"}

    # Get graph data for context
    if session_id:
        graph = None
        if graphs_table is not None:
            # TODO: Implement proper remote table querying
            # For now, return None for remote tables
            graph = None

        if graph:
            # Build response with graph context
            relevant_entities = [r["entity_name"] for r in results[:5]]

            # Find relevant relationships
            relevant_relationships = [
                rel
                for rel in graph["relationships"]
                if rel["source"] in relevant_entities
                or rel["target"] in relevant_entities
            ]

            # Generate contextual answer
            context = f"""Based on the knowledge graph, here are the relevant entities: {', '.join(relevant_entities)}
            
            Key relationships:
            {chr(10).join([f"- {r['source']} {r['type']} {r['target']}" for r in relevant_relationships[:5]])}"""

            response = await openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "Answer the query based on the knowledge graph context provided.",
                    },
                    {
                        "role": "user",
                        "content": f"Query: {query}\n\nContext:\n{context}",
                    },
                ],
                temperature=0.3,
                max_tokens=500,
            )

            answer = response.choices[0].message.content
        else:
            answer = "Knowledge graph not found for this session."
    else:
        # General search across all graphs
        answer = f"Found {len(results)} relevant entities across all conversations."

    return {
        "query": query,
        "answer": answer,
        "entities": [
            {
                "name": r["entity_name"],
                "type": r["entity_type"],
                "relevance": float(r.get("_distance", 0)),
                "community_id": r["community_id"],
            }
            for r in results[:10]
        ],
        "session_id": session_id,
    }


@app.post("/v1/transfer/prepare")
async def prepare_transfer(request: TransferRequest):
    """Prepare context for cross-platform transfer with graph enhancement"""

    if request.mode == "graph-enhanced":
        # Use knowledge graph for enhanced context
        graph = None
        if graphs_table is not None:
            # TODO: Implement proper remote table querying
            # For now, return None for remote tables
            graph = None

        if graph:
            # Get key entities and relationships
            key_entities = sorted(
                graph["entities"],
                key=lambda x: len(
                    [
                        r
                        for r in graph["relationships"]
                        if r["source"] == x["name"] or r["target"] == x["name"]
                    ]
                ),
                reverse=True,
            )[:10]

            context = await create_graph_enhanced_summary(
                request.messages,
                key_entities,
                graph["communities"],
                request.from_platform,
                request.to_platform,
            )
        else:
            # Fallback to smart mode
            context = await create_smart_summary(
                request.messages, request.from_platform, request.to_platform
            )
    elif request.mode == "smart":
        # Vector-based smart summary
        context = await create_smart_summary(
            request.messages, request.from_platform, request.to_platform
        )
    else:
        # Full conversation
        context = format_full_conversation(request.messages, request.to_platform)

    return {
        "success": True,
        "context": context,
        "token_count": len(encoding.encode(context)),
        "mode": request.mode,
    }


@app.post("/v1/insights/generate")
async def generate_insights(
    time_range: Optional[int] = 7,
    current_user: AuthenticatedUser = Depends(get_current_user_obj),
):
    """Generate insights from user's conversations"""

    # Get user's recent sessions
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=time_range)

    # Get sessions from LanceDB
    sessions = []
    if sessions_table is not None:
        try:
            # For sessions table, handle LanceDB Cloud limitations
            cutoff_ts = int(cutoff_date.timestamp())
            try:
                # TODO: Implement proper remote table querying
                # For now, return empty list for remote tables
                sessions = []
            except Exception as e:
                print(f"Error in session query: {e}")
                sessions = []
        except Exception as e:
            print(f"❌ Error accessing sessions table: {e}")
            return {"insights": [], "message": f"Error accessing sessions: {str(e)}"}
    else:
        return {"insights": [], "message": "Sessions table not available"}

    if not sessions:
        return {"insights": [], "message": "No recent conversations found"}

    # Aggregate topics
    all_topics = []
    for session in sessions:
        all_topics.extend(session.get("allTopics", []))

    topic_counts = defaultdict(int)
    for topic in all_topics:
        topic_counts[topic] += 1

    # Get conversation patterns
    platform_usage = defaultdict(int)
    hourly_activity = defaultdict(int)

    for session in sessions:
        platform_usage[session.get("platform", "unknown")] += session.get(
            "messageCount", 0
        )
        last_message = session.get("lastMessage", None)
        if last_message:
            # Handle timestamp as int or datetime
            if isinstance(last_message, int):
                hour = datetime.fromtimestamp(last_message).hour
            elif hasattr(last_message, "hour"):
                hour = last_message.hour
            else:
                hour = datetime.now().hour
            hourly_activity[hour] += 1

    # Generate insights using GPT-4
    insights_prompt = f"""Based on this user activity data, generate 3-5 key insights:

Top topics: {dict(sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:10])}
Platform usage: {dict(platform_usage)}
Activity patterns: Most active hours are {sorted(hourly_activity.items(), key=lambda x: x[1], reverse=True)[:3]}
Total conversations: {len(sessions)}
Average conversation length: {sum(s.get('messageCount', 0) for s in sessions) / len(sessions):.1f} messages

Provide actionable insights about the user's AI usage patterns, interests, and recommendations."""

    response = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": insights_prompt}],
        temperature=0.5,
        max_tokens=500,
    )

    insights = response.choices[0].message.content.split("\n")
    insights = [i.strip() for i in insights if i.strip() and not i.startswith("#")]

    return {
        "insights": insights,
        "stats": {
            "total_conversations": len(sessions),
            "top_topics": sorted(
                topic_counts.items(), key=lambda x: x[1], reverse=True
            )[:5],
            "platform_distribution": dict(platform_usage),
            "time_range_days": time_range,
        },
    }


@app.post("/v1/journeys/analyze")
async def analyze_journey(batch: JourneyBatch):
    """Analyze screenshots using GPT-4o with enhanced processing"""

    user = await find_user_by_wallet(batch.wallet)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prepare messages for GPT-4o
    messages = [
        {
            "role": "system",
            "content": """Analyze these screenshots to understand the user's journey.
            Identify what they're trying to accomplish, key actions, and patterns.
            Be specific about the steps taken and the apparent goal.""",
        }
    ]

    # Add screenshots
    for i, screenshot in enumerate(batch.screenshots):
        messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Screenshot {i+1}: {screenshot.title} - {screenshot.url}",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{screenshot.screenshot}"
                        },
                    },
                ],
            }
        )

    # Get structured analysis
    response = await openai_client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=messages,
        response_format=JourneyAnalysis,
        temperature=0.3,
        max_tokens=1000,
    )

    analysis = response.choices[0].message.parsed

    # Calculate journey metrics
    duration_seconds = (
        (batch.screenshots[-1].timestamp - batch.screenshots[0].timestamp)
        if len(batch.screenshots) > 1
        else 0
    )

    # Calculate enhanced earnings
    base_rate = 0.05
    quality_bonus = analysis.quality_score * 0.05
    complexity_bonus = 0.02 if len(analysis.actions) > 5 else 0
    earned = base_rate + quality_bonus + complexity_bonus

    # Generate embedding for journey
    journey_text = f"{analysis.summary} {analysis.intent} {' '.join(analysis.patterns)}"
    journey_embedding = await get_embedding(journey_text)

    # Store in enhanced LanceDB table
    journeys_table = lance_db.open_table("journeys_v2")
    journey_record = {
        "journey_id": analysis.journey_id,
        "wallet": batch.wallet,
        "summary": analysis.summary,
        "summary_vector": journey_embedding,
        "intent": analysis.intent,
        "category": analysis.category,
        "quality_score": analysis.quality_score,
        "action_count": len(analysis.actions),
        "duration_seconds": duration_seconds,
        "timestamp": int(datetime.now().timestamp()),
    }
    journeys_table.add([journey_record])

    # Store full analysis in MongoDB
    journey_doc = {
        "_id": analysis.journey_id,
        "userId": user["_id"],
        "wallet": batch.wallet,
        "sessionId": batch.session_id,
        "analysis": analysis.model_dump(),
        "screenshotCount": len(batch.screenshots),
        "earned": earned,
        "duration": duration_seconds,
        "created": datetime.now(timezone.utc),
    }
    # TODO: Replace with LanceDB journeys table insert journey_doc

    # Update user stats
    await update_user_earnings(user["_id"], earned, journey_delta=1)

    return {
        "success": True,
        "journey_id": analysis.journey_id,
        "analysis": analysis.model_dump(),
        "earned": earned,
        "duration_seconds": duration_seconds,
    }


@app.get("/v1/stats/{wallet}")
async def get_user_stats(wallet: str):
    """Get enhanced user statistics"""

    user = await find_user_by_wallet(wallet)
    if not user:
        # Create a new user if not found
        user_id = f"user_{wallet[-8:]}"
        now = datetime.now()
        user_data = {
            "_id": user_id,
            "wallet": wallet,
            "created": int(now.timestamp()),
            "created_at": now.isoformat(),
            "total_earnings": 0.0,
            "message_count": 0,
            "journey_count": 0,
            "graph_count": 0,
            "graph_nodes_created": 0,
            "last_active": now.isoformat(),
            # Enhanced token tracking fields
            "total_tokens": 0,
            "tokens_by_platform": {},
            "tokens_by_role": {"user": 0, "assistant": 0},
            "daily_tokens": {},
            "last_token_update": None,
        }
        await create_user(user_data)
        user = user_data

    # Get today's earnings
    today = datetime.now().date()
    message_key = f"earnings:{wallet}:{today}"
    journey_key = f"journey_earnings:{wallet}:{today}"

    message_earnings = await redis_client.get(message_key) or "0"
    journey_earnings = await redis_client.get(journey_key) or "0"

    today_earnings = float(message_earnings) * 0.001 + float(journey_earnings)

    # Get conversation stats
    conversation_count = await count_user_sessions(wallet)

    # Get recent activity
    recent_sessions = []
    if sessions_table is not None:
        try:
            # TODO: Implement proper remote table querying
            # For now, return empty list for remote tables
            wallet_sessions = []
        except Exception as e:
            print(f"Error in wallet sessions query: {e}")
            wallet_sessions = []
        recent_sessions = sorted(
            wallet_sessions, key=lambda x: x.get("last_message", 0), reverse=True
        )[:5]

    # Get graph stats
    graph_count = 0
    if graphs_table is not None:
        try:
            # TODO: Implement proper remote table querying
            # For now, return empty list for remote tables
            user_graphs = []
            graph_count = 0
        except Exception as e:
            print(f"Error in graphs query: {e}")
            user_graphs = []
            graph_count = 0

    # Handle different key formats (from cache vs database)
    total_earnings = user.get("total_earnings") or user.get("totalEarnings", 0.0)
    journey_count = user.get("journey_count") or user.get("journeyCount", 0)
    graph_nodes = user.get("graph_nodes_created") or user.get("graphNodesCreated", 0)
    
    # Handle created timestamp
    created = user.get("created")
    if isinstance(created, str):
        # If it's an ISO string, parse it
        joined_date = created
    elif isinstance(created, (int, float)):
        # If it's a timestamp, convert it
        joined_date = datetime.fromtimestamp(created).isoformat()
    else:
        joined_date = datetime.now().isoformat()
    
    return {
        "wallet": wallet,
        "totalEarnings": total_earnings,
        "todayEarnings": today_earnings,
        "conversationCount": conversation_count,
        "journeyCount": journey_count,
        "graphNodesCreated": graph_nodes,
        "knowledgeGraphs": graph_count,
        "joined": joined_date,
        "recentActivity": [
            {
                "session_id": s["_id"],
                "platform": s.get("platform", "unknown"),
                "title": s.get("title", "Untitled"),
                "lastMessage": s.get("lastMessage", datetime.now()).isoformat(),
            }
            for s in recent_sessions
        ],
    }


# New API Endpoints for Graph Visualization and Journey Analytics


@app.post("/v1/graph/visualize")
async def visualize_knowledge_graph(
    request: Dict[str, Any],
    current_user: AuthenticatedUser = Depends(get_current_user_obj),
):
    """Generate graph visualization data with Neo4j-like structure"""

    # Track activity
    await track_session_activity(
        current_user,
        "graph_visualization",
        {
            "session_id": request.get("session_id"),
            "max_nodes": request.get("max_nodes", 100),
        },
    )

    # Extract request parameters
    wallet = request.get("wallet", current_user.wallet)
    session_id = request.get("session_id")
    filters = request.get("filter", {})
    layout = request.get("layout", "force")
    max_nodes = request.get("max_nodes", 100)

    # Verify user owns this data
    if wallet and wallet != current_user.wallet:
        raise HTTPException(
            status_code=403, detail="Cannot access another user's graph"
        )

    # Build query for graph embeddings
    if graph_embeddings_table is None:
        return {"nodes": [], "edges": [], "message": "Graph embeddings not available"}

    # Apply filters
    conditions = []
    if session_id:
        conditions.append(f"entity_id LIKE '{session_id}_%'")

    if filters.get("entity_types"):
        types_str = "','".join(filters["entity_types"])
        conditions.append(f"entity_type IN ('{types_str}')")

    if filters.get("min_centrality"):
        conditions.append(f"centrality_score >= {filters['min_centrality']}")

    if filters.get("community_id") is not None:
        conditions.append(f"community_id = {filters['community_id']}")

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # Get entities
    try:
        if graph_embeddings_table is None:
            return {
                "nodes": [],
                "edges": [],
                "communities": [],
                "stats": {},
                "message": "Graph embeddings table not available",
            }

        # TODO: Implement proper remote table querying
        # For now, return empty list for remote tables
        all_entities = []

        # Apply local filtering if needed
        entities = all_entities
        if filters.get("min_centrality"):
            entities = [
                e
                for e in entities
                if e.get("centrality_score", 0) >= filters["min_centrality"]
            ]
        if filters.get("community_id") is not None:
            entities = [
                e for e in entities if e.get("community_id") == filters["community_id"]
            ]

    except Exception as e:
        print(f"❌ Error accessing graph embeddings: {e}")
        return {
            "nodes": [],
            "edges": [],
            "communities": [],
            "stats": {},
            "error": f"Failed to load graph data: {str(e)}",
        }

    if not entities:
        return {
            "nodes": [],
            "edges": [],
            "communities": [],
            "stats": {},
            "message": "No graph data available",
        }

    # Build nodes for visualization
    nodes = []
    entity_map = {}

    for entity in entities:
        try:
            # Safely access fields with defaults
            entity_id = entity.get("entity_id", "unknown")
            entity_name = entity.get("entity_name", "Unknown Entity")
            entity_type = entity.get("entity_type", "unknown")
            centrality = float(entity.get("centrality_score", 0.5))
            community_id = entity.get("community_id", 0)
            timestamp = entity.get("timestamp", 0)

            node = {
                "id": entity_id,
                "label": entity_name,
                "type": entity_type,
                "size": max(10, centrality * 50),  # Scale for visualization
                "color": f"#{hash(str(community_id)) % 0xFFFFFF:06x}",
                "metadata": {
                    "centrality_score": centrality,
                    "community_id": community_id,
                    "occurrence_count": 1,  # Would be tracked in real implementation
                    "first_seen": (
                        datetime.fromtimestamp(timestamp).isoformat()
                        if timestamp
                        else "unknown"
                    ),
                    "last_seen": (
                        datetime.fromtimestamp(timestamp).isoformat()
                        if timestamp
                        else "unknown"
                    ),
                },
            }
            nodes.append(node)
            entity_map[entity_name] = node
        except Exception as e:
            print(f"⚠️ Error processing entity: {e}")
            continue

    # Get relationships between entities (simplified - in production, store in graph DB)
    edges = []

    # For demo, create edges between entities in same community
    communities = defaultdict(list)
    entity_id_by_name = {}  # Map entity names to their IDs for edge creation

    for entity in entities:
        community_id = entity.get("community_id", 0)
        entity_name = entity.get("entity_name", "Unknown Entity")
        entity_id = entity.get("entity_id", "unknown")

        communities[community_id].append(entity_id)  # Store entity_id, not name
        entity_id_by_name[entity_name] = entity_id

    for community_id, entity_ids in communities.items():
        # Create edges within community (simplified)
        for i in range(len(entity_ids)):
            for j in range(i + 1, min(i + 3, len(entity_ids))):  # Limit connections
                edges.append(
                    {
                        "source": entity_ids[i],  # Use actual entity_id
                        "target": entity_ids[j],  # Use actual entity_id
                        "type": "relates_to",
                        "weight": 0.5 + (0.5 * random.random()),
                        "label": "related",
                    }
                )

    # Get community information
    community_info = []
    for community_id, entity_ids in communities.items():
        community_info.append(
            {
                "id": community_id,
                "color": f"#{hash(community_id) % 0xFFFFFF:06x}",
                "label": f"Community {community_id}",
                "node_count": len(entity_ids),
            }
        )

    # Calculate statistics
    stats = {
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "density": (
            len(edges) / (len(nodes) * (len(nodes) - 1) / 2) if len(nodes) > 1 else 0
        ),
        "avg_degree": (2 * len(edges)) / len(nodes) if nodes else 0,
    }

    return {
        "nodes": nodes,
        "edges": edges,
        "communities": community_info,
        "stats": stats,
    }


@app.post("/v1/journeys/sankey")
async def generate_journey_sankey(
    request: Dict[str, Any],
    current_user: AuthenticatedUser = Depends(get_current_user_obj),
):
    """Generate Sankey diagram data for user journeys"""

    # Track activity
    await track_session_activity(
        current_user,
        "journey_sankey",
        {
            "aggregate": request.get("aggregate", False),
            "granularity": request.get("granularity", "domain"),
        },
    )

    # Extract parameters
    wallet = request.get("wallet", current_user.wallet)
    aggregate = request.get("aggregate", False)
    filters = request.get("filter", {})
    granularity = request.get("granularity", "domain")

    # Verify permissions
    if not aggregate and wallet != current_user.wallet:
        raise HTTPException(
            status_code=403, detail="Cannot access another user's journey data"
        )

    # Build query
    if journeys_table is None:
        return {"nodes": [], "links": [], "message": "Journeys table not available"}

    conditions = []
    if not aggregate and wallet:
        conditions.append(f"wallet = '{wallet}'")

    if filters.get("date_range"):
        start_ts = int(
            datetime.fromisoformat(filters["date_range"]["start"]).timestamp()
        )
        end_ts = int(datetime.fromisoformat(filters["date_range"]["end"]).timestamp())
        conditions.append(f"timestamp >= {start_ts}")
        conditions.append(f"timestamp <= {end_ts}")

    if filters.get("min_duration"):
        conditions.append(f"duration_seconds >= {filters['min_duration']}")

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # Get journey data
    try:
        if journeys_table is None:
            # If table doesn't exist, create it
            print("⚠️ Journeys table not initialized, attempting to create...")
            # Return empty data for now
            return {
                "nodes": [],
                "links": [],
                "patterns": [],
                "insights": {},
                "message": "Journeys table not available",
            }

        # TODO: Implement proper remote table querying
        # For now, return empty DataFrame for remote tables
        import pandas as pd

        df = pd.DataFrame()
        # Apply filters locally for remote LanceDB
        # if not aggregate and wallet:
        #     df = df[df['wallet'] == wallet]
        # Add more filtering as needed
    except Exception as e:
        print(f"❌ Error accessing journeys table: {e}")
        df = pd.DataFrame()

    if df.empty:
        return {"nodes": [], "links": [], "patterns": [], "insights": {}}

    # Process journeys into nodes and links
    nodes = {}
    links = defaultdict(lambda: {"value": 0, "durations": []})

    # For simplified implementation, we'll use categories as nodes
    for _, journey in df.iterrows():
        # Create a simple flow based on intent and category
        source = journey["intent"]
        target = journey["category"]

        # Add nodes
        if source not in nodes:
            nodes[source] = {
                "id": source,
                "name": source.replace("_", " ").title(),
                "type": "source",
                "visits": 0,
            }

        if target not in nodes:
            nodes[target] = {
                "id": target,
                "name": target.replace("_", " ").title(),
                "type": "target",
                "visits": 0,
            }

        # Update visits
        nodes[source]["visits"] += 1
        nodes[target]["visits"] += 1

        # Add link
        link_key = f"{source}->{target}"
        links[link_key]["value"] += 1
        links[link_key]["durations"].append(journey["duration_seconds"])

    # Format links
    formatted_links = []
    for link_key, link_data in links.items():
        source, target = link_key.split("->")
        formatted_links.append(
            {
                "source": source,
                "target": target,
                "value": link_data["value"],
                "avg_duration": (
                    sum(link_data["durations"]) / len(link_data["durations"])
                    if link_data["durations"]
                    else 0
                ),
                "conversion_rate": 0.8,  # Placeholder
            }
        )

    # Find patterns
    intent_category_pairs = (
        df.groupby(["intent", "category"]).size().reset_index(name="count")
    )
    patterns = [
        {
            "pattern": [row["intent"], row["category"]],
            "frequency": row["count"],
            "avg_quality_score": df[
                (df["intent"] == row["intent"]) & (df["category"] == row["category"])
            ]["quality_score"].mean(),
        }
        for _, row in intent_category_pairs.nlargest(10, "count").iterrows()
    ]

    # Calculate insights
    most_common_paths = [[p["pattern"][0], p["pattern"][1]] for p in patterns[:5]]

    # Dropout analysis (simplified)
    category_counts = df["category"].value_counts()
    dropout_points = [
        {"page": category, "dropout_rate": 0.1 + (0.2 * random.random())}  # Placeholder
        for category in category_counts.index[:5]
    ]

    # High value paths
    high_value = df.nlargest(5, "quality_score")[
        ["intent", "category", "quality_score"]
    ]
    high_value_paths = [
        {
            "path": [row["intent"], row["category"]],
            "avg_earnings": row["quality_score"]
            * 0.1,  # Convert score to earnings estimate
        }
        for _, row in high_value.iterrows()
    ]

    return {
        "nodes": list(nodes.values()),
        "links": formatted_links,
        "patterns": patterns,
        "insights": {
            "most_common_paths": most_common_paths,
            "dropout_points": dropout_points,
            "high_value_paths": high_value_paths,
        },
    }


# X (Twitter) Authentication Endpoints


@app.get("/v1/auth/x/login")
async def x_auth_login_page():
    """Display X OAuth login page"""
    return HTMLResponse(
        """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Connect to X (Twitter) - Contextly</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                margin: 0;
                padding: 40px 20px;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .container {
                background: white;
                border-radius: 12px;
                padding: 40px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.1);
                text-align: center;
                max-width: 400px;
                width: 100%;
            }
            .logo {
                font-size: 24px;
                font-weight: bold;
                color: #1d4ed8;
                margin-bottom: 8px;
            }
            .subtitle {
                color: #6b7280;
                margin-bottom: 32px;
            }
            .x-logo {
                font-size: 48px;
                margin-bottom: 24px;
            }
            .connect-btn {
                background: #1d9bf0;
                color: white;
                border: none;
                padding: 12px 32px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                width: 100%;
                margin-bottom: 16px;
                transition: background 0.2s;
            }
            .connect-btn:hover {
                background: #1a8cd8;
            }
            .demo-btn {
                background: #f3f4f6;
                color: #374151;
                border: 1px solid #d1d5db;
                padding: 12px 32px;
                border-radius: 8px;
                font-size: 16px;
                cursor: pointer;
                width: 100%;
                transition: background 0.2s;
            }
            .demo-btn:hover {
                background: #e5e7eb;
            }
            .status {
                margin-top: 24px;
                padding: 12px;
                border-radius: 6px;
                display: none;
            }
            .status.success {
                background: #d1fae5;
                color: #065f46;
                border: 1px solid #a7f3d0;
            }
            .status.error {
                background: #fee2e2;
                color: #991b1b;
                border: 1px solid #fca5a5;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">Contextly.ai</div>
            <div class="subtitle">Connect your X account to earn CTXT tokens</div>
            
            <div class="x-logo">𝕏</div>
            
            <button class="connect-btn" onclick="connectX()">
                Connect X Account
            </button>
            
            <button class="demo-btn" onclick="mockConnect()">
                Demo Mode (No X Required)
            </button>
            
            <div id="status" class="status"></div>
        </div>
        
        <script>
            function showStatus(message, type) {
                const status = document.getElementById('status');
                status.textContent = message;
                status.className = 'status ' + type;
                status.style.display = 'block';
            }
            
            async function connectX() {
                showStatus('Connecting to X...', 'success');
                
                // For now, simulate successful connection
                setTimeout(() => {
                    showStatus('✅ Connected successfully! You can close this window.', 'success');
                    
                    // Notify parent window
                    if (window.opener) {
                        window.opener.postMessage({ type: 'x_auth_success', user: { username: 'demo_user' } }, '*');
                    }
                    
                    // Auto-close after 2 seconds
                    setTimeout(() => {
                        window.close();
                    }, 2000);
                }, 1000);
            }
            
            async function mockConnect() {
                showStatus('Setting up demo mode...', 'success');
                
                setTimeout(() => {
                    showStatus('✅ Demo mode activated! You can close this window.', 'success');
                    
                    // Notify parent window
                    if (window.opener) {
                        window.opener.postMessage({ 
                            type: 'x_auth_success', 
                            user: { username: 'demo_user', demo: true } 
                        }, '*');
                    }
                    
                    // Auto-close after 2 seconds
                    setTimeout(() => {
                        window.close();
                    }, 2000);
                }, 1000);
            }
        </script>
    </body>
    </html>
    """
    )


@app.post("/v1/auth/x/login")
async def initiate_x_auth(request: Request, body: Dict[str, Any]):
    """Initiate X (Twitter) OAuth authentication flow"""
    from .x_oauth import create_twitter_login_url

    wallet_address = body.get("wallet_address")
    result = await create_twitter_login_url(request, redis_client, wallet_address)

    # If it's a RedirectResponse (production), convert to JSON response
    if hasattr(result, "headers"):
        auth_url = result.headers.get("location")
        return {
            "auth_url": auth_url,
            "session_id": str(uuid.uuid4()),
            "state": "pending",
        }

    # Development mode returns dict directly
    return result


@app.get("/v1/auth/x/dev")
async def mock_x_auth_page(session_id: str):
    """Mock X authentication page for development"""
    return HTMLResponse(
        f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Connect X Account - Contextly</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
                background: #15202b;
                color: #ffffff;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }}
            .container {{
                background: #192734;
                padding: 2rem;
                border-radius: 16px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.5);
                text-align: center;
                max-width: 400px;
            }}
            h1 {{
                margin: 0 0 1rem 0;
                font-size: 24px;
            }}
            .logo {{
                font-size: 48px;
                margin-bottom: 1rem;
            }}
            input {{
                width: 100%;
                padding: 12px;
                margin: 8px 0;
                background: #253341;
                border: 1px solid #38444d;
                border-radius: 8px;
                color: #ffffff;
                font-size: 16px;
            }}
            button {{
                width: 100%;
                padding: 12px;
                margin-top: 1rem;
                background: #1d9bf0;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
            }}
            button:hover {{
                background: #1a8cd8;
            }}
            .info {{
                margin-top: 1rem;
                font-size: 12px;
                color: #8899a6;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">𝕏</div>
            <h1>Connect X Account</h1>
            <p>Enter your X username to connect with Contextly</p>
            <form id="authForm">
                <input type="text" id="username" placeholder="@username" required>
                <button type="submit">Connect Account</button>
            </form>
            <div class="info">
                This is a mock authentication page for development.
                In production, this would redirect to X's OAuth page.
            </div>
        </div>
        <script>
            document.getElementById('authForm').addEventListener('submit', async (e) => {{
                e.preventDefault();
                const username = document.getElementById('username').value.replace('@', '');
                
                // Call the callback endpoint
                const params = new URLSearchParams({{
                    oauth_token: '{session_id}',
                    oauth_verifier: 'mock_verifier_' + username,
                    username: username
                }});
                
                window.location.href = '/v1/auth/x/callback?dev_mode=true&' + params.toString();
            }});
        </script>
    </body>
    </html>
    """
    )


@app.get("/v1/auth/x/callback")
async def handle_x_auth_callback(
    request: Request,
    oauth_token: Optional[str] = None,
    session_id: Optional[str] = None,
    oauth_verifier: Optional[str] = None,
    username: Optional[str] = None,
    dev_mode: Optional[bool] = False,
    denied: Optional[str] = None,
):
    """Handle X OAuth callback"""
    from .x_oauth import handle_twitter_callback

    if denied:
        raise HTTPException(status_code=400, detail="User denied authorization")

    # Use session_id if oauth_token not provided (dev mode)
    token = oauth_token or session_id

    if dev_mode:
        # Handle development mode callback
        result = await handle_twitter_callback(request, redis_client)

        if result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])

        x_user_data = result["x_user_data"]

        # For dev mode, we need to get the wallet from the session or request
        # to store demo auth data properly
        wallet_address = None
        if token:
            session_data = await redis_client.get(f"x_auth_session:{token}")
            if session_data:
                session = json.loads(session_data)
                wallet_address = session.get("wallet_address")

        # Store demo X authentication data for status endpoint detection
        if wallet_address:
            demo_auth_data = {
                "username": x_user_data.get("x_username", "demo_user"),
                "x_id": x_user_data.get("x_id", "demo_x_id"),
                "linked_at": x_user_data.get(
                    "linked_at", datetime.now(timezone.utc).isoformat()
                ),
            }
            await redis_client.set(
                f"x_demo:{wallet_address}",
                json.dumps(demo_auth_data),
                ex=None,  # No expiry
            )
    else:
        # Get session data
        session_data = await redis_client.get(f"x_auth_session:{token}")
        if not session_data:
            raise HTTPException(status_code=400, detail="Invalid or expired session")

        session = json.loads(session_data)

        # For demo, use the provided username or generate one
        x_user_data = {
            "x_id": f"x_{uuid.uuid4().hex[:8]}",
            "x_username": username or f"user_{random.randint(1000, 9999)}",
            "x_name": "Demo User",
            "linked_at": datetime.now(timezone.utc).isoformat(),
        }

        # Store demo X authentication data for status endpoint detection
        if session.get("wallet_address"):
            # Store under x_demo key for demo authentication detection
            demo_auth_data = {
                "username": x_user_data["x_username"],
                "x_id": x_user_data["x_id"],
                "linked_at": x_user_data["linked_at"],
            }
            await redis_client.set(
                f"x_demo:{session['wallet_address']}",
                json.dumps(demo_auth_data),
                ex=None,  # No expiry
            )

            # Also store under x_link for compatibility with existing code
            await redis_client.set(
                f"x_link:{session['wallet_address']}",
                json.dumps(x_user_data),
                ex=None,  # No expiry
            )

    # Return success HTML page
    return HTMLResponse(
        f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Success - Contextly</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
                background: #15202b;
                color: #ffffff;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }}
            .container {{
                background: #192734;
                padding: 2rem;
                border-radius: 16px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.5);
                text-align: center;
                max-width: 400px;
            }}
            .success-icon {{
                font-size: 48px;
                margin-bottom: 1rem;
            }}
            h1 {{
                margin: 0 0 0.5rem 0;
                font-size: 24px;
            }}
            .username {{
                color: #1d9bf0;
                font-weight: 600;
            }}
            .message {{
                color: #8899a6;
                margin: 1rem 0;
            }}
            .close-message {{
                margin-top: 2rem;
                font-size: 14px;
                color: #8899a6;
            }}
        </style>
        <script>
            // Close window after delay
            setTimeout(() => {{
                window.close();
            }}, 3000);
            
            // Notify parent window if possible
            if (window.opener) {{
                window.opener.postMessage({{ type: 'x-auth-success', username: '{x_user_data["x_username"]}' }}, '*');
            }}
        </script>
    </head>
    <body>
        <div class="container">
            <div class="success-icon">✅</div>
            <h1>Connected Successfully!</h1>
            <p>X account <span class="username">@{x_user_data["x_username"]}</span> is now connected to Contextly</p>
            <p class="message">You can now earn rewards for your AI conversations</p>
            <p class="close-message">This window will close automatically...</p>
        </div>
    </body>
    </html>
    """
    )


@app.get("/v1/auth/x/test")
async def test_x_auth():
    """Test endpoint that returns Twitter auth configuration mode"""
    import os

    # Check if we're using dummy/missing Twitter credentials
    twitter_client_id = os.getenv("TWITTER_CLIENT_ID", "dummy_client_id")
    is_dev_mode = twitter_client_id in ["dummy_client_id", "", None]

    return {
        "status": "working",
        "message": "X auth endpoint is responding",
        "dev_mode": is_dev_mode,
        "auth_type": "development" if is_dev_mode else "production",
    }


@app.get("/v1/auth/x/status")
async def check_x_auth_status(
    wallet: Optional[str] = None, telegram_user_id: Optional[str] = None
):
    """Check X authentication status"""

    try:
        if not wallet and not telegram_user_id:
            raise HTTPException(
                status_code=400, detail="Either wallet or telegram_user_id required"
            )

        # Check for demo X authentication in Redis/memory
        if wallet:
            try:
                # Check if this wallet has been marked as X-authenticated in the demo
                x_demo_key = f"x_demo:{wallet}"
                x_data = await redis_client.get(x_demo_key)
                if x_data:
                    import json

                    x_info = json.loads(x_data)
                    return {
                        "authenticated": True,
                        "x_username": x_info.get("username", "demo_user"),
                        "x_id": x_info.get("x_id", "demo_x_id"),
                        "linked_at": x_info.get("linked_at"),
                    }
            except Exception as e:
                print(f"Redis check error: {e}")

        # Default: not authenticated
        return {"authenticated": False, "message": "X account not connected"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in X auth status: {e}")
        return {"authenticated": False, "error": str(e)}


@app.post("/v1/auth/verify")
async def verify_authentication(auth_data: Dict[str, Any]):
    """Verify user authentication via wallet or X account"""

    auth_type = auth_data.get("type")

    if auth_type == "wallet":
        # Verify wallet signature
        wallet = auth_data.get("wallet")
        signature = auth_data.get("signature")
        message = auth_data.get("message")

        if verify_wallet_signature(wallet, signature, message):
            user = await find_user_by_wallet(wallet)
            if user:
                return {
                    "authenticated": True,
                    "user_id": user["_id"],
                    "method": "wallet",
                    "wallet": wallet,
                }

    elif auth_type == "x":
        # Verify X account
        x_id = auth_data.get("x_id")
        telegram_user_id = auth_data.get("telegram_user_id")

        if telegram_user_id:
            x_link = await redis_client.get(f"x_link:{telegram_user_id}")
            if x_link:
                x_data = json.loads(x_link)
                if x_data.get("x_id") == x_id:
                    return {
                        "authenticated": True,
                        "user_id": x_id,
                        "method": "x",
                        "x_username": x_data.get("x_username"),
                    }

    return {"authenticated": False}


@app.get("/v1/sessions/history")
async def get_session_history(
    current_user: AuthenticatedUser = Depends(get_current_user_obj),
    limit: int = 50,
    offset: int = 0,
):
    """Get user's session history with earnings tracking"""

    # Get all sessions for this user
    sessions = []

    # Get activities for current session
    activity_pattern = f"activity:{current_user.session_id}:*"
    # Note: This is simplified - in production use proper Redis scanning

    # Get user's conversation sessions
    user_sessions = []
    if sessions_table is not None:
        try:
            # For sessions table, handle LanceDB Cloud limitations
            wallet = current_user.wallet
            x_id = current_user.x_id

            try:
                # TODO: Implement proper remote table querying
                # For now, return empty list for remote tables
                all_sessions = []
            except Exception as e:
                print(f"Error in sessions query: {e}")
                all_sessions = []

            # Filter by wallet or x_id
            if x_id:
                user_sessions = [
                    s
                    for s in all_sessions
                    if s.get("wallet") == wallet or s.get("x_id") == x_id
                ]
            else:
                user_sessions = [s for s in all_sessions if s.get("wallet") == wallet]

            # Sort by last_message
            user_sessions = sorted(
                user_sessions, key=lambda x: x.get("last_message", 0), reverse=True
            )
            user_sessions = user_sessions[offset : offset + limit]
        except Exception as e:
            print(f"❌ Error accessing sessions table: {e}")
            # Return empty sessions with error message
            return {
                "sessions": [],
                "total": 0,
                "page": offset // limit + 1,
                "total_pages": 0,
                "error": f"Error accessing sessions: {str(e)}",
            }
    else:
        # Return empty sessions if table not available
        return {
            "sessions": [],
            "total": 0,
            "page": offset // limit + 1,
            "total_pages": 0,
            "message": "Sessions table not available",
        }

    # Calculate earnings per session
    for session in user_sessions:
        session_id = session.get("session_id", session.get("_id"))

        # Get earnings for this session
        earnings_key = f"earnings:session:{session_id}"
        session_earnings = await redis_client.get(earnings_key) or "0"

        sessions.append(
            {
                "session_id": session_id,
                "platform": session.get("platform"),
                "message_count": session.get("messageCount", 0),
                "last_activity": session.get("lastMessage"),
                "total_tokens": session.get("totalTokens", 0),
                "ctxt_earned": float(session_earnings) * 0.001,  # Convert to CTXT
                "topics": session.get("allTopics", [])[:5],
            }
        )

    # Get total earnings
    total_earnings = (
        await redis_client.get(f"total_earnings:{current_user.user_id}")
        or current_user.total_earnings
    )

    return {
        "user_id": current_user.user_id,
        "auth_method": current_user.method,
        "total_ctxt_earned": float(total_earnings),
        "session_count": len(sessions),
        "sessions": sessions,
        "current_session": {
            "session_id": current_user.session_id,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "auth_method": current_user.method,
        },
    }


@app.get("/v1/earnings/details")
async def get_earnings_details(
    current_user: AuthenticatedUser = Depends(get_current_user_obj), days: int = 30
):
    """Get detailed earnings breakdown by day and activity type"""

    # Calculate date range
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    # Get daily earnings
    daily_earnings = {}
    earnings_by_type = {
        "messages": 0.0,
        "journeys": 0.0,
        "graphs": 0.0,
        "referrals": 0.0,
    }

    # Aggregate earnings data
    for i in range(days):
        date = (start_date + timedelta(days=i)).date()

        # Get message earnings
        message_key = f"earnings:{current_user.wallet or current_user.x_id}:{date}"
        message_earnings = await redis_client.get(message_key) or "0"

        # Get journey earnings
        journey_key = (
            f"journey_earnings:{current_user.wallet or current_user.x_id}:{date}"
        )
        journey_earnings = await redis_client.get(journey_key) or "0"

        daily_total = (float(message_earnings) * 0.001) + float(journey_earnings)

        if daily_total > 0:
            daily_earnings[str(date)] = {
                "messages": float(message_earnings) * 0.001,
                "journeys": float(journey_earnings),
                "total": daily_total,
            }

            earnings_by_type["messages"] += float(message_earnings) * 0.001
            earnings_by_type["journeys"] += float(journey_earnings)

    # Get user stats
    user = await find_user_by_id(current_user.user_id)
    
    # Handle case where user is not found
    if user is None:
        user = {}

    return {
        "user_id": current_user.user_id,
        "total_ctxt_earned": current_user.total_earnings,
        "period_days": days,
        "daily_earnings": daily_earnings,
        "earnings_by_type": earnings_by_type,
        "stats": {
            "total_conversations": user.get("conversationCount", 0) if user else 0,
            "total_journeys": user.get("journeyCount", 0) if user else 0,
            "graphs_created": user.get("graphNodesCreated", 0) if user else 0,
            "average_daily": sum(earnings_by_type.values()) / days if days > 0 else 0,
        },
    }


# Helper functions for enhanced features
def extract_topics(text: str) -> List[str]:
    """Extract topics from text using simple NLP"""
    # Simple keyword extraction - in production use more sophisticated methods
    import re
    from collections import Counter

    # Remove common words
    stop_words = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
        "as",
        "is",
        "was",
        "are",
        "were",
    }

    # Extract words
    words = re.findall(r"\b[a-z]+\b", text.lower())
    words = [w for w in words if len(w) > 3 and w not in stop_words]

    # Get most common words as topics
    word_counts = Counter(words)
    topics = [word for word, count in word_counts.most_common(5)]

    return topics


def format_messages_for_summary(messages: List[Message]) -> str:
    """Format messages for summarization"""
    formatted = []
    for msg in messages[:50]:  # Limit to prevent token overflow
        role = "Human" if msg.role == "user" else "Assistant"
        formatted.append(f"{role}: {msg.text[:500]}")
    return "\n\n".join(formatted)


def get_summary_system_prompt(mode: str) -> str:
    """Get appropriate system prompt for summary mode"""
    prompts = {
        "brief": "Create a concise summary focusing on the main topic and conclusion.",
        "detailed": "Create a comprehensive summary including key points, decisions made, and important details.",
        "progressive": "Create a structured summary with sections for context, main discussion, and outcomes.",
    }
    return prompts.get(mode, prompts["brief"])


async def progressive_summarization(messages: List[Message], max_length: int) -> str:
    """Progressive summarization for very long conversations"""
    # Chunk messages into groups
    chunk_size = 20
    chunks = [messages[i : i + chunk_size] for i in range(0, len(messages), chunk_size)]

    # Summarize each chunk
    chunk_summaries = []
    for chunk in chunks:
        text = format_messages_for_summary(chunk)
        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "Summarize this conversation segment concisely.",
                },
                {"role": "user", "content": text[:2000]},
            ],
            temperature=0.3,
            max_tokens=200,
        )
        chunk_summaries.append(response.choices[0].message.content)

    # Final summary of summaries
    final_response = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "Create a final summary from these conversation segments.",
            },
            {
                "role": "user",
                "content": f"Segment summaries:\n\n{chr(10).join(chunk_summaries)}",
            },
        ],
        temperature=0.3,
        max_tokens=max_length,
    )

    return final_response.choices[0].message.content


async def analyze_conversation_content(messages: List[Message]) -> Dict[str, List[str]]:
    """Analyze conversation for key points and action items"""
    conversation_text = format_messages_for_summary(messages)

    prompt = """Analyze this conversation and extract:
    1. Key points discussed (max 5)
    2. Action items or todos mentioned (if any)
    3. Main topics covered (max 5)
    
    Format as JSON with keys: key_points, action_items, topics"""

    response = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": f"{prompt}\n\nConversation:\n{conversation_text[:3000]}",
            }
        ],
        temperature=0.3,
        max_tokens=500,
        response_format={"type": "json_object"},
    )

    try:
        result = json.loads(response.choices[0].message.content)
        return {
            "key_points": result.get("key_points", [])[:5],
            "action_items": result.get("action_items", []),
            "topics": result.get("topics", [])[:5],
        }
    except:
        return {"key_points": [], "action_items": [], "topics": []}


async def create_smart_summary(
    messages: List[Message], from_platform: str, to_platform: str
) -> str:
    """Create smart summary using embeddings and GPT-4o"""
    # Get key messages using embeddings
    key_messages = []
    conversations_table = lance_db.open_table("conversations_v2")

    # Sample important messages
    for i in range(0, len(messages), max(1, len(messages) // 10)):
        msg = messages[i]
        if msg.role == "user":
            embedding = await get_embedding(msg.text[:500], "sentence")

            # Find similar context
            similar = (
                conversations_table.search(embedding, vector_column_name="text_vector")
                .limit(3)
                .to_list()
            )

            key_messages.append(
                {"text": msg.text[:300], "context": [m["text"][:100] for m in similar]}
            )

    system_prompt = f"""Create a context transfer summary from {from_platform} to {to_platform}.
    Focus on key topics, ongoing discussions, and necessary context.
    Format appropriately for {to_platform}."""

    user_prompt = "Key messages:\n\n" + "\n".join(
        [f"- {m['text']}" for m in key_messages[:10]]
    )

    response = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=500,
        temperature=0.3,
    )

    return response.choices[0].message.content


async def create_graph_enhanced_summary(
    messages: List[Message],
    key_entities: List[Entity],
    communities: List[Dict],
    from_platform: str,
    to_platform: str,
) -> str:
    """Create summary enhanced with knowledge graph context"""

    entity_context = "\n".join(
        [
            f"- {e['name']} ({e['type']}): {e.get('description', 'N/A')[:100]}"
            for e in key_entities[:10]
        ]
    )

    community_context = "\n".join(
        [f"- Topic cluster {c['id']}: {c['summary'][:100]}" for c in communities[:3]]
    )

    recent_messages = "\n".join([f"{m.role}: {m.text[:200]}" for m in messages[-5:]])

    prompt = f"""Create a context transfer from {from_platform} to {to_platform} using this knowledge graph context:

Key entities discussed:
{entity_context}

Main topic clusters:
{community_context}

Recent conversation:
{recent_messages}

Create a comprehensive summary that preserves the relationships and context."""

    response = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=700,
    )

    return response.choices[0].message.content


def format_full_conversation(messages: List[Message], to_platform: str) -> str:
    """Format conversation for target platform"""
    formatters = {
        "claude": lambda m: (
            f"Human: {m.text}" if m.role == "user" else f"Assistant: {m.text}"
        ),
        "chatgpt": lambda m: (
            f"User: {m.text}" if m.role == "user" else f"ChatGPT: {m.text}"
        ),
        "gemini": lambda m: (
            f"You: {m.text}" if m.role == "user" else f"Gemini: {m.text}"
        ),
    }

    formatter = formatters.get(to_platform, formatters["chatgpt"])
    return "\n\n".join(formatter(msg) for msg in messages)


async def process_message_for_graph(
    message_id: str, text: str, session_id: str, wallet: str
):
    """Background task to process message for knowledge graph"""
    try:
        # Extract entities and relationships
        entities, relationships = await extract_entities_relationships(text)

        # Update message with entities
        conversations_table = lance_db.open_table("conversations_v2")
        # Note: LanceDB doesn't support direct updates, so we log for now
        print(f"Extracted {len(entities)} entities from message {message_id}")

    except Exception as e:
        print(f"Error processing message for graph: {e}")


# ============================================================================
# AUTOMATION ENDPOINTS
# ============================================================================


class ScreenshotAnalysisRequest(BaseModel):
    screenshot: str  # Base64 encoded image
    url: str
    title: str
    timestamp: str
    wallet: str
    session_id: Optional[str] = None


class ArtifactRequest(BaseModel):
    html: str
    text: str
    metadata: Dict[str, Any]
    wallet: str
    session_id: Optional[str] = None


class LinksAnalysisRequest(BaseModel):
    links: List[Dict[str, str]]  # [{url, text, type}]
    page_url: str
    page_title: str
    wallet: str
    session_id: Optional[str] = None


class RecordingRequest(BaseModel):
    recording_data: Dict[str, Any]
    duration: int  # seconds
    url: str
    wallet: str
    session_id: Optional[str] = None


@app.post("/v1/automation/screenshot")
async def analyze_screenshot(
    request: ScreenshotAnalysisRequest,
    current_user: AuthenticatedUser = Depends(get_current_user_obj),
):
    """Analyze screenshot with GPT-4 Vision and calculate earnings"""
    try:
        # Decode base64 image
        image_data = base64.b64decode(
            request.screenshot.split(",")[1]
            if "," in request.screenshot
            else request.screenshot
        )

        # Send to GPT-4 Vision
        response = await openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Analyze this screenshot and extract: 1) Main content/purpose 2) UI elements 3) Text content 4) User interactions visible 5) Data quality score (1-10)",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64.b64encode(image_data).decode()}"
                            },
                        },
                    ],
                }
            ],
            max_tokens=500,
        )

        analysis = response.choices[0].message.content

        # Extract quality score from analysis
        quality_score = 7  # Default
        if "quality score:" in analysis.lower():
            try:
                quality_score = int(
                    re.search(r"quality score[:\s]+(\d+)", analysis, re.I).group(1)
                )
            except:
                pass

        # Calculate earnings (0.001-0.01 CTXT based on quality)
        earnings = 0.001 + (quality_score / 10) * 0.009

        # Generate embedding
        embedding = embedder.encode(f"{request.title} {request.url} {analysis}")

        # Store in LanceDB
        screenshot_data = {
            "id": str(uuid.uuid4()),
            "user_id": current_user.user_id,
            "wallet": request.wallet,
            "screenshot_hash": hashlib.sha256(image_data).hexdigest()[:16],
            "url": request.url,
            "title": request.title,
            "analysis": analysis,
            "quality_score": quality_score,
            "earnings": earnings,
            "timestamp": request.timestamp,
            "session_id": request.session_id or str(uuid.uuid4()),
            "vector": embedding.tolist(),
        }

        screenshots_table.add([screenshot_data])

        # Update user earnings
        await update_wallet_earnings_cache(request.wallet, earnings)

        return {
            "success": True,
            "analysis": analysis,
            "quality_score": quality_score,
            "earnings": earnings,
            "screenshot_id": screenshot_data["id"],
        }

    except Exception as e:
        print(f"Screenshot analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/automation/artifact")
async def store_artifact(
    request: ArtifactRequest,
    current_user: AuthenticatedUser = Depends(get_current_user_obj),
):
    """Store and analyze page artifact with GPT-4"""
    try:
        # Analyze with GPT-4
        prompt = f"""Analyze this web page artifact:
        URL: {request.metadata.get('url', 'Unknown')}
        Title: {request.metadata.get('title', 'Unknown')}
        
        Text content (first 2000 chars): {request.text[:2000]}
        
        Extract:
        1. Main topics and themes
        2. Key entities (people, organizations, concepts)
        3. Unique value score (1-10)
        4. Potential use cases for this data
        5. Quality assessment
        """

        response = await openai_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
        )

        analysis = response.choices[0].message.content

        # Extract value score
        value_score = 7  # Default
        if "value score:" in analysis.lower():
            try:
                value_score = int(
                    re.search(r"value score[:\s]+(\d+)", analysis, re.I).group(1)
                )
            except:
                pass

        # Calculate earnings (0.005-0.05 CTXT based on uniqueness)
        earnings = 0.005 + (value_score / 10) * 0.045

        # Generate embedding
        embedding = embedder.encode(
            f"{request.metadata.get('title', '')} {request.text[:1000]}"
        )

        # Store in LanceDB
        artifact_data = {
            "id": str(uuid.uuid4()),
            "user_id": current_user.user_id,
            "wallet": request.wallet,
            "url": request.metadata.get("url", ""),
            "title": request.metadata.get("title", ""),
            "html_hash": hashlib.sha256(request.html.encode()).hexdigest()[:16],
            "text_preview": request.text[:500],
            "metadata": json.dumps(request.metadata),
            "analysis": analysis,
            "value_score": value_score,
            "earnings": earnings,
            "timestamp": request.metadata.get(
                "timestamp", datetime.now(timezone.utc).isoformat()
            ),
            "session_id": request.session_id or str(uuid.uuid4()),
            "vector": embedding.tolist(),
        }

        artifacts_table.add([artifact_data])

        # Extract entities for knowledge graph
        # TODO: Implement entity extraction and knowledge graph update
        # entities = extract_entities_from_text(request.text[:2000])
        # if entities:
        #     await update_knowledge_graph(artifact_data["id"], entities, "artifact")

        # Update earnings
        await update_wallet_earnings_cache(request.wallet, earnings)

        return {
            "success": True,
            "analysis": analysis,
            "value_score": value_score,
            "earnings": earnings,
            "artifact_id": artifact_data["id"],
            "entities_extracted": len(entities),
        }

    except Exception as e:
        print(f"Artifact storage error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/automation/links")
async def analyze_links(
    request: LinksAnalysisRequest,
    current_user: AuthenticatedUser = Depends(get_current_user_obj),
):
    """Analyze extracted links with GPT-4"""
    try:
        # Prepare links summary for analysis
        links_summary = "\n".join(
            [
                f"- {link['text']}: {link['url']} ({link['type']})"
                for link in request.links[:50]  # Limit to first 50
            ]
        )

        prompt = f"""Analyze these extracted links from {request.page_title}:
        
        {links_summary}
        
        Provide:
        1. Link categories and distribution
        2. External vs internal ratio
        3. Valuable resources identified
        4. Link graph insights
        5. Data value score (1-10)
        """

        response = await openai_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
        )

        analysis = response.choices[0].message.content

        # Extract value score
        value_score = 6  # Default
        if "value score:" in analysis.lower():
            try:
                value_score = int(
                    re.search(r"value score[:\s]+(\d+)", analysis, re.I).group(1)
                )
            except:
                pass

        # Calculate earnings (0.002-0.02 CTXT based on value)
        earnings = 0.002 + (value_score / 10) * 0.018

        # Create link graph
        link_graph = nx.DiGraph()
        for link in request.links:
            link_graph.add_edge(
                request.page_url, link["url"], text=link["text"], type=link["type"]
            )

        # Store in LanceDB
        links_data = {
            "id": str(uuid.uuid4()),
            "user_id": current_user.user_id,
            "wallet": request.wallet,
            "page_url": request.page_url,
            "page_title": request.page_title,
            "total_links": len(request.links),
            "external_links": len(
                [l for l in request.links if l["type"] == "external"]
            ),
            "internal_links": len(
                [l for l in request.links if l["type"] == "internal"]
            ),
            "links_data": json.dumps(request.links[:100]),  # Store first 100
            "analysis": analysis,
            "value_score": value_score,
            "earnings": earnings,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": request.session_id or str(uuid.uuid4()),
        }

        # Note: Add a links_analysis table to LanceDB schema
        # For now, store in conversations table
        conversations_table = lance_db.open_table("conversations_v2")
        conversations_table.add(
            [
                {
                    **links_data,
                    "platform": "link_analysis",
                    "role": "system",
                    "content": f"Link analysis for {request.page_title}",
                    "vector": embedder.encode(analysis).tolist(),
                }
            ]
        )

        # Update earnings
        await update_wallet_earnings_cache(request.wallet, earnings)

        return {
            "success": True,
            "analysis": analysis,
            "value_score": value_score,
            "earnings": earnings,
            "link_stats": {
                "total": len(request.links),
                "external": links_data["external_links"],
                "internal": links_data["internal_links"],
            },
        }

    except Exception as e:
        print(f"Links analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/automation/recording")
async def process_recording(
    request: RecordingRequest,
    current_user: AuthenticatedUser = Depends(get_current_user_obj),
):
    """Process page recording data"""
    try:
        # For now, we'll analyze the recording metadata
        # In production, you'd process actual video frames

        prompt = f"""Analyze this web journey recording:
        URL: {request.url}
        Duration: {request.duration} seconds
        Recording data: {json.dumps(request.recording_data, indent=2)}
        
        Assess:
        1. Journey complexity
        2. User interaction patterns
        3. Valuable insights captured
        4. Journey value score (1-10)
        """

        response = await openai_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
        )

        analysis = response.choices[0].message.content

        # Extract value score
        value_score = 7  # Default
        if "value score:" in analysis.lower():
            try:
                value_score = int(
                    re.search(r"value score[:\s]+(\d+)", analysis, re.I).group(1)
                )
            except:
                pass

        # Calculate earnings (0.01-0.1 CTXT based on journey complexity)
        complexity_factor = min(request.duration / 60, 10) / 10  # Cap at 10 minutes
        earnings = 0.01 + (value_score / 10) * 0.09 * complexity_factor

        # Store recording data
        recording_data = {
            "id": str(uuid.uuid4()),
            "user_id": current_user.user_id,
            "wallet": request.wallet,
            "url": request.url,
            "duration": request.duration,
            "recording_metadata": json.dumps(request.recording_data),
            "analysis": analysis,
            "value_score": value_score,
            "earnings": earnings,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": request.session_id or str(uuid.uuid4()),
        }

        # Store in conversations table for now
        conversations_table = lance_db.open_table("conversations_v2")
        conversations_table.add(
            [
                {
                    **recording_data,
                    "platform": "recording",
                    "role": "system",
                    "content": f"Recording analysis for {request.url}",
                    "vector": embedder.encode(analysis).tolist(),
                }
            ]
        )

        # Update earnings
        await update_wallet_earnings_cache(request.wallet, earnings)

        return {
            "success": True,
            "analysis": analysis,
            "value_score": value_score,
            "earnings": earnings,
            "duration": request.duration,
            "recording_id": recording_data["id"],
        }

    except Exception as e:
        print(f"Recording processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def update_wallet_earnings_cache(wallet: str, amount: float):
    """Update user earnings in cache with money sign emojis"""
    try:
        # Update in cache
        cache_key = f"earnings:{wallet}"
        current = await redis_client.get(cache_key)
        new_total = float(current or 0) + amount
        await redis_client.set(cache_key, str(new_total), ex=3600)

        # Log earnings event with money signs
        money_signs = "💰" * min(
            int(amount * 1000), 10
        )  # More money signs for higher earnings
        print(
            f"{money_signs} Updated earnings for {wallet}: +{amount} CTXT (total: {new_total}) {money_signs}"
        )

    except Exception as e:
        print(f"Error updating earnings: {e}")


# Auto-Contextly Mode Management
class AutoModeRequest(BaseModel):
    enabled: bool
    wallet: str
    session_id: Optional[str] = None


@app.post("/v1/auto-mode/toggle")
async def toggle_auto_mode(
    auto_data: AutoModeRequest,
    current_user: AuthenticatedUser = Depends(get_current_user_obj),
):
    """Toggle auto-contextly mode for continuous data capture"""
    try:
        wallet = auto_data.wallet
        enabled = auto_data.enabled

        # Store auto mode state
        cache_key = f"auto_mode:{wallet}"
        await redis_client.set(cache_key, str(enabled), ex=86400)  # 24 hours

        if enabled:
            # Initialize auto mode session
            session_id = auto_data.session_id or str(uuid.uuid4())
            session_key = f"auto_session:{wallet}"
            await redis_client.set(session_key, session_id, ex=86400)

            # Show money signs when enabling
            money_celebration = "💰💸💎✨🤑" * 3
            print(
                f"{money_celebration} Auto-Contextly Mode ENABLED for {wallet}! Start earning CTXT! {money_celebration}"
            )

            return JSONResponse(
                content={
                    "status": "success",
                    "message": "💰 Auto-Contextly mode enabled! You'll now earn CTXT for all captured data 💰",
                    "auto_mode_enabled": True,
                    "session_id": session_id,
                    "earnings_display": "💰💸 EARNING CTXT 💸💰",
                }
            )
        else:
            # Disable auto mode
            await redis_client.delete(f"auto_session:{wallet}")
            print(f"Auto-Contextly Mode DISABLED for {wallet}")

            return JSONResponse(
                content={
                    "status": "success",
                    "message": "Auto-Contextly mode disabled",
                    "auto_mode_enabled": False,
                    "earnings_display": None,
                }
            )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to toggle auto mode: {str(e)}"
        )


@app.get("/v1/auto-mode/status/{wallet}")
async def get_auto_mode_status(
    wallet: str, current_user: AuthenticatedUser = Depends(get_current_user_obj)
):
    """Get current auto mode status and earnings display"""
    try:
        cache_key = f"auto_mode:{wallet}"
        enabled = await redis_client.get(cache_key)

        # Get current earnings
        earnings_key = f"earnings:{wallet}"
        current_earnings = float(await redis_client.get(earnings_key) or 0)

        if enabled == "True":
            # Show animated money signs based on earnings level
            if current_earnings > 1.0:
                display = "💰💸💎 EARNING BIG 💎💸💰"
            elif current_earnings > 0.1:
                display = "💰💸 EARNING CTXT 💸💰"
            else:
                display = "💰 EARNING 💰"

            return {
                "auto_mode_enabled": True,
                "earnings_display": display,
                "current_earnings": current_earnings,
                "session_id": await redis_client.get(f"auto_session:{wallet}"),
            }
        else:
            return {
                "auto_mode_enabled": False,
                "earnings_display": None,
                "current_earnings": current_earnings,
                "session_id": None,
            }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get auto mode status: {str(e)}"
        )


@app.post("/v1/auto-mode/capture")
async def auto_capture_data(
    request: Request, current_user: AuthenticatedUser = Depends(get_current_user_obj)
):
    """Endpoint for auto-contextly continuous data capture"""
    try:
        data = await request.json()
        wallet = data.get("wallet")
        capture_type = data.get("type")  # "screenshot", "text", "url", "interaction"

        # Check if auto mode is enabled
        cache_key = f"auto_mode:{wallet}"
        enabled = await redis_client.get(cache_key)

        if enabled != "True":
            return JSONResponse(
                content={"status": "error", "message": "Auto mode not enabled"}
            )

        # Calculate earnings based on capture type
        earnings_map = {
            "screenshot": 0.002,
            "text": 0.001,
            "url": 0.001,
            "interaction": 0.005,
        }

        earnings = earnings_map.get(capture_type, 0.001)

        # Store capture data in LanceDB
        session_id = await redis_client.get(f"auto_session:{wallet}")

        # Add to appropriate table based on type
        if capture_type == "screenshot" and "screenshot" in data:
            # Use existing screenshot endpoint logic
            pass

        # Update earnings with money signs
        await update_wallet_earnings_cache(wallet, earnings)

        money_signs = "💰" * min(int(earnings * 1000), 5)

        return JSONResponse(
            content={
                "status": "success",
                "earnings": earnings,
                "display_message": f"{money_signs} +{earnings} CTXT earned! {money_signs}",
                "capture_type": capture_type,
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auto capture failed: {str(e)}")


# Initialize tables for automation features
@app.on_event("startup")
async def startup():
    print(f"🚀 Contextly.ai Enhanced API running on port {CONFIG['PORT']}")

    # Initialize LanceDB tables
    await init_lancedb()

    print("✅ All services initialized")


if __name__ == "__main__":
    print(
        """
    💬 Contextly.ai Enhanced Backend API v3.0
    ==========================================
    
    New Features:
    ✅ Advanced LanceDB Integration
    ✅ GraphRAG Knowledge Graphs
    ✅ Intelligent Summarization
    ✅ Auto Title Generation
    ✅ Enhanced Conversation Listing
    ✅ Multimodal Support
    ✅ Cross-platform Context Transfer
    ✅ Insights Generation
    
    Stack:
    - Vector DB: LanceDB Cloud (All Data Storage)
    - Graph: NetworkX + GraphRAG
    - Cache: Upstash Redis
    - LLM: OpenAI GPT-4o
    - Embeddings: OpenAI + Sentence Transformers
    
    Enhanced Endpoints (All require authentication):
    
    Authentication:
    POST /v1/wallet/register         - Register wallet
    POST /v1/auth/x/login           - Initiate X OAuth flow
    GET  /v1/auth/x/callback        - Handle X OAuth callback
    GET  /v1/auth/x/status          - Check X auth status
    POST /v1/auth/verify            - Verify authentication
    
    Conversations (Auth Required):
    POST /v1/conversations/message   - Store message with graph processing
    POST /v1/conversations/summarize - Generate intelligent summaries
    POST /v1/conversations/title     - Auto-generate titles
    POST /v1/conversations/list      - List with summaries for dropdown
    POST /v1/conversations/search    - Vector search
    
    Knowledge Graph (Auth Required):
    POST /v1/graph/build            - Build knowledge graph
    POST /v1/graph/query            - Query graph with NLP
    POST /v1/graph/visualize        - Generate graph visualization data
    
    Analytics (Auth Required):
    POST /v1/transfer/prepare       - Graph-enhanced transfer
    POST /v1/journeys/analyze       - Enhanced journey analysis
    POST /v1/journeys/sankey        - Generate Sankey diagram data
    POST /v1/insights/generate      - Generate user insights
    
    User Data (Auth Required):
    GET  /v1/stats/{wallet}         - Enhanced statistics
    GET  /v1/sessions/history       - Session history with earnings
    GET  /v1/earnings/details       - Detailed earnings breakdown
    
    Automation Features (Auth Required):
    POST /v1/automation/screenshot   - Analyze screenshot with GPT-4 Vision
    POST /v1/automation/artifact     - Store and analyze page artifact
    POST /v1/automation/links        - Analyze extracted links
    POST /v1/automation/recording    - Process page recording data
    
    Authentication Headers:
    - X-Wallet-Address: Your wallet address
    - X-Wallet-Signature: Signature of auth message
    - X-Auth-Token: X authentication token
    - X-Session-ID: Session ID from previous auth
    - Authorization: Bearer <JWT token>
    
    Docs: http://localhost:{CONFIG['PORT']}/docs
    """
    )

    uvicorn.run(app, host="0.0.0.0", port=CONFIG["PORT"])
