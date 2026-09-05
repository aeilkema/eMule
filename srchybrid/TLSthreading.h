#pragma once

#include "mbedtls/threading.h"
#include "mbedtls/x509_crt.h"
#include "mbedtls/pk.h"
#include "psa/crypto.h"

int threading_mutex_init_alt(mbedtls_platform_mutex_t *mutex) noexcept;
void threading_mutex_destroy_alt(mbedtls_platform_mutex_t *mutex) noexcept;
int threading_mutex_lock_alt(mbedtls_platform_mutex_t *mutex) noexcept;
int threading_mutex_unlock_alt(mbedtls_platform_mutex_t *mutex) noexcept;
int cond_init_alt(mbedtls_platform_condition_variable_t *cond) noexcept;
void cond_destroy_alt(mbedtls_platform_condition_variable_t *cond) noexcept;
int cond_signal_alt(mbedtls_platform_condition_variable_t *cond) noexcept;
int cond_broadcast_alt(mbedtls_platform_condition_variable_t *cond) noexcept;
int cond_wait_alt(mbedtls_platform_condition_variable_t *cond, mbedtls_platform_mutex_t *mutex) noexcept;

CString SSLerror(int ret);

// Compatibility bridge for the legacy Unicode MFC web-server code. Current
// mbedTLS file APIs accept narrow paths, while the eMule preferences expose
// CString paths in Unicode builds. Keep the conversion at the TLS boundary so
// the historic WebSocket implementation does not need platform-specific casts.
inline int mbedtls_x509_crt_parse_file(mbedtls_x509_crt *chain, const CString& path)
{
    const CStringA narrowPath(path);
    return ::mbedtls_x509_crt_parse_file(chain, narrowPath.GetString());
}

inline int mbedtls_pk_parse_keyfile(mbedtls_pk_context *ctx, const CString& path, const char *password)
{
    const CStringA narrowPath(path);
    return ::mbedtls_pk_parse_keyfile(ctx, narrowPath.GetString(), password);
}

// mbedTLS 4 no longer exposes the old one-shot mbedtls_sha1 helper. The web
// interface already initializes PSA Crypto before hashing the certificate, so
// map the legacy call to the supported one-shot PSA hash API.
inline int mbedtls_sha1(const unsigned char *input, size_t inputLength, unsigned char output[20])
{
    size_t outputLength = 0;
    const psa_status_t status = psa_hash_compute(
        PSA_ALG_SHA_1,
        input,
        inputLength,
        output,
        PSA_HASH_LENGTH(PSA_ALG_SHA_1),
        &outputLength);
    if (status != PSA_SUCCESS)
        return static_cast<int>(status);
    return outputLength == PSA_HASH_LENGTH(PSA_ALG_SHA_1) ? 0 : -1;
}
