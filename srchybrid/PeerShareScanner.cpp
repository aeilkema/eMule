//this file is part of eMule Next
//Copyright (C)2026 eMule Next contributors
//GPL v2 or later
#include "stdafx.h"
#include "PeerShareScanner.h"

#include <algorithm>

namespace
{
    uint64 CurrentSeconds()
    {
        return static_cast<uint64>(time(NULL));
    }
}

EmuleNextPeerShareState::EmuleNextPeerShareState()
    : status(ENPSS_UNKNOWN)
    , firstSeen(0)
    , lastQueued(0)
    , lastRequested(0)
    , lastCompleted(0)
    , nextAllowed(0)
    , fileCount(0)
    , totalBytes(0)
{
}

CPeerShareScanner::CPeerShareScanner()
    : m_transport(NULL)
    , m_enabled(true)
    , m_maxConcurrent(2)
    , m_successTtl(6 * 60 * 60)
    , m_failureCooldown(30 * 60)
    , m_deniedCooldown(24 * 60 * 60)
    , m_requestTimeout(90)
{
}

void CPeerShareScanner::SetTransport(IEmuleNextPeerShareTransport* transport)
{
    m_transport = transport;
}

void CPeerShareScanner::SetEnabled(bool enabled)
{
    m_enabled = enabled;
}

bool CPeerShareScanner::IsEnabled() const
{
    return m_enabled;
}

void CPeerShareScanner::SetMaxConcurrent(uint32 maxConcurrent)
{
    m_maxConcurrent = std::max<uint32>(1, std::min<uint32>(8, maxConcurrent));
}

void CPeerShareScanner::SetSuccessfulTtlSeconds(uint64 ttlSeconds)
{
    m_successTtl = std::max<uint64>(300, ttlSeconds);
}

void CPeerShareScanner::SetFailureCooldownSeconds(uint64 cooldownSeconds)
{
    m_failureCooldown = std::max<uint64>(60, cooldownSeconds);
}

uint64 CPeerShareScanner::ResolveNow(uint64 now)
{
    return now != 0 ? now : CurrentSeconds();
}

bool CPeerShareScanner::HashLess::operator()(const std::array<unsigned char, 16>& left,
    const std::array<unsigned char, 16>& right) const
{
    return std::lexicographical_compare(left.begin(), left.end(), right.begin(), right.end());
}

CPeerShareScanner::Entry* CPeerShareScanner::FindEntry(const EmuleNextHash16& peerHash)
{
    if (!peerHash.valid)
        return NULL;
    StateMap::iterator it = m_states.find(peerHash.bytes);
    return it != m_states.end() ? &it->second : NULL;
}

const CPeerShareScanner::Entry* CPeerShareScanner::FindEntry(const EmuleNextHash16& peerHash) const
{
    if (!peerHash.valid)
        return NULL;
    StateMap::const_iterator it = m_states.find(peerHash.bytes);
    return it != m_states.end() ? &it->second : NULL;
}

bool CPeerShareScanner::QueuePeer(const EmuleNextHash16& peerHash, bool highPriority, uint64 now)
{
    if (!peerHash.valid)
        return false;

    now = ResolveNow(now);
    Entry& entry = m_states[peerHash.bytes];
    if (!entry.state.peerHash.valid) {
        entry.state.peerHash = peerHash;
        entry.state.firstSeen = now;
    }

    // A current request must never be duplicated. Successful, denied and
    // unsupported peers are not hammered before their cooldown expires.
    if (entry.state.status == ENPSS_QUERYING)
        return false;
    if (now < entry.state.nextAllowed) {
        if (highPriority)
            entry.highPriority = true;
        return false;
    }

    entry.state.status = ENPSS_QUEUED;
    entry.state.lastQueued = now;
    entry.state.lastError.Empty();
    entry.highPriority = entry.highPriority || highPriority;
    return true;
}

bool CPeerShareScanner::QueuePeerManual(const EmuleNextHash16& peerHash, uint64 now)
{
    if (!peerHash.valid)
        return false;
    now = ResolveNow(now);

    Entry* existing = FindEntry(peerHash);
    if (existing != NULL) {
        if (existing->state.status == ENPSS_QUERYING)
            return false;
        // A user-requested refresh may replace cached success data, but must
        // never punch through privacy or transport-failure cooldowns.
        if (existing->state.status == ENPSS_SHARED)
            existing->state.nextAllowed = now;
        else if (now < existing->state.nextAllowed)
            return false;
    }
    return QueuePeer(peerHash, true, now);
}

CPeerShareScanner::Entry* CPeerShareScanner::NextReady(uint64 now)
{
    Entry* best = NULL;
    for (StateMap::iterator it = m_states.begin(); it != m_states.end(); ++it) {
        Entry& candidate = it->second;
        if (candidate.state.status != ENPSS_QUEUED || now < candidate.state.nextAllowed)
            continue;
        if (m_transport != NULL && !m_transport->IsPeerOnline(candidate.state.peerHash))
            continue;

        if (best == NULL
            || (candidate.highPriority && !best->highPriority)
            || (candidate.highPriority == best->highPriority
                && candidate.state.lastQueued < best->state.lastQueued)) {
            best = &candidate;
        }
    }
    return best;
}

void CPeerShareScanner::Tick(uint64 now)
{
    if (!m_enabled || m_transport == NULL)
        return;

    now = ResolveNow(now);

    // Timeouts are a transport outcome, never proof that the peer shares
    // nothing. A future scan may retry after the cooldown.
    std::vector<EmuleNextHash16> timedOut;
    for (StateMap::const_iterator it = m_states.begin(); it != m_states.end(); ++it) {
        const EmuleNextPeerShareState& state = it->second.state;
        if (state.status == ENPSS_QUERYING
            && state.lastRequested != 0
            && now >= state.lastRequested + m_requestTimeout) {
            timedOut.push_back(state.peerHash);
        }
    }
    for (size_t i = 0; i < timedOut.size(); ++i)
        OnTimeout(timedOut[i], _T("shared-file request timed out"), now);

    uint32 active = GetActiveCount();
    while (active < m_maxConcurrent) {
        Entry* entry = NextReady(now);
        if (entry == NULL)
            break;

        if (m_transport->RequestSharedFileList(entry->state.peerHash)) {
            entry->state.status = ENPSS_QUERYING;
            entry->state.lastRequested = now;
            entry->state.lastError.Empty();
            entry->highPriority = false;
            ++active;
        }
        else {
            // Could be a transient socket/client state. Keep it queued, but
            // avoid a busy retry loop on every GUI/core tick.
            entry->state.nextAllowed = now + 60;
            entry->state.lastError = _T("request not sent; peer currently unavailable");
            break;
        }
    }
}

void CPeerShareScanner::Finish(const EmuleNextHash16& peerHash,
    EmuleNextPeerShareStatus status,
    uint64 nextDelay,
    LPCTSTR error,
    uint64 now)
{
    Entry* entry = FindEntry(peerHash);
    if (entry == NULL)
        return;

    now = ResolveNow(now);
    entry->state.status = status;
    entry->state.lastCompleted = now;
    entry->state.nextAllowed = now + nextDelay;
    entry->state.lastError = error != NULL ? error : _T("");
    entry->highPriority = false;
}

void CPeerShareScanner::OnSharedFileList(const EmuleNextHash16& peerHash,
    uint32 fileCount,
    uint64 totalBytes,
    uint64 now)
{
    Entry* entry = FindEntry(peerHash);
    if (entry == NULL)
        return;
    entry->state.fileCount = fileCount;
    entry->state.totalBytes = totalBytes;
    Finish(peerHash, ENPSS_SHARED, m_successTtl, NULL, now);
}

void CPeerShareScanner::OnDenied(const EmuleNextHash16& peerHash, uint64 now)
{
    Finish(peerHash, ENPSS_DENIED, m_deniedCooldown,
        _T("peer denied shared-file browsing"), now);
}

void CPeerShareScanner::OnUnsupported(const EmuleNextHash16& peerHash, uint64 now)
{
    Finish(peerHash, ENPSS_UNSUPPORTED, m_deniedCooldown,
        _T("peer does not support shared-file browsing"), now);
}

void CPeerShareScanner::OnTimeout(const EmuleNextHash16& peerHash, LPCTSTR error, uint64 now)
{
    Finish(peerHash, ENPSS_TIMEOUT, m_failureCooldown,
        error != NULL ? error : _T("shared-file request timed out"), now);
}

void CPeerShareScanner::OnError(const EmuleNextHash16& peerHash, LPCTSTR error, uint64 now)
{
    Finish(peerHash, ENPSS_ERROR, m_failureCooldown,
        error != NULL ? error : _T("shared-file request failed"), now);
}

bool CPeerShareScanner::GetState(const EmuleNextHash16& peerHash, EmuleNextPeerShareState& state) const
{
    const Entry* entry = FindEntry(peerHash);
    if (entry == NULL)
        return false;
    state = entry->state;
    return true;
}

void CPeerShareScanner::GetStates(std::vector<EmuleNextPeerShareState>& states) const
{
    states.clear();
    states.reserve(m_states.size());
    for (StateMap::const_iterator it = m_states.begin(); it != m_states.end(); ++it)
        states.push_back(it->second.state);
}

uint32 CPeerShareScanner::GetActiveCount() const
{
    uint32 count = 0;
    for (StateMap::const_iterator it = m_states.begin(); it != m_states.end(); ++it)
        if (it->second.state.status == ENPSS_QUERYING)
            ++count;
    return count;
}

uint32 CPeerShareScanner::GetQueuedCount() const
{
    uint32 count = 0;
    for (StateMap::const_iterator it = m_states.begin(); it != m_states.end(); ++it)
        if (it->second.state.status == ENPSS_QUEUED)
            ++count;
    return count;
}
