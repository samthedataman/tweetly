// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/utils/math/SafeMath.sol";

/**
 * @title TokenVesting
 * @dev Library for token vesting calculations
 */
library TokenVesting {
    using SafeMath for uint256;
    
    struct VestingSchedule {
        uint256 totalAmount;
        uint256 startTime;
        uint256 cliffDuration;
        uint256 vestingDuration;
        uint256 releasedAmount;
        bool revocable;
        bool revoked;
    }
    
    /**
     * @dev Calculates the vested amount at a given time
     * @param schedule The vesting schedule
     * @param currentTime Current timestamp
     * @return The vested amount
     */
    function calculateVestedAmount(
        VestingSchedule memory schedule,
        uint256 currentTime
    ) internal pure returns (uint256) {
        if (schedule.revoked) {
            return schedule.releasedAmount;
        }
        
        if (currentTime < schedule.startTime.add(schedule.cliffDuration)) {
            return 0;
        }
        
        if (currentTime >= schedule.startTime.add(schedule.vestingDuration)) {
            return schedule.totalAmount;
        }
        
        uint256 timeFromStart = currentTime.sub(schedule.startTime);
        uint256 vestedAmount = schedule.totalAmount
            .mul(timeFromStart)
            .div(schedule.vestingDuration);
            
        return vestedAmount;
    }
    
    /**
     * @dev Calculates the releasable amount
     * @param schedule The vesting schedule
     * @param currentTime Current timestamp
     * @return The releasable amount
     */
    function calculateReleasableAmount(
        VestingSchedule memory schedule,
        uint256 currentTime
    ) internal pure returns (uint256) {
        uint256 vestedAmount = calculateVestedAmount(schedule, currentTime);
        return vestedAmount.sub(schedule.releasedAmount);
    }
    
    /**
     * @dev Creates a new vesting schedule
     * @param totalAmount Total tokens to vest
     * @param startTime Start time of vesting
     * @param cliffDuration Cliff period duration
     * @param vestingDuration Total vesting duration
     * @param revocable Whether the vesting is revocable
     * @return The new vesting schedule
     */
    function createVestingSchedule(
        uint256 totalAmount,
        uint256 startTime,
        uint256 cliffDuration,
        uint256 vestingDuration,
        bool revocable
    ) internal pure returns (VestingSchedule memory) {
        require(vestingDuration > 0, "Vesting duration must be > 0");
        require(totalAmount > 0, "Total amount must be > 0");
        require(cliffDuration <= vestingDuration, "Cliff must be <= vesting duration");
        
        return VestingSchedule({
            totalAmount: totalAmount,
            startTime: startTime,
            cliffDuration: cliffDuration,
            vestingDuration: vestingDuration,
            releasedAmount: 0,
            revocable: revocable,
            revoked: false
        });
    }
    
    /**
     * @dev Releases tokens from the vesting schedule
     * @param schedule The vesting schedule
     * @param amount Amount to release
     * @param currentTime Current timestamp
     * @return Updated vesting schedule
     */
    function releaseTokens(
        VestingSchedule memory schedule,
        uint256 amount,
        uint256 currentTime
    ) internal pure returns (VestingSchedule memory) {
        uint256 releasable = calculateReleasableAmount(schedule, currentTime);
        require(amount <= releasable, "Amount exceeds releasable");
        
        schedule.releasedAmount = schedule.releasedAmount.add(amount);
        return schedule;
    }
    
    /**
     * @dev Revokes a vesting schedule
     * @param schedule The vesting schedule
     * @return Updated vesting schedule
     */
    function revokeVesting(
        VestingSchedule memory schedule
    ) internal pure returns (VestingSchedule memory) {
        require(schedule.revocable, "Vesting not revocable");
        require(!schedule.revoked, "Already revoked");
        
        schedule.revoked = true;
        return schedule;
    }
}