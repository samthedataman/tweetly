// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/metatx/ERC2771Context.sol";
import "./interfaces/IContextlyToken.sol";

contract ContextlyToken is 
    IContextlyToken,
    ERC20, 
    ERC20Burnable,
    ERC20Permit, 
    AccessControl, 
    Pausable, 
    ERC2771Context 
{
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");
    
    // Token distribution
    uint256 public constant TOTAL_SUPPLY = 1_000_000_000 * 10**18; // 1B CTXT
    uint256 public constant USER_REWARDS_ALLOCATION = 400_000_000 * 10**18; // 40%
    
    // Emission parameters
    uint256 public constant INITIAL_DAILY_EMISSION = 1_000_000 * 10**18;
    uint256 public constant EMISSION_DECAY_PERIOD = 365 days;
    uint256 public constant EMISSION_DECAY_RATE = 8500; // 85%
    uint256 public immutable deploymentTime;
    
    // Burn tracking
    uint256 public constant TRANSFER_BURN_RATE = 100; // 1%
    uint256 public totalBurned;
    
    // User statistics
    mapping(address => UserStats) public userStats;
    
    // Events
    event EarningsGranted(
        address indexed user,
        uint256 amount,
        uint256 words,
        uint256 characters,
        uint256 qualityScore,
        string platform,
        string messageId
    );
    
    event TokensBurned(address indexed from, uint256 amount, string reason);
    
    constructor(
        address _trustedForwarder,
        address _treasuryAddress,
        address _liquidityAddress,
        address _teamAddress,
        address _ecosystemAddress,
        address _publicSaleAddress,
        address _privateSaleAddress
    ) 
        ERC20("Contextly", "CTXT") 
        ERC20Permit("Contextly")
        ERC2771Context(_trustedForwarder)
    {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(MINTER_ROLE, msg.sender);
        _grantRole(PAUSER_ROLE, msg.sender);
        
        deploymentTime = block.timestamp;
        
        // Mint allocations
        _mint(address(this), 400_000_000 * 10**18); // 40% rewards pool
        _mint(_teamAddress, 150_000_000 * 10**18); // 15% team
        _mint(_ecosystemAddress, 200_000_000 * 10**18); // 20% ecosystem
        _mint(_treasuryAddress, 100_000_000 * 10**18); // 10% treasury
        _mint(_liquidityAddress, 50_000_000 * 10**18); // 5% liquidity
        _mint(_publicSaleAddress, 50_000_000 * 10**18); // 5% public
        _mint(_privateSaleAddress, 50_000_000 * 10**18); // 5% private
    }
    
    function grantEarnings(
        address user,
        uint256 amount,
        uint256 words,
        uint256 characters,
        uint256 qualityScore,
        string calldata platform,
        string calldata messageId
    ) external override onlyRole(MINTER_ROLE) whenNotPaused {
        require(user != address(0), "Invalid user");
        require(amount > 0, "Amount must be positive");
        require(amount <= balanceOf(address(this)), "Insufficient rewards pool");
        require(qualityScore <= 10000, "Invalid quality score");
        
        _updateUserStats(user, amount, words, characters, qualityScore);
        _transfer(address(this), user, amount);
        
        emit EarningsGranted(user, amount, words, characters, qualityScore, platform, messageId);
    }
    
    function batchGrantEarnings(
        address[] calldata users,
        uint256[] calldata amounts,
        uint256[] calldata words,
        uint256[] calldata characters,
        uint256[] calldata qualityScores,
        string calldata platform
    ) external override onlyRole(MINTER_ROLE) whenNotPaused {
        require(users.length == amounts.length, "Length mismatch");
        require(users.length <= 100, "Batch too large");
        
        uint256 totalAmount = 0;
        
        for (uint256 i = 0; i < users.length; i++) {
            require(users[i] != address(0), "Invalid user");
            require(amounts[i] > 0, "Amount must be positive");
            require(qualityScores[i] <= 10000, "Invalid quality score");
            
            _updateUserStats(users[i], amounts[i], words[i], characters[i], qualityScores[i]);
            totalAmount += amounts[i];
        }
        
        require(totalAmount <= balanceOf(address(this)), "Insufficient rewards pool");
        
        for (uint256 i = 0; i < users.length; i++) {
            _transfer(address(this), users[i], amounts[i]);
        }
    }
    
    function _updateUserStats(
        address user,
        uint256 amount,
        uint256 words,
        uint256 characters,
        uint256 qualityScore
    ) internal {
        UserStats storage stats = userStats[user];
        
        // Streak logic
        uint256 daysSinceLastActive = (block.timestamp - stats.lastActiveTime) / 1 days;
        if (daysSinceLastActive > 2) {
            stats.currentStreak = 1;
        } else if (daysSinceLastActive >= 1) {
            stats.currentStreak++;
            if (stats.currentStreak > stats.longestStreak) {
                stats.longestStreak = stats.currentStreak;
            }
        }
        
        // Update stats
        stats.totalEarned += amount;
        stats.totalWords += words;
        stats.totalCharacters += characters;
        
        // Weighted quality score
        if (stats.totalEarned > amount) {
            uint256 oldWeight = stats.totalEarned - amount;
            stats.qualityScore = (stats.qualityScore * oldWeight + qualityScore * amount) / stats.totalEarned;
        } else {
            stats.qualityScore = qualityScore;
        }
        
        stats.lastActiveTime = block.timestamp;
        
        if (daysSinceLastActive >= 1) {
            stats.contributionDays++;
        }
    }
    
    function _transfer(
        address from,
        address to,
        uint256 amount
    ) internal override {
        if (from != address(0) && to != address(0) && from != address(this)) {
            uint256 burnAmount = (amount * TRANSFER_BURN_RATE) / 10000;
            uint256 transferAmount = amount - burnAmount;
            
            if (burnAmount > 0) {
                super._burn(from, burnAmount);
                totalBurned += burnAmount;
                emit TokensBurned(from, burnAmount, "transfer_burn");
            }
            
            super._transfer(from, to, transferAmount);
        } else {
            super._transfer(from, to, amount);
        }
    }
    
    function burnForBoost(uint256 amount) external override {
        require(amount >= 100 * 10**18, "Minimum 100 CTXT");
        _burn(msg.sender, amount);
        totalBurned += amount;
        emit TokensBurned(msg.sender, amount, "boost_burn");
    }
    
    function getCurrentDailyEmission() public view override returns (uint256) {
        uint256 periodsPassed = (block.timestamp - deploymentTime) / EMISSION_DECAY_PERIOD;
        uint256 currentEmission = INITIAL_DAILY_EMISSION;
        
        for (uint256 i = 0; i < periodsPassed; i++) {
            currentEmission = (currentEmission * EMISSION_DECAY_RATE) / 10000;
        }
        
        return currentEmission;
    }
    
    function getRewardsPoolBalance() public view override returns (uint256) {
        return balanceOf(address(this));
    }
    
    function pause() public onlyRole(PAUSER_ROLE) {
        _pause();
    }
    
    function unpause() public onlyRole(PAUSER_ROLE) {
        _unpause();
    }
    
    function _beforeTokenTransfer(
        address from,
        address to,
        uint256 amount
    ) internal override whenNotPaused {
        super._beforeTokenTransfer(from, to, amount);
    }
    
    function _msgSender() internal view override(Context, ERC2771Context) returns (address) {
        return ERC2771Context._msgSender();
    }
    
    function _msgData() internal view override(Context, ERC2771Context) returns (bytes calldata) {
        return ERC2771Context._msgData();
    }
}