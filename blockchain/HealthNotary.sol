// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/access/Ownable.sol";

contract HealthNotary is Ownable {
    error Unauthorized();
    error InvalidAddress();
    error InvalidPayload();
    error DuplicateDataHash();

    uint256 public recordCount;

    struct Record {
        uint256 timestamp;
        bytes32 deviceId;
        bytes32 dataHash;
        bool critical;
    }

    mapping(uint256 => Record) public registry;
    mapping(address => bool) public notarizers;
    mapping(bytes32 => bool) public dataHashUsed;

    event DataNotarized(
        uint256 indexed id,
        bytes32 indexed deviceId,
        bytes32 dataHash,
        bool critical,
        address indexed notarizer,
        uint256 timestamp
    );
    event NotarizerUpdated(address indexed notarizer, bool enabled);

    modifier onlyNotarizer() {
        if (!notarizers[msg.sender]) revert Unauthorized();
        _;
    }

    constructor() Ownable(msg.sender) {
        notarizers[msg.sender] = true;
        emit NotarizerUpdated(msg.sender, true);
    }

    function transferOwnership(address newOwner) public override onlyOwner {
        if (newOwner == address(0)) revert InvalidAddress();
        super.transferOwnership(newOwner);
        notarizers[newOwner] = true;
        emit NotarizerUpdated(newOwner, true);
    }

    function setNotarizer(address notarizer, bool enabled) external onlyOwner {
        if (notarizer == address(0)) revert InvalidAddress();
        notarizers[notarizer] = enabled;
        emit NotarizerUpdated(notarizer, enabled);
    }

    function addRecord(bytes32 deviceId, bytes32 dataHash, bool critical) external onlyNotarizer {
        if (deviceId == bytes32(0) || dataHash == bytes32(0)) revert InvalidPayload();
        if (dataHashUsed[dataHash]) revert DuplicateDataHash();
        uint256 newId = ++recordCount;
        registry[newId] = Record(block.timestamp, deviceId, dataHash, critical);
        dataHashUsed[dataHash] = true;
        emit DataNotarized(newId, deviceId, dataHash, critical, msg.sender, block.timestamp);
    }
}
