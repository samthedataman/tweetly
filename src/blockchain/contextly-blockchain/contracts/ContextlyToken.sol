// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Snapshot.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/draft-ERC20Permit.sol";
import "../interfaces/IContextlyToken.sol";

/**
 * @title ContextlyToken
 * @dev CTXT Token implementation with advanced features
 * @notice This token powers the Contextly ecosystem for AI-driven knowledge sharing
 */
contract ContextlyToken is 
    ERC20, 
    ERC20Burnable, 
    ERC20Snapshot, 
    Ownable, 
    Pausable, 
    ERC20Permit,
    IContextlyToken 
{
    // Constants
    uint256 public constant MAX_SUPPLY = 1_000_000_000 * 10**18; // 1 billion CTXT
    uint256 public constant INITIAL_SUPPLY = 100_000_000 * 10**18; // 100 million CTXT
    
    // State variables
    mapping(address => bool) public minters;
    mapping(address => uint256) public vestingSchedules;
    mapping(address => uint256) public lastClaimTime;
    
    // Token distribution allocations
    uint256 public constant TEAM_ALLOCATION = 200_000_000 * 10**18; // 20%
    uint256 public constant COMMUNITY_ALLOCATION = 300_000_000 * 10**18; // 30%
    uint256 public constant ECOSYSTEM_ALLOCATION = 200_000_000 * 10**18; // 20%
    uint256 public constant TREASURY_ALLOCATION = 200_000_000 * 10**18; // 20%
    uint256 public constant INITIAL_LIQUIDITY = 100_000_000 * 10**18; // 10%
    
    // Vesting periods
    uint256 public constant TEAM_VESTING_PERIOD = 365 days * 4; // 4 years
    uint256 public constant CLIFF_PERIOD = 365 days; // 1 year cliff
    
    // Events
    event MinterAdded(address indexed minter);
    event MinterRemoved(address indexed minter);
    event VestingScheduleCreated(address indexed beneficiary, uint256 amount, uint256 startTime);
    event TokensClaimed(address indexed beneficiary, uint256 amount);
    
    /**
     * @dev Constructor that gives msg.sender all of initial supply
     */
    constructor(
        address _teamWallet,
        address _communityWallet,
        address _ecosystemWallet,
        address _treasuryWallet
    ) ERC20("Contextly Token", "CTXT") ERC20Permit("Contextly Token") {
        // Mint initial circulating supply to deployer
        _mint(msg.sender, INITIAL_LIQUIDITY);
        
        // Set up vesting for team allocation
        vestingSchedules[_teamWallet] = TEAM_ALLOCATION;
        lastClaimTime[_teamWallet] = block.timestamp + CLIFF_PERIOD;
        emit VestingScheduleCreated(_teamWallet, TEAM_ALLOCATION, block.timestamp);
        
        // Mint other allocations
        _mint(_communityWallet, COMMUNITY_ALLOCATION);
        _mint(_ecosystemWallet, ECOSYSTEM_ALLOCATION);
        _mint(_treasuryWallet, TREASURY_ALLOCATION);
    }
    
    /**
     * @dev Adds a new minter
     * @param _minter Address to be added as minter
     */
    function addMinter(address _minter) external onlyOwner {
        require(_minter != address(0), "Invalid minter address");
        require(!minters[_minter], "Already a minter");
        
        minters[_minter] = true;
        emit MinterAdded(_minter);
    }
    
    /**
     * @dev Removes a minter
     * @param _minter Address to be removed from minters
     */
    function removeMinter(address _minter) external onlyOwner {
        require(minters[_minter], "Not a minter");
        
        minters[_minter] = false;
        emit MinterRemoved(_minter);
    }
    
    /**
     * @dev Mints new tokens (only by authorized minters)
     * @param _to Address to mint tokens to
     * @param _amount Amount of tokens to mint
     */
    function mint(address _to, uint256 _amount) external override {
        require(minters[msg.sender], "Not authorized to mint");
        require(totalSupply() + _amount <= MAX_SUPPLY, "Exceeds max supply");
        
        _mint(_to, _amount);
    }
    
    /**
     * @dev Burns tokens from a specific address (only by authorized minters)
     * @param _from Address to burn tokens from
     * @param _amount Amount of tokens to burn
     */
    function burnFrom(address _from, uint256 _amount) public override(ERC20Burnable, IContextlyToken) {
        require(minters[msg.sender] || msg.sender == _from, "Not authorized");
        
        if (msg.sender != _from) {
            _spendAllowance(_from, msg.sender, _amount);
        }
        
        _burn(_from, _amount);
    }
    
    /**
     * @dev Claims vested tokens
     */
    function claimVestedTokens() external {
        uint256 vestedAmount = vestingSchedules[msg.sender];
        require(vestedAmount > 0, "No vesting schedule");
        require(block.timestamp >= lastClaimTime[msg.sender], "Cliff period not over");
        
        uint256 elapsedTime = block.timestamp - lastClaimTime[msg.sender];
        uint256 claimableAmount = (vestedAmount * elapsedTime) / TEAM_VESTING_PERIOD;
        
        if (claimableAmount > vestedAmount) {
            claimableAmount = vestedAmount;
        }
        
        vestingSchedules[msg.sender] -= claimableAmount;
        lastClaimTime[msg.sender] = block.timestamp;
        
        _mint(msg.sender, claimableAmount);
        emit TokensClaimed(msg.sender, claimableAmount);
    }
    
    /**
     * @dev Returns the amount of tokens that can be claimed by an address
     * @param _beneficiary Address to check
     * @return Amount of tokens that can be claimed
     */
    function getClaimableAmount(address _beneficiary) external view returns (uint256) {
        uint256 vestedAmount = vestingSchedules[_beneficiary];
        if (vestedAmount == 0 || block.timestamp < lastClaimTime[_beneficiary]) {
            return 0;
        }
        
        uint256 elapsedTime = block.timestamp - lastClaimTime[_beneficiary];
        uint256 claimableAmount = (vestedAmount * elapsedTime) / TEAM_VESTING_PERIOD;
        
        return claimableAmount > vestedAmount ? vestedAmount : claimableAmount;
    }
    
    /**
     * @dev Creates a snapshot of balances
     */
    function snapshot() external onlyOwner returns (uint256) {
        return _snapshot();
    }
    
    /**
     * @dev Pauses all token transfers
     */
    function pause() external onlyOwner {
        _pause();
    }
    
    /**
     * @dev Unpauses all token transfers
     */
    function unpause() external onlyOwner {
        _unpause();
    }
    
    /**
     * @dev Hook that is called before any transfer of tokens
     */
    function _beforeTokenTransfer(
        address from,
        address to,
        uint256 amount
    ) internal override(ERC20, ERC20Snapshot) whenNotPaused {
        super._beforeTokenTransfer(from, to, amount);
    }
    
    /**
     * @dev Returns the balance of an account at a specific snapshot
     * @param _account Address to check
     * @param _snapshotId Snapshot ID
     * @return Balance at snapshot
     */
    function balanceOfAt(address _account, uint256 _snapshotId) 
        public 
        view 
        override(ERC20Snapshot, IContextlyToken) 
        returns (uint256) 
    {
        return super.balanceOfAt(_account, _snapshotId);
    }
    
    /**
     * @dev Returns the total supply at a specific snapshot
     * @param _snapshotId Snapshot ID
     * @return Total supply at snapshot
     */
    function totalSupplyAt(uint256 _snapshotId) 
        public 
        view 
        override(ERC20Snapshot, IContextlyToken) 
        returns (uint256) 
    {
        return super.totalSupplyAt(_snapshotId);
    }
}