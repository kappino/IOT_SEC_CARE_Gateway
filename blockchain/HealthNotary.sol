// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract HealthNotary {
    address public owner;

    struct Record {
        uint256 timestamp;
        bytes32 deviceId;
        bytes32 dataHash;
        bool critical;
    }

    mapping(uint256 => Record) public registry;
    uint256 public recordCount;

    event DataNotarized(uint256 indexed id, bytes32 indexed deviceId, bool critical);

    modifier onlyOwner() {
        require(msg.sender == owner, "Solo l'admin puo notarizzare");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function addRecord(bytes32 _deviceId, bytes32 _dataHash, bool _critical) public onlyOwner {
        recordCount++;
        registry[recordCount] = Record(block.timestamp, _deviceId, _dataHash, _critical);
        emit DataNotarized(recordCount, _deviceId, _critical);
    }
}