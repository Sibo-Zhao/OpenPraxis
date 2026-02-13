# System Design Interview Retrospective

## Problem

Design a URL shortening service supporting tens of millions of users.

## My Approach

I started by asking about read/write ratio and latency requirements, then expanded across storage, short code generation, and high availability. For storage I proposed a KV + DB approach; for short codes I used base62-encoded snowflake IDs.

## Feedback

The interviewer pointed out: I did not clarify CAP trade-offs and the consistency model; my handling of hot keys (local cache, multi-level caching) was not specific enough.

## Takeaways

- System design should anchor constraints first (QPS, latency, consistency).
- Hot-key and degradation strategies must be thought through in advance — simply saying "add a cache" is not enough.
