// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/math/SafeMath.sol";
import "../interfaces/IContextlyToken.sol";
import "../interfaces/IContextlyStaking.sol";

/**
 * @title ContextlyStaking
 * @dev Staking contract for CTXT tokens with rewards and tier system
 * @notice Stake CTXT to earn rewards and unlock platform benefits
 */
contract ContextlyStaking is IContextlyStaking, ReentrancyGuard, Pausable, Ownable {
    using SafeMath for uint256;
    
    // Constants
    uint256 public constant SECONDS_PER_YEAR = 365 days;
    uint256 public constant PRECISION = 1e18;
    uint256 public constant MIN_STAKE_AMOUNT = 100 * 10**18; // 100 CTXT minimum
    
    // Tier thresholds
    uint256 public constant BRONZE_THRESHOLD = 1_000 * 10**18; // 1,000 CTXT
    uint256 public constant SILVER_THRESHOLD = 10_000 * 10**18; // 10,000 CTXT
    uint256 public constant GOLD_THRESHOLD = 50_000 * 10**18; // 50,000 CTXT
    uint256 public constant PLATINUM_THRESHOLD = 100_000 * 10**18; // 100,000 CTXT
    
    // State variables
    IContextlyToken public immutable ctxtToken;
    uint256 public rewardRate = 12; // 12% APY
    uint256 public totalStaked;
    uint256 public rewardPool;
    uint256 public lastRewardUpdate;
    
    // Staker info
    mapping(address => StakeInfo) public stakes;
    mapping(address => uint256) public userRewardPerTokenPaid;
    mapping(address => uint256) public rewards;
    
    // Tier benefits multipliers (in basis points, 10000 = 1x)
    mapping(StakingTier => uint256) public tierMultipliers;
    
    // Events
    event RewardRateUpdated(uint256 newRate);
    event RewardPoolFunded(uint256 amount);
    event EmergencyWithdraw(address indexed user, uint256 amount);
    
    /**
     * @dev Constructor
     * @param _ctxtToken Address of CTXT token contract
     */
    constructor(address _ctxtToken) {
        require(_ctxtToken != address(0), "Invalid token address");
        ctxtToken = IContextlyToken(_ctxtToken);
        
        // Initialize tier multipliers
        tierMultipliers[StakingTier.NONE] = 10000; // 1x
        tierMultipliers[StakingTier.BRONZE] = 11000; // 1.1x
        tierMultipliers[StakingTier.SILVER] = 12500; // 1.25x
        tierMultipliers[StakingTier.GOLD] = 15000; // 1.5x
        tierMultipliers[StakingTier.PLATINUM] = 20000; // 2x
        
        lastRewardUpdate = block.timestamp;
    }
    
    /**
     * @dev Stakes CTXT tokens
     * @param _amount Amount of CTXT to stake
     */
    function stake(uint256 _amount) external override nonReentrant whenNotPaused {
        require(_amount >= MIN_STAKE_AMOUNT, "Below minimum stake");
        require(ctxtToken.transferFrom(msg.sender, address(this), _amount), "Transfer failed");
        
        _updateRewards(msg.sender);
        
        StakeInfo storage userStake = stakes[msg.sender];
        userStake.amount = userStake.amount.add(_amount);
        userStake.timestamp = block.timestamp;
        userStake.tier = _calculateTier(userStake.amount);
        
        totalStaked = totalStaked.add(_amount);
        
        emit Staked(msg.sender, _amount);
    }
    
    /**
     * @dev Unstakes CTXT tokens
     * @param _amount Amount of CTXT to unstake
     */
    function unstake(uint256 _amount) external override nonReentrant {
        StakeInfo storage userStake = stakes[msg.sender];
        require(userStake.amount >= _amount, "Insufficient stake");
        require(block.timestamp >= userStake.timestamp + 7 days, "Stake locked");
        
        _updateRewards(msg.sender);
        
        userStake.amount = userStake.amount.sub(_amount);
        userStake.tier = _calculateTier(userStake.amount);
        
        totalStaked = totalStaked.sub(_amount);
        
        require(ctxtToken.transfer(msg.sender, _amount), "Transfer failed");
        
        emit Unstaked(msg.sender, _amount);
    }
    
    /**
     * @dev Claims accumulated rewards
     */
    function claimRewards() external override nonReentrant {
        _updateRewards(msg.sender);
        
        uint256 reward = rewards[msg.sender];
        require(reward > 0, "No rewards to claim");
        require(reward <= rewardPool, "Insufficient reward pool");
        
        rewards[msg.sender] = 0;
        rewardPool = rewardPool.sub(reward);
        
        require(ctxtToken.transfer(msg.sender, reward), "Transfer failed");
        
        emit RewardsClaimed(msg.sender, reward);
    }
    
    /**
     * @dev Gets pending rewards for a user
     * @param _user Address to check
     * @return Pending reward amount
     */
    function getPendingRewards(address _user) external view override returns (uint256) {
        StakeInfo memory userStake = stakes[_user];
        if (userStake.amount == 0) {
            return rewards[_user];
        }
        
        uint256 timeDiff = block.timestamp.sub(lastRewardUpdate);
        uint256 rewardPerToken = _calculateRewardPerToken(timeDiff);
        
        uint256 tierMultiplier = tierMultipliers[userStake.tier];
        uint256 userReward = userStake.amount
            .mul(rewardPerToken.sub(userRewardPerTokenPaid[_user]))
            .mul(tierMultiplier)
            .div(PRECISION)
            .div(10000);
        
        return rewards[_user].add(userReward);
    }
    
    /**
     * @dev Gets user's staking info
     * @param _user Address to check
     * @return Stake information
     */
    function getUserStakeInfo(address _user) external view override returns (StakeInfo memory) {
        return stakes[_user];
    }
    
    /**
     * @dev Gets user's current staking tier
     * @param _user Address to check
     * @return Current tier
     */
    function getUserTier(address _user) external view override returns (StakingTier) {
        return stakes[_user].tier;
    }
    
    /**
     * @dev Funds the reward pool
     * @param _amount Amount to add to reward pool
     */
    function fundRewardPool(uint256 _amount) external onlyOwner {
        require(ctxtToken.transferFrom(msg.sender, address(this), _amount), "Transfer failed");
        rewardPool = rewardPool.add(_amount);
        emit RewardPoolFunded(_amount);
    }
    
    /**
     * @dev Updates the reward rate
     * @param _newRate New reward rate (as percentage, e.g., 12 for 12%)
     */
    function updateRewardRate(uint256 _newRate) external onlyOwner {
        require(_newRate <= 50, "Rate too high"); // Max 50% APY
        _updateRewards(address(0)); // Update global state
        rewardRate = _newRate;
        emit RewardRateUpdated(_newRate);
    }
    
    /**
     * @dev Emergency withdrawal without rewards
     */
    function emergencyWithdraw() external nonReentrant {
        StakeInfo storage userStake = stakes[msg.sender];
        uint256 amount = userStake.amount;
        require(amount > 0, "No stake to withdraw");
        
        userStake.amount = 0;
        userStake.tier = StakingTier.NONE;
        totalStaked = totalStaked.sub(amount);
        
        // Clear rewards
        rewards[msg.sender] = 0;
        userRewardPerTokenPaid[msg.sender] = 0;
        
        require(ctxtToken.transfer(msg.sender, amount), "Transfer failed");
        
        emit EmergencyWithdraw(msg.sender, amount);
    }
    
    /**
     * @dev Pauses the contract
     */
    function pause() external onlyOwner {
        _pause();
    }
    
    /**
     * @dev Unpauses the contract
     */
    function unpause() external onlyOwner {
        _unpause();
    }
    
    /**
     * @dev Updates tier multiplier
     * @param _tier Tier to update
     * @param _multiplier New multiplier (in basis points)
     */
    function updateTierMultiplier(StakingTier _tier, uint256 _multiplier) external onlyOwner {
        require(_multiplier >= 10000 && _multiplier <= 30000, "Invalid multiplier");
        tierMultipliers[_tier] = _multiplier;
    }
    
    /**
     * @dev Internal function to update rewards
     * @param _user User to update rewards for (address(0) for global update)
     */
    function _updateRewards(address _user) private {
        uint256 timeDiff = block.timestamp.sub(lastRewardUpdate);
        if (timeDiff > 0 && totalStaked > 0) {
            uint256 rewardPerToken = _calculateRewardPerToken(timeDiff);
            lastRewardUpdate = block.timestamp;
            
            if (_user != address(0)) {
                StakeInfo memory userStake = stakes[_user];
                if (userStake.amount > 0) {
                    uint256 tierMultiplier = tierMultipliers[userStake.tier];
                    uint256 userReward = userStake.amount
                        .mul(rewardPerToken.sub(userRewardPerTokenPaid[_user]))
                        .mul(tierMultiplier)
                        .div(PRECISION)
                        .div(10000);
                    
                    rewards[_user] = rewards[_user].add(userReward);
                }
                userRewardPerTokenPaid[_user] = rewardPerToken;
            }
        } else if (_user != address(0)) {
            userRewardPerTokenPaid[_user] = _calculateRewardPerToken(0);
        }
    }
    
    /**
     * @dev Calculates reward per token
     * @param _timeDiff Time difference for calculation
     * @return Reward per token
     */
    function _calculateRewardPerToken(uint256 _timeDiff) private view returns (uint256) {
        if (totalStaked == 0) {
            return 0;
        }
        
        return rewardRate
            .mul(PRECISION)
            .mul(_timeDiff)
            .div(SECONDS_PER_YEAR)
            .div(100);
    }
    
    /**
     * @dev Calculates staking tier based on amount
     * @param _amount Staked amount
     * @return Calculated tier
     */
    function _calculateTier(uint256 _amount) private pure returns (StakingTier) {
        if (_amount >= PLATINUM_THRESHOLD) {
            return StakingTier.PLATINUM;
        } else if (_amount >= GOLD_THRESHOLD) {
            return StakingTier.GOLD;
        } else if (_amount >= SILVER_THRESHOLD) {
            return StakingTier.SILVER;
        } else if (_amount >= BRONZE_THRESHOLD) {
            return StakingTier.BRONZE;
        } else {
            return StakingTier.NONE;
        }
    }
}