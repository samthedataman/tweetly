// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Counters.sol";
import "../interfaces/IContextlyRegistry.sol";
import "../interfaces/IContextlyToken.sol";

/**
 * @title ContextlyRegistry
 * @dev Registry for managing user contributions and knowledge graphs
 * @notice Tracks user contributions, quality scores, and rewards distribution
 */
contract ContextlyRegistry is IContextlyRegistry, AccessControl, ReentrancyGuard {
    using Counters for Counters.Counter;
    
    // Role definitions
    bytes32 public constant CONTRIBUTOR_ROLE = keccak256("CONTRIBUTOR_ROLE");
    bytes32 public constant VALIDATOR_ROLE = keccak256("VALIDATOR_ROLE");
    bytes32 public constant MODERATOR_ROLE = keccak256("MODERATOR_ROLE");
    
    // Constants
    uint256 public constant QUALITY_SCORE_DECIMALS = 100;
    uint256 public constant MIN_QUALITY_SCORE = 60;
    uint256 public constant BASE_REWARD = 1 * 10**18; // 1 CTXT base reward
    
    // State variables
    IContextlyToken public immutable ctxtToken;
    Counters.Counter private contributionIdCounter;
    
    // User profiles
    mapping(address => UserProfile) public userProfiles;
    mapping(address => bool) public registeredUsers;
    
    // Contributions
    mapping(uint256 => Contribution) public contributions;
    mapping(address => uint256[]) public userContributions;
    
    // Quality validators
    mapping(address => bool) public validators;
    uint256 public validatorCount;
    
    // Reward multipliers based on contribution type
    mapping(ContributionType => uint256) public typeMultipliers;
    
    // Platform integration
    mapping(string => bool) public supportedPlatforms;
    
    // Events
    event ValidatorAdded(address indexed validator);
    event ValidatorRemoved(address indexed validator);
    event PlatformAdded(string platform);
    event PlatformRemoved(string platform);
    event TypeMultiplierUpdated(ContributionType contributionType, uint256 multiplier);
    
    /**
     * @dev Constructor
     * @param _ctxtToken Address of CTXT token contract
     */
    constructor(address _ctxtToken) {
        require(_ctxtToken != address(0), "Invalid token address");
        ctxtToken = IContextlyToken(_ctxtToken);
        
        // Setup roles
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(MODERATOR_ROLE, msg.sender);
        
        // Initialize type multipliers (in basis points, 10000 = 1x)
        typeMultipliers[ContributionType.CONVERSATION] = 10000; // 1x
        typeMultipliers[ContributionType.SUMMARY] = 15000; // 1.5x
        typeMultipliers[ContributionType.KNOWLEDGE_GRAPH] = 20000; // 2x
        typeMultipliers[ContributionType.VALIDATION] = 12000; // 1.2x
        
        // Add default platforms
        supportedPlatforms["claude"] = true;
        supportedPlatforms["chatgpt"] = true;
        supportedPlatforms["gemini"] = true;
    }
    
    /**
     * @dev Registers a new user
     * @param _wallet User's wallet address
     * @param _username Chosen username
     * @param _xHandle Twitter/X handle (optional)
     */
    function registerUser(
        address _wallet,
        string calldata _username,
        string calldata _xHandle
    ) external override {
        require(!registeredUsers[_wallet], "User already registered");
        require(bytes(_username).length > 0, "Username required");
        require(_wallet != address(0), "Invalid wallet address");
        
        UserProfile storage profile = userProfiles[_wallet];
        profile.wallet = _wallet;
        profile.username = _username;
        profile.xHandle = _xHandle;
        profile.registrationTime = block.timestamp;
        profile.reputationScore = 100; // Starting reputation
        profile.isActive = true;
        
        registeredUsers[_wallet] = true;
        _grantRole(CONTRIBUTOR_ROLE, _wallet);
        
        emit UserRegistered(_wallet, _username);
    }
    
    /**
     * @dev Submits a new contribution
     * @param _contentHash IPFS hash of the contribution content
     * @param _contributionType Type of contribution
     * @param _platform Platform where contribution was made
     * @param _metadata Additional metadata
     */
    function submitContribution(
        string calldata _contentHash,
        ContributionType _contributionType,
        string calldata _platform,
        string calldata _metadata
    ) external override onlyRole(CONTRIBUTOR_ROLE) {
        require(supportedPlatforms[_platform], "Platform not supported");
        require(bytes(_contentHash).length > 0, "Content hash required");
        
        uint256 contributionId = contributionIdCounter.current();
        contributionIdCounter.increment();
        
        Contribution storage contrib = contributions[contributionId];
        contrib.id = contributionId;
        contrib.contributor = msg.sender;
        contrib.contentHash = _contentHash;
        contrib.contributionType = _contributionType;
        contrib.timestamp = block.timestamp;
        contrib.platform = _platform;
        contrib.metadata = _metadata;
        contrib.qualityScore = 0; // To be set by validators
        contrib.isValidated = false;
        
        userContributions[msg.sender].push(contributionId);
        userProfiles[msg.sender].totalContributions++;
        
        emit ContributionSubmitted(contributionId, msg.sender, _contributionType);
    }
    
    /**
     * @dev Validates a contribution and assigns quality score
     * @param _contributionId ID of the contribution
     * @param _qualityScore Quality score (0-100)
     */
    function validateContribution(
        uint256 _contributionId,
        uint256 _qualityScore
    ) external override onlyRole(VALIDATOR_ROLE) {
        Contribution storage contrib = contributions[_contributionId];
        require(contrib.id == _contributionId, "Contribution not found");
        require(!contrib.isValidated, "Already validated");
        require(_qualityScore <= 100, "Invalid quality score");
        
        contrib.qualityScore = _qualityScore;
        contrib.isValidated = true;
        contrib.validator = msg.sender;
        
        // Update user stats
        UserProfile storage profile = userProfiles[contrib.contributor];
        profile.totalValidated++;
        
        // Calculate and distribute rewards if quality meets threshold
        if (_qualityScore >= MIN_QUALITY_SCORE) {
            uint256 reward = _calculateReward(_qualityScore, contrib.contributionType);
            
            if (reward > 0 && ctxtToken.balanceOf(address(this)) >= reward) {
                ctxtToken.transfer(contrib.contributor, reward);
                profile.totalEarned += reward;
                contrib.rewardAmount = reward;
                
                emit RewardDistributed(contrib.contributor, _contributionId, reward);
            }
            
            // Update reputation
            _updateReputation(contrib.contributor, _qualityScore);
        }
        
        emit ContributionValidated(_contributionId, _qualityScore);
    }
    
    /**
     * @dev Gets user profile
     * @param _user User address
     * @return User profile data
     */
    function getUserProfile(address _user) external view override returns (UserProfile memory) {
        return userProfiles[_user];
    }
    
    /**
     * @dev Gets contribution details
     * @param _contributionId Contribution ID
     * @return Contribution data
     */
    function getContribution(uint256 _contributionId) external view override returns (Contribution memory) {
        return contributions[_contributionId];
    }
    
    /**
     * @dev Gets user's contributions
     * @param _user User address
     * @return Array of contribution IDs
     */
    function getUserContributions(address _user) external view override returns (uint256[] memory) {
        return userContributions[_user];
    }
    
    /**
     * @dev Adds a new validator
     * @param _validator Address to add as validator
     */
    function addValidator(address _validator) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(!validators[_validator], "Already a validator");
        
        validators[_validator] = true;
        validatorCount++;
        _grantRole(VALIDATOR_ROLE, _validator);
        
        emit ValidatorAdded(_validator);
    }
    
    /**
     * @dev Removes a validator
     * @param _validator Address to remove
     */
    function removeValidator(address _validator) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(validators[_validator], "Not a validator");
        
        validators[_validator] = false;
        validatorCount--;
        _revokeRole(VALIDATOR_ROLE, _validator);
        
        emit ValidatorRemoved(_validator);
    }
    
    /**
     * @dev Adds a supported platform
     * @param _platform Platform identifier
     */
    function addPlatform(string calldata _platform) external onlyRole(MODERATOR_ROLE) {
        require(!supportedPlatforms[_platform], "Platform already added");
        supportedPlatforms[_platform] = true;
        emit PlatformAdded(_platform);
    }
    
    /**
     * @dev Removes a platform
     * @param _platform Platform identifier
     */
    function removePlatform(string calldata _platform) external onlyRole(MODERATOR_ROLE) {
        require(supportedPlatforms[_platform], "Platform not found");
        supportedPlatforms[_platform] = false;
        emit PlatformRemoved(_platform);
    }
    
    /**
     * @dev Updates reward multiplier for contribution type
     * @param _type Contribution type
     * @param _multiplier New multiplier (in basis points)
     */
    function updateTypeMultiplier(
        ContributionType _type,
        uint256 _multiplier
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(_multiplier >= 5000 && _multiplier <= 50000, "Invalid multiplier");
        typeMultipliers[_type] = _multiplier;
        emit TypeMultiplierUpdated(_type, _multiplier);
    }
    
    /**
     * @dev Bans a user
     * @param _user User to ban
     */
    function banUser(address _user) external onlyRole(MODERATOR_ROLE) {
        UserProfile storage profile = userProfiles[_user];
        require(profile.isActive, "User not active");
        
        profile.isActive = false;
        _revokeRole(CONTRIBUTOR_ROLE, _user);
    }
    
    /**
     * @dev Unbans a user
     * @param _user User to unban
     */
    function unbanUser(address _user) external onlyRole(MODERATOR_ROLE) {
        UserProfile storage profile = userProfiles[_user];
        require(!profile.isActive, "User already active");
        
        profile.isActive = true;
        _grantRole(CONTRIBUTOR_ROLE, _user);
    }
    
    /**
     * @dev Withdraws tokens from contract (admin only)
     * @param _amount Amount to withdraw
     */
    function withdrawTokens(uint256 _amount) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(ctxtToken.balanceOf(address(this)) >= _amount, "Insufficient balance");
        ctxtToken.transfer(msg.sender, _amount);
    }
    
    /**
     * @dev Internal function to calculate rewards
     * @param _qualityScore Quality score of contribution
     * @param _type Type of contribution
     * @return Calculated reward amount
     */
    function _calculateReward(
        uint256 _qualityScore,
        ContributionType _type
    ) private view returns (uint256) {
        uint256 typeMultiplier = typeMultipliers[_type];
        uint256 qualityMultiplier = (_qualityScore * QUALITY_SCORE_DECIMALS) / 100;
        
        return (BASE_REWARD * typeMultiplier * qualityMultiplier) / (10000 * QUALITY_SCORE_DECIMALS);
    }
    
    /**
     * @dev Internal function to update user reputation
     * @param _user User address
     * @param _qualityScore Quality score from validation
     */
    function _updateReputation(address _user, uint256 _qualityScore) private {
        UserProfile storage profile = userProfiles[_user];
        
        // Weighted average: new reputation = (old * 80% + new score * 20%)
        uint256 newReputation = (profile.reputationScore * 80 + _qualityScore * 20) / 100;
        
        // Ensure reputation stays within bounds
        if (newReputation > 100) {
            newReputation = 100;
        } else if (newReputation < 10) {
            newReputation = 10;
        }
        
        profile.reputationScore = newReputation;
    }
}