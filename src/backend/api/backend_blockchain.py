import os
import json
import asyncio
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from collections import deque
import logging
import hashlib

from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_account import Account
from eth_account.messages import encode_defunct
import lancedb
import pyarrow as pa
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

class BlockchainService:
    """Handles all blockchain interactions with LanceDB caching"""
    
    def __init__(self, config: dict):
        self.config = config
        self.w3 = None
        self.account = None
        self.contracts = {}
        self.lance_db = None
        self.db = None
        
        # Batch processing
        self.pending_contributions = deque()
        self.batch_lock = asyncio.Lock()
        self.batch_task = None
        
        # Action types enum
        self.ACTION_TYPES = {
            'MESSAGE': 0,
            'JOURNEY': 1,
            'REFERRAL': 2,
            'DAILY_CHECKIN': 3,
            'STREAK_BONUS': 4,
            'ACHIEVEMENT': 5,
            'COMMUNITY_TASK': 6,
            'QUALITY_BONUS': 7,
            'VIRAL_CONTENT': 8,
            'CUSTOM': 9
        }
        
        asyncio.create_task(self._initialize())
    
    async def _initialize(self):
        """Initialize all connections and contracts"""
        # Initialize Web3
        self.w3 = Web3(Web3.HTTPProvider(self.config['rpc_url']))
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        
        # Load backend account
        self.account = Account.from_key(self.config['backend_private_key'])
        self.w3.eth.default_account = self.account.address
        
        # Initialize LanceDB
        self.lance_db = lancedb.connect(
            uri=self.config['lancedb_uri'],
            api_key=self.config['lancedb_api_key'],
            region="us-east-1"
        )
        
        # Initialize cache tables in LanceDB
        await self._init_cache_tables()
        
        # Initialize MongoDB
        mongo_client = AsyncIOMotorClient(self.config['mongodb_url'])
        self.db = mongo_client.contextly
        
        # Load contracts
        await self._load_contracts()
        
        # Start batch processor
        self.batch_task = asyncio.create_task(self._batch_processor())
        
        logger.info(f"✅ Blockchain service initialized. Backend wallet: {self.account.address}")
    
    async def _init_cache_tables(self):
        """Initialize LanceDB tables for caching"""
        # Transaction cache table
        if "transaction_cache" not in self.lance_db.table_names():
            schema = pa.schema([
                ('tx_hash', pa.string()),
                ('user_wallet', pa.string()),
                ('action_type', pa.string()),
                ('amount', pa.string()),
                ('status', pa.string()),
                ('block_number', pa.int64()),
                ('timestamp', pa.timestamp('us')),
                ('metadata', pa.string())  # JSON string
            ])
            self.lance_db.create_table("transaction_cache", schema=schema)
        
        # User stats cache table
        if "user_stats_cache" not in self.lance_db.table_names():
            schema = pa.schema([
                ('wallet', pa.string()),
                ('total_earned', pa.string()),
                ('total_words', pa.int64()),
                ('total_characters', pa.int64()),
                ('quality_score', pa.float64()),
                ('journey_count', pa.int64()),
                ('referral_count', pa.int64()),
                ('current_streak', pa.int32()),
                ('last_updated', pa.timestamp('us')),
                ('cache_expiry', pa.timestamp('us'))
            ])
            self.lance_db.create_table("user_stats_cache", schema=schema)
        
        # Pending actions queue table
        if "pending_actions" not in self.lance_db.table_names():
            schema = pa.schema([
                ('action_id', pa.string()),
                ('user_wallet', pa.string()),
                ('action_type', pa.string()),
                ('base_amount', pa.string()),
                ('quality_score', pa.float64()),
                ('extra_data', pa.string()),  # JSON
                ('queued_at', pa.timestamp('us')),
                ('status', pa.string()),
                ('retry_count', pa.int32())
            ])
            self.lance_db.create_table("pending_actions", schema=schema)
    
    async def queue_action(self, action: Dict) -> Dict:
        """Queue any action (message, journey, referral, etc.) for processing"""
        # Validate wallet
        if not Web3.is_address(action['wallet']):
            raise ValueError("Invalid wallet address")
        
        # Generate action ID
        action_id = self._generate_action_id(action)
        
        # Check if already processed
        if await self._is_action_processed(action_id):
            return {
                'status': 'already_processed',
                'message': 'This action has already been processed'
            }
        
        # Add to pending actions in LanceDB
        pending_table = self.lance_db.open_table("pending_actions")
        pending_table.add([{
            'action_id': action_id,
            'user_wallet': action['wallet'],
            'action_type': action.get('action_type', 'MESSAGE'),
            'base_amount': str(action.get('base_amount', 0)),
            'quality_score': action.get('quality_score', 0.5),
            'extra_data': json.dumps(action.get('extra_data', {})),
            'queued_at': datetime.now(timezone.utc),
            'status': 'pending',
            'retry_count': 0
        }])
        
        # Also add to memory queue for immediate processing
        async with self.batch_lock:
            self.pending_contributions.append({
                **action,
                'action_id': action_id,
                'queued_at': datetime.now(timezone.utc)
            })
        
        # Calculate estimated earnings
        estimated = await self._estimate_earnings(action)
        
        return {
            'status': 'queued',
            'action_id': action_id,
            'estimated_earnings': estimated,
            'position_in_queue': len(self.pending_contributions)
        }
    
    async def process_journey(self, journey_data: Dict) -> Dict:
        """Process a user journey with screenshots"""
        journey_id = f"journey_{journey_data['session_id']}_{int(datetime.now().timestamp())}"
        
        # Queue journey action
        action = {
            'wallet': journey_data['wallet'],
            'action_type': 'JOURNEY',
            'base_amount': 50,  # Base 50 CTXT for journeys
            'quality_score': journey_data.get('quality_score', 0.7),
            'extra_data': {
                'journey_id': journey_id,
                'screenshot_count': len(journey_data.get('screenshots', [])),
                'category': journey_data.get('category', 'browsing'),
                'duration': journey_data.get('duration', 0),
                'patterns': journey_data.get('patterns', [])
            }
        }
        
        result = await self.queue_action(action)
        
        # Store journey details in MongoDB for analysis
        await self.db.journeys.insert_one({
            'journey_id': journey_id,
            'wallet': journey_data['wallet'],
            'session_id': journey_data['session_id'],
            'screenshots': journey_data.get('screenshots', []),
            'analysis': journey_data.get('analysis', {}),
            'created_at': datetime.now(timezone.utc),
            'blockchain_status': 'pending'
        })
        
        return {
            **result,
            'journey_id': journey_id
        }
    
    async def record_referral(self, referrer_wallet: str, referee_wallet: str, referral_code: str) -> Dict:
        """Record a referral relationship"""
        # Validate wallets
        referrer = Web3.to_checksum_address(referrer_wallet)
        referee = Web3.to_checksum_address(referee_wallet)
        
        # Check if already referred
        existing = await self.db.users.find_one({'wallet': referee})
        if existing and existing.get('referred_by'):
            return {
                'status': 'error',
                'message': 'User already has a referrer'
            }
        
        # Build transaction
        tx = self.contracts['registry'].functions.recordReferral(
            referrer,
            referee,
            referral_code
        ).build_transaction({
            'from': self.account.address,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
            'gas': 200000,
            'gasPrice': await self._get_optimal_gas_price(),
            'chainId': self.config['chain_id']
        })
        
        # Sign and send
        signed_tx = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        logger.info(f"📤 Referral transaction sent: {tx_hash.hex()}")
        
        # Update database
        await self.db.users.update_one(
            {'wallet': referee},
            {'$set': {'referred_by': referrer, 'referral_code': referral_code}}
        )
        
        # Queue referral bonus for referrer
        await self.queue_action({
            'wallet': referrer,
            'action_type': 'REFERRAL',
            'base_amount': 100,  # 100 CTXT referral bonus
            'quality_score': 1.0,
            'extra_data': {
                'referee': referee,
                'referral_code': referral_code
            }
        })
        
        return {
            'status': 'success',
            'tx_hash': tx_hash.hex(),
            'message': 'Referral recorded successfully'
        }
    
    async def process_daily_checkin(self, wallet: str) -> Dict:
        """Process daily check-in"""
        # Check last check-in from cache
        cache_key = f"checkin_{wallet}_{datetime.now().date()}"
        
        # Use LanceDB to check if already checked in today
        cache_table = self.lance_db.open_table("user_stats_cache")
        today_checkin = cache_table.search().where(
            f"wallet = '{wallet}' AND cache_expiry > '{datetime.now(timezone.utc)}'"
        ).limit(1).to_list()
        
        if today_checkin:
            return {
                'status': 'already_checked_in',
                'message': 'Already checked in today'
            }
        
        # Queue check-in action
        return await self.queue_action({
            'wallet': wallet,
            'action_type': 'DAILY_CHECKIN',
            'base_amount': 5,  # 5 CTXT daily bonus
            'quality_score': 1.0,
            'extra_data': {
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        })
    
    async def grant_achievement(self, wallet: str, achievement_id: str) -> Dict:
        """Grant an achievement to a user"""
        # Build transaction
        tx = self.contracts['registry'].functions.grantAchievement(
            Web3.to_checksum_address(wallet),
            achievement_id
        ).build_transaction({
            'from': self.account.address,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
            'gas': 150000,
            'gasPrice': await self._get_optimal_gas_price(),
            'chainId': self.config['chain_id']
        })
        
        # Sign and send
        signed_tx = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        logger.info(f"🏆 Achievement granted: {achievement_id} to {wallet}")
        
        return {
            'status': 'success',
            'tx_hash': tx_hash.hex(),
            'achievement_id': achievement_id
        }
    
    async def _batch_processor(self):
        """Process batches every 5 minutes or when full"""
        while True:
            try:
                # Check pending actions in LanceDB
                pending_table = self.lance_db.open_table("pending_actions")
                pending = pending_table.search().where(
                    f"status = 'pending' AND retry_count < 3"
                ).limit(50).to_list()
                
                if pending:
                    await self._process_batch_from_lance(pending)
                
                await asyncio.sleep(300)  # 5 minutes
                
            except Exception as e:
                logger.error(f"Batch processor error: {e}")
                await asyncio.sleep(60)
    
    async def _process_batch_from_lance(self, pending_actions: List[Dict]):
        """Process a batch of actions from LanceDB"""
        # Group by action type for efficient processing
        grouped = {}
        for action in pending_actions:
            action_type = action['action_type']
            if action_type not in grouped:
                grouped[action_type] = []
            grouped[action_type].append(action)
        
        # Process each action type
        for action_type, actions in grouped.items():
            if action_type == 'MESSAGE':
                await self._process_message_batch(actions)
            elif action_type == 'JOURNEY':
                await self._process_journey_batch(actions)
            else:
                await self._process_generic_action_batch(actions)
    
    async def _process_generic_action_batch(self, actions: List[Dict]):
        """Process a batch of generic actions"""
        try:
            # Prepare transaction data
            users = []
            action_types = []
            base_amounts = []
            quality_scores = []
            action_ids = []
            extra_data_list = []
            
            for action in actions:
                users.append(Web3.to_checksum_address(action['user_wallet']))
                action_types.append(self.ACTION_TYPES[action['action_type']])
                base_amounts.append(Web3.to_wei(float(action['base_amount']), 'ether'))
                quality_scores.append(int(action['quality_score'] * 10000))
                action_ids.append(action['action_id'])
                extra_data_list.append(action['extra_data'].encode())
            
            # Build batch transaction
            nonce = self.w3.eth.get_transaction_count(self.account.address)
            
            # Process each action individually for now
            for i, user in enumerate(users):
                tx = self.contracts['registry'].functions.processAction(
                    user,
                    action_types[i],
                    base_amounts[i],
                    quality_scores[i],
                    action_ids[i],
                    extra_data_list[i]
                ).build_transaction({
                    'from': self.account.address,
                    'nonce': nonce + i,
                    'gas': 300000,
                    'gasPrice': await self._get_optimal_gas_price(),
                    'chainId': self.config['chain_id']
                })
                
                signed_tx = self.account.sign_transaction(tx)
                tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                
                logger.info(f"📤 Action transaction sent: {tx_hash.hex()}")
                
                # Update status in LanceDB
                await self._update_action_status(
                    action_ids[i],
                    'processing',
                    tx_hash.hex()
                )
            
        except Exception as e:
            logger.error(f"Generic action batch error: {e}")
            # Update retry count
            for action in actions:
                await self._increment_retry_count(action['action_id'])
    
    async def _update_action_status(self, action_id: str, status: str, tx_hash: str = None):
        """Update action status in LanceDB"""
        # For now, we'll store in MongoDB as LanceDB doesn't support updates well
        # In production, you might want to use a proper queue system
        await self.db.action_status.update_one(
            {'action_id': action_id},
            {
                '$set': {
                    'status': status,
                    'tx_hash': tx_hash,
                    'updated_at': datetime.now(timezone.utc)
                }
            },
            upsert=True
        )
    
    async def get_user_stats(self, wallet: str) -> Dict:
        """Get user stats with LanceDB caching"""
        wallet = Web3.to_checksum_address(wallet)
        
        # Check cache first
        cache_table = self.lance_db.open_table("user_stats_cache")
        cached = cache_table.search().where(
            f"wallet = '{wallet}' AND cache_expiry > '{datetime.now(timezone.utc)}'"
        ).limit(1).to_list()
        
        if cached:
            return json.loads(cached[0]['metadata'])
        
        # Get from blockchain
        stats = await self._get_onchain_stats(wallet)
        
        # Cache in LanceDB
        cache_table.add([{
            'wallet': wallet,
            'total_earned': stats['total_earned'],
            'total_words': stats['total_words'],
            'total_characters': stats['total_characters'],
            'quality_score': stats['quality_score'],
            'journey_count': stats['journey_count'],
            'referral_count': stats['referral_count'],
            'current_streak': stats['current_streak'],
            'last_updated': datetime.now(timezone.utc),
            'cache_expiry': datetime.now(timezone.utc) + timedelta(minutes=5)
        }])
        
        return stats
    
    async def _get_onchain_stats(self, wallet: str) -> Dict:
        """Get stats directly from blockchain"""
        # Get token stats
        token_stats = await self._call_contract_method(
            self.contracts['token'].functions.userStats(wallet)
        )
        
        # Get game stats
        game_stats = await self._call_contract_method(
            self.contracts['registry'].functions.userGameStats(wallet)
        )
        
        # Get balance
        balance = await self._call_contract_method(
            self.contracts['token'].functions.balanceOf(wallet)
        )
        
        # Get staking info
        staking_boost = await self._call_contract_method(
            self.contracts['staking'].functions.getUserEarningsBoost(wallet)
        )
        
        return {
            'wallet': wallet,
            'balance': str(Web3.from_wei(balance, 'ether')),
            'total_earned': str(Web3.from_wei(token_stats[0], 'ether')),
            'total_words': token_stats[1],
            'total_characters': token_stats[2],
            'quality_score': token_stats[3] / 100,
            'last_active': datetime.fromtimestamp(token_stats[4], tz=timezone.utc).isoformat(),
            'contribution_days': token_stats[5],
            'current_streak': token_stats[6],
            'longest_streak': token_stats[7],
            'journey_count': game_stats[1],  # journeysCompleted
            'referral_count': game_stats[2],  # referralCount
            'referral_earnings': str(Web3.from_wei(game_stats[3], 'ether')),  # referralEarnings
            'staking_boost': staking_boost / 10000
        }
    
    def _generate_action_id(self, action: Dict) -> str:
        """Generate unique action ID"""
        data = f"{action['wallet']}_{action.get('action_type')}_{datetime.now().timestamp()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    async def _is_action_processed(self, action_id: str) -> bool:
        """Check if action is already processed"""
        # Check in MongoDB for now
        existing = await self.db.action_status.find_one({
            'action_id': action_id,
            'status': {'$in': ['confirmed', 'processing']}
        })
        return existing is not None
    
    async def _estimate_earnings(self, action: Dict) -> str:
        """Estimate earnings for any action type"""
        action_type = action.get('action_type', 'MESSAGE')
        base_amount = action.get('base_amount', 1)
        quality_score = action.get('quality_score', 0.5)
        
        # Get action reward info from contract
        try:
            action_reward = await self._call_contract_method(
                self.contracts['registry'].functions.actionRewards(
                    self.ACTION_TYPES[action_type]
                )
            )
            
            base_reward = Web3.from_wei(action_reward[0], 'ether')
            multiplier = action_reward[1] / 10000
            
            # Calculate estimate
            estimated = base_reward * multiplier * (1 + quality_score)
            
            return f"{estimated:.4f}"
        except:
            # Fallback estimate
            return f"{base_amount * (1 + quality_score):.4f}"