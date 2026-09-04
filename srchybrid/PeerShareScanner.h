//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#pragma once

#include "EmuleNextDatabase.h"
#include <map>
#include <vector>

enum EmuleNextPeerShareStatus
{
    ENPSS_UNKNOWN = 0,
    ENPSS_QUEUED,
    ENPSS_QUERYING,
    ENPSS_SHARED,
    ENPSS_DENIED,
    ENPSS_TIMEOUT,
    ENPSS_UNSUPPORTED,
    ENPSS_ERROR
};

struct EmuleNextPeerShareState
{
    EmuleNextHash16 peerHash;
    EmuleNextPeerShareStatus status;
    uint64 firstSeen;
    uint64 lastQueued;
    uint64 lastRequested;
    uint64 lastCompleted;
    uint64 nextAllowed;
    uint32 fileCount;
    uint64 totalBytes;
    CString lastError;

    EmuleNextPeerShareState();
};

class IEmuleNextPeerShareTransport
{
public:
    virtual ~IEmuleNextPeerShareTransport() {}

    // Implementations MUST use the normal eMule shared-file request. Returning
    // false means no request was sent. The scanner never bypasses peer privacy.
    virtual bool RequestSharedFileList(const EmuleNextHash16& peerHash) = 0;
    virtual bool IsPeerOnline(const EmuleNextHash16& peerHash) const = 0;
};

class CPeerShareScanner
{
public:
    CPeerShareScanner();

    void SetTransport(IEmuleNextPeerShareTransport* transport);
    void SetEnabled(bool enabled);
    bool IsEnabled() const;
    void SetMaxConcurrent(uint32 maxConcurrent);
    void SetSuccessfulTtlSeconds(uint64 ttlSeconds);
    void SetFailureCooldownSeconds(uint64 cooldownSeconds);

    bool QueuePeer(const EmuleNextHash16& peerHash, bool highPriority = false, uint64 now = 0);
    void Tick(uint64 now = 0);

    void OnSharedFileList(const EmuleNextHash16& peerHash, uint32 fileCount, uint64 totalBytes, uint64 now = 0);
    void OnDenied(const EmuleNextHash16& peerHash, uint64 now = 0);
    void OnUnsupported(const EmuleNextHash16& peerHash, uint64 now = 0);
    void OnTimeout(const EmuleNextHash16& peerHash, LPCTSTR error = NULL, uint64 now = 0);
    void OnError(const EmuleNextHash16& peerHash, LPCTSTR error, uint64 now = 0);

    bool GetState(const EmuleNextHash16& peerHash, EmuleNextPeerShareState& state) const;
    void GetStates(std::vector<EmuleNextPeerShareState>& states) const;
    uint32 GetActiveCount() const;
    uint32 GetQueuedCount() const;

private:
    struct HashLess
    {
        bool operator()(const std::array<unsigned char, 16>& left,
            const std::array<unsigned char, 16>& right) const;
    };

    struct Entry
    {
        EmuleNextPeerShareState state;
        bool highPriority;
        Entry() : highPriority(false) {}
    };

    typedef std::map<std::array<unsigned char, 16>, Entry, HashLess> StateMap;

    static uint64 ResolveNow(uint64 now);
    Entry* FindEntry(const EmuleNextHash16& peerHash);
    const Entry* FindEntry(const EmuleNextHash16& peerHash) const;
    void Finish(const EmuleNextHash16& peerHash, EmuleNextPeerShareStatus status,
        uint64 nextDelay, LPCTSTR error, uint64 now);
    Entry* NextReady(uint64 now);

    StateMap m_states;
    IEmuleNextPeerShareTransport* m_transport;
    bool m_enabled;
    uint32 m_maxConcurrent;
    uint64 m_successTtl;
    uint64 m_failureCooldown;
    uint64 m_deniedCooldown;
    uint64 m_requestTimeout;
};
