// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title IContextlyStaking
 * @dev Interface for Contextly Staking contract
 */
interface IContextlyStaking {
    // Enums
    enum StakingTier { NONE, BRONZE, SILVER, GOLD, PLATINUM }
    
    // Structs
    struct StakeInfo {
        uint256 amount;
        uint256 timestamp;
        StakingTier tier;
    }
    
    // Functions
    function stake(uint256 amount) external;
    function unstake(uint256 amount) external;
    function claimRewards() external;
    function getPendingRewards(address user) external view returns (uint256);
    function getUserStakeInfo(address user) external view returns (StakeInfo memory);
    function getUserTier(address user) external view returns (StakingTier);
    
    // Events
    event Staked(address indexed user, uint256 amount);
    event Unstaked(address indexed user, uint256 amount);
    event RewardsClaimed(address indexed user, uint256 amount);
}