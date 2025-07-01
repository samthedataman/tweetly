// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/**
 * @title IContextlyToken
 * @dev Interface for Contextly Token (CTXT)
 */
interface IContextlyToken is IERC20 {
    // Functions
    function mint(address to, uint256 amount) external;
    function burnFrom(address from, uint256 amount) external;
    function snapshot() external returns (uint256);
    function balanceOfAt(address account, uint256 snapshotId) external view returns (uint256);
    function totalSupplyAt(uint256 snapshotId) external view returns (uint256);
    
    // Events
    event MinterAdded(address indexed minter);
    event MinterRemoved(address indexed minter);
}