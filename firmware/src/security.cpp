#include "security.h"
#include "config.h"
#include "secrets.h"

#include <ArduinoJson.h>
#include "mbedtls/md.h"

// Device registry

struct DeviceState {
    String id;
    long   lastTs;
};

static DeviceState s_devices[DEVICE_LIMIT];
static int         s_deviceCount = 0;

static DeviceState* findOrRegisterDevice(const String& id) {
    for (int i = 0; i < s_deviceCount; i++) {
        if (s_devices[i].id == id) return &s_devices[i];
    }
    if (s_deviceCount >= DEVICE_LIMIT) return nullptr;
    s_devices[s_deviceCount++] = {id, 0};
    return &s_devices[s_deviceCount - 1];
}

// HMAC-SHA256

static bool computeHMAC(const char* data, char outHex[65]) {
    uint8_t hmacResult[32];
    mbedtls_md_context_t ctx;

    mbedtls_md_init(&ctx);
    if (mbedtls_md_setup(&ctx, mbedtls_md_info_from_type(MBEDTLS_MD_SHA256), 1) != 0) {
        mbedtls_md_free(&ctx);
        return false;
    }
    mbedtls_md_hmac_starts(&ctx, (const uint8_t*)HMAC_SECRET, strlen(HMAC_SECRET));
    mbedtls_md_hmac_update(&ctx, (const uint8_t*)data, strlen(data));
    mbedtls_md_hmac_finish(&ctx, hmacResult);
    mbedtls_md_free(&ctx);

    for (int i = 0; i < 32; i++) {
        snprintf(outHex + i * 2, 3, "%02x", hmacResult[i]);
    }
    
    return true;
}

// Public API

VerifyResult verifyHMAC(const String& payload) {
    StaticJsonDocument<768> doc;
    if (deserializeJson(doc, payload)) return VerifyResult::BAD_JSON;

    const char* id  = doc["id"];
    long        ts  = doc["ts"] | 0L;
    String valStr = doc["value"].as<String>();
    const char* sig = doc["sig"];
    const char* val = valStr.c_str();

    if (!id || valStr.isEmpty() || !sig) return VerifyResult::MISSING_FIELDS;
    
    DeviceState* dev = findOrRegisterDevice(String(id));
    if (!dev) return VerifyResult::DEVICE_LIMIT_EXCEEDED;

    if (ts <= dev->lastTs) {
        Serial.printf("[SEC] Replay from %s (ts=%ld, last=%ld)\n", id, ts, dev->lastTs);
        return VerifyResult::REPLAY_ATTACK;
    }

    char dataBuf[512];
    int written = snprintf(dataBuf, sizeof(dataBuf), "%s%ld%s", id, ts, val);
    
    if (written < 0 || written >= (int)sizeof(dataBuf)) {
        Serial.println("[SEC] ERROR: dataBuf overflow — payload malformato o oltre i limiti");
        return VerifyResult::BAD_SIGNATURE;
    }

    char computed[65];
    if (!computeHMAC(dataBuf, computed)) return VerifyResult::BAD_SIGNATURE;

    if (strcmp(computed, sig) != 0) {
        Serial.printf("[SEC] Bad sig\n  calc: %s\n  recv: %s\n", computed, sig);
        return VerifyResult::BAD_SIGNATURE;
    }

    dev->lastTs = ts;
    return VerifyResult::OK;
}

const char* verifyResultToString(VerifyResult r) {
    switch (r) {
        case VerifyResult::OK:                    return "OK";
        case VerifyResult::BAD_JSON:              return "BAD_JSON";
        case VerifyResult::MISSING_FIELDS:        return "MISSING_FIELDS";
        case VerifyResult::DEVICE_LIMIT_EXCEEDED: return "DEVICE_LIMIT_EXCEEDED";
        case VerifyResult::REPLAY_ATTACK:         return "REPLAY_ATTACK";
        case VerifyResult::BAD_SIGNATURE:         return "BAD_SIGNATURE";
        default:                                  return "UNKNOWN";
    }
}