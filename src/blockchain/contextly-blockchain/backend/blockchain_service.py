#!/usr/bin/env python3
"""
Contextly Blockchain Service
Handles all blockchain interactions for the Contextly ecosystem
"""

import os
import json
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from decimal import Decimal
from web3 import Web3
from web3.contract import Contract
from web3.middleware import geth_poa_middleware
from eth_account import Account
from eth_account.signers.local import LocalAccount
import aiohttp
from dotenv import load_dotenv

load_dotenv()


class BlockchainService:
    """Main blockchain service for Contextly"""
    
    def __init__(self):
        # Configuration
        self.rpc_url = os.getenv("BASE_RPC_URL", "https://mainnet.base.org")
        self.chain_id = int(os.getenv("CHAIN_ID", "8453"))  # Base mainnet
        self.private_key = os.getenv("PRIVATE_KEY")
        
        # Contract addresses (to be set after deployment)
        self.token_address = os.getenv("CTXT_TOKEN_ADDRESS")
        self.staking_address = os.getenv("STAKING_ADDRESS")
        self.registry_address = os.getenv("REGISTRY_ADDRESS")
        
        # Web3 setup
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        
        # Add POA middleware for Base
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        
        # Account setup
        if self.private_key:
            self.account: LocalAccount = Account.from_key(self.private_key)
            self.w3.eth.default_account = self.account.address
        
        # Contract instances
        self.token_contract: Optional[Contract] = None
        self.staking_contract: Optional[Contract] = None
        self.registry_contract: Optional[Contract] = None
        
        # Load ABIs
        self.token_abi = self._load_abi("ContextlyToken.json")
        self.staking_abi = self._load_abi("ContextlyStaking.json")
        self.registry_abi = self._load_abi("ContextlyRegistry.json")
        
        # Initialize contracts if addresses are available
        if self.token_address:
            self.token_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(self.token_address),
                abi=self.token_abi
            )
        
        if self.staking_address:
            self.staking_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(self.staking_address),
                abi=self.staking_abi
            )
        
        if self.registry_address:
            self.registry_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(self.registry_address),
                abi=self.registry_abi
            )
    
    def _load_abi(self, filename: str) -> List[Dict]:
        """Load contract ABI from file"""
        abi_path = os.path.join(os.path.dirname(__file__), "..", "abis", filename)
        if os.path.exists(abi_path):
            with open(abi_path, "r") as f:
                return json.load(f)
        return []
    
    async def get_balance(self, address: str) -> Decimal:
        """Get CTXT token balance for an address"""
        if not self.token_contract:
            return Decimal(0)
        
        try:
            balance = self.token_contract.functions.balanceOf(
                Web3.to_checksum_address(address)
            ).call()
            return Decimal(balance) / Decimal(10**18)
        except Exception as e:
            print(f"Error getting balance: {e}")
            return Decimal(0)
    
    async def transfer_tokens(
        self,
        to_address: str,
        amount: Decimal
    ) -> Optional[str]:
        """Transfer CTXT tokens"""
        if not self.token_contract or not self.account:
            return None
        
        try:
            # Convert amount to wei
            amount_wei = int(amount * Decimal(10**18))
            
            # Build transaction
            function = self.token_contract.functions.transfer(
                Web3.to_checksum_address(to_address),
                amount_wei
            )
            
            tx = await self._build_and_send_transaction(function)
            return tx
        except Exception as e:
            print(f"Error transferring tokens: {e}")
            return None
    
    async def mint_rewards(
        self,
        recipient: str,
        amount: Decimal
    ) -> Optional[str]:
        """Mint reward tokens to a recipient"""
        if not self.token_contract or not self.account:
            return None
        
        try:
            amount_wei = int(amount * Decimal(10**18))
            
            function = self.token_contract.functions.mint(
                Web3.to_checksum_address(recipient),
                amount_wei
            )
            
            tx = await self._build_and_send_transaction(function)
            return tx
        except Exception as e:
            print(f"Error minting tokens: {e}")
            return None
    
    async def stake_tokens(self, amount: Decimal) -> Optional[str]:
        """Stake CTXT tokens"""
        if not self.staking_contract or not self.account:
            return None
        
        try:
            amount_wei = int(amount * Decimal(10**18))
            
            # First approve staking contract
            approve_tx = await self._approve_tokens(
                self.staking_address,
                amount_wei
            )
            
            if not approve_tx:
                return None
            
            # Then stake
            function = self.staking_contract.functions.stake(amount_wei)
            tx = await self._build_and_send_transaction(function)
            return tx
        except Exception as e:
            print(f"Error staking tokens: {e}")
            return None
    
    async def unstake_tokens(self, amount: Decimal) -> Optional[str]:
        """Unstake CTXT tokens"""
        if not self.staking_contract or not self.account:
            return None
        
        try:
            amount_wei = int(amount * Decimal(10**18))
            
            function = self.staking_contract.functions.unstake(amount_wei)
            tx = await self._build_and_send_transaction(function)
            return tx
        except Exception as e:
            print(f"Error unstaking tokens: {e}")
            return None
    
    async def claim_staking_rewards(self) -> Optional[str]:
        """Claim staking rewards"""
        if not self.staking_contract or not self.account:
            return None
        
        try:
            function = self.staking_contract.functions.claimRewards()
            tx = await self._build_and_send_transaction(function)
            return tx
        except Exception as e:
            print(f"Error claiming rewards: {e}")
            return None
    
    async def get_staking_info(self, address: str) -> Dict[str, Any]:
        """Get staking information for an address"""
        if not self.staking_contract:
            return {}
        
        try:
            stake_info = self.staking_contract.functions.getUserStakeInfo(
                Web3.to_checksum_address(address)
            ).call()
            
            pending_rewards = self.staking_contract.functions.getPendingRewards(
                Web3.to_checksum_address(address)
            ).call()
            
            return {
                "staked_amount": Decimal(stake_info[0]) / Decimal(10**18),
                "stake_timestamp": stake_info[1],
                "tier": stake_info[2],
                "pending_rewards": Decimal(pending_rewards) / Decimal(10**18)
            }
        except Exception as e:
            print(f"Error getting staking info: {e}")
            return {}
    
    async def register_user(
        self,
        wallet: str,
        username: str,
        x_handle: str = ""
    ) -> Optional[str]:
        """Register a new user in the registry"""
        if not self.registry_contract or not self.account:
            return None
        
        try:
            function = self.registry_contract.functions.registerUser(
                Web3.to_checksum_address(wallet),
                username,
                x_handle
            )
            
            tx = await self._build_and_send_transaction(function)
            return tx
        except Exception as e:
            print(f"Error registering user: {e}")
            return None
    
    async def submit_contribution(
        self,
        content_hash: str,
        contribution_type: int,
        platform: str,
        metadata: str = ""
    ) -> Optional[str]:
        """Submit a new contribution"""
        if not self.registry_contract or not self.account:
            return None
        
        try:
            function = self.registry_contract.functions.submitContribution(
                content_hash,
                contribution_type,
                platform,
                metadata
            )
            
            tx = await self._build_and_send_transaction(function)
            return tx
        except Exception as e:
            print(f"Error submitting contribution: {e}")
            return None
    
    async def validate_contribution(
        self,
        contribution_id: int,
        quality_score: int
    ) -> Optional[str]:
        """Validate a contribution and assign quality score"""
        if not self.registry_contract or not self.account:
            return None
        
        try:
            function = self.registry_contract.functions.validateContribution(
                contribution_id,
                quality_score
            )
            
            tx = await self._build_and_send_transaction(function)
            return tx
        except Exception as e:
            print(f"Error validating contribution: {e}")
            return None
    
    async def get_user_profile(self, address: str) -> Dict[str, Any]:
        """Get user profile from registry"""
        if not self.registry_contract:
            return {}
        
        try:
            profile = self.registry_contract.functions.getUserProfile(
                Web3.to_checksum_address(address)
            ).call()
            
            return {
                "wallet": profile[0],
                "username": profile[1],
                "x_handle": profile[2],
                "registration_time": profile[3],
                "reputation_score": profile[4],
                "total_contributions": profile[5],
                "total_validated": profile[6],
                "total_earned": Decimal(profile[7]) / Decimal(10**18),
                "is_active": profile[8]
            }
        except Exception as e:
            print(f"Error getting user profile: {e}")
            return {}
    
    async def _approve_tokens(
        self,
        spender: str,
        amount: int
    ) -> Optional[str]:
        """Approve token spending"""
        if not self.token_contract or not self.account:
            return None
        
        try:
            function = self.token_contract.functions.approve(
                Web3.to_checksum_address(spender),
                amount
            )
            
            tx = await self._build_and_send_transaction(function)
            return tx
        except Exception as e:
            print(f"Error approving tokens: {e}")
            return None
    
    async def _build_and_send_transaction(self, function) -> Optional[str]:
        """Build and send a transaction"""
        try:
            # Get gas estimate
            gas_estimate = function.estimate_gas({"from": self.account.address})
            
            # Get current gas price
            gas_price = self.w3.eth.gas_price
            
            # Build transaction
            tx_data = function.build_transaction({
                "from": self.account.address,
                "gas": int(gas_estimate * 1.2),  # Add 20% buffer
                "gasPrice": gas_price,
                "nonce": self.w3.eth.get_transaction_count(self.account.address),
                "chainId": self.chain_id
            })
            
            # Sign transaction
            signed_tx = self.account.sign_transaction(tx_data)
            
            # Send transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            return receipt.transactionHash.hex()
        except Exception as e:
            print(f"Error building/sending transaction: {e}")
            return None
    
    async def listen_to_events(
        self,
        contract_name: str,
        event_name: str,
        callback,
        from_block: int = "latest"
    ):
        """Listen to contract events"""
        contract = None
        
        if contract_name == "token":
            contract = self.token_contract
        elif contract_name == "staking":
            contract = self.staking_contract
        elif contract_name == "registry":
            contract = self.registry_contract
        
        if not contract:
            return
        
        event_filter = contract.events[event_name].create_filter(
            fromBlock=from_block
        )
        
        while True:
            try:
                for event in event_filter.get_new_entries():
                    await callback(event)
                await asyncio.sleep(2)  # Poll every 2 seconds
            except Exception as e:
                print(f"Error in event listener: {e}")
                await asyncio.sleep(5)


# Example usage
async def main():
    """Example usage of blockchain service"""
    service = BlockchainService()
    
    # Get balance
    balance = await service.get_balance("0x1234...")
    print(f"Balance: {balance} CTXT")
    
    # Get staking info
    staking_info = await service.get_staking_info("0x1234...")
    print(f"Staking info: {staking_info}")
    
    # Get user profile
    profile = await service.get_user_profile("0x1234...")
    print(f"User profile: {profile}")


if __name__ == "__main__":
    asyncio.run(main())