// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title IContextlyRegistry
 * @dev Interface for Contextly Registry contract
 */
interface IContextlyRegistry {
    // Enums
    enum ContributionType { CONVERSATION, SUMMARY, KNOWLEDGE_GRAPH, VALIDATION }
    
    // Structs
    struct UserProfile {
        address wallet;
        string username;
        string xHandle;
        uint256 registrationTime;
        uint256 reputationScore;
        uint256 totalContributions;
        uint256 totalValidated;
        uint256 totalEarned;
        bool isActive;
    }
    
    struct Contribution {
        uint256 id;
        address contributor;
        string contentHash;
        ContributionType contributionType;
        uint256 timestamp;
        string platform;
        string metadata;
        uint256 qualityScore;
        bool isValidated;
        address validator;
        uint256 rewardAmount;
    }
    
    // Functions
    function registerUser(address wallet, string calldata username, string calldata xHandle) external;
    function submitContribution(
        string calldata contentHash,
        ContributionType contributionType,
        string calldata platform,
        string calldata metadata
    ) external;
    function validateContribution(uint256 contributionId, uint256 qualityScore) external;
    function getUserProfile(address user) external view returns (UserProfile memory);
    function getContribution(uint256 contributionId) external view returns (Contribution memory);
    function getUserContributions(address user) external view returns (uint256[] memory);
    
    // Events
    event UserRegistered(address indexed wallet, string username);
    event ContributionSubmitted(uint256 indexed contributionId, address indexed contributor, ContributionType contributionType);
    event ContributionValidated(uint256 indexed contributionId, uint256 qualityScore);
    event RewardDistributed(address indexed recipient, uint256 indexed contributionId, uint256 amount);
}