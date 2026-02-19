#pragma once
#include <Arduino.h>

enum class VerifyResult {
    OK,
    BAD_JSON,
    MISSING_FIELDS,
    DEVICE_LIMIT_EXCEEDED,
    REPLAY_ATTACK,
    BAD_SIGNATURE,
};

VerifyResult verifyHMAC(const String& payload);
const char*  verifyResultToString(VerifyResult r);