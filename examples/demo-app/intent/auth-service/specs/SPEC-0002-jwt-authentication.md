---
id: SPEC-0002
status: accepted
---

# JWT Authentication

## Intent

Give users a way to sign up, log in, and prove their identity to other services. We're using stateless JWT tokens so that services can verify requests without calling back to auth on every request.

## Context

The cart and order services need to know who the user is. We could use sessions, but JWTs let us keep services stateless and avoid a shared session store. This is a small app, so we're not building a full identity provider — just enough auth to demonstrate the flow.

## Goals

- Register with email + password
- Login returns a JWT valid for 1 hour
- Any service can verify a token without a database call
- Passwords are hashed before storage

## Non-goals

- OAuth/social login
- Refresh tokens (1-hour expiry is fine for a demo)
- Role-based access control (all authenticated users have equal access)
- Password reset flow

## Design

The auth service exposes three endpoints through [[API-AUTH-V1]]:
- `POST /register` — hash password, store user, return token
- `POST /login` — verify password, return token
- `GET /verify` — validate token from Authorization header

Tokens are HMAC-signed JSON payloads containing `sub` (user ID), `email`, and `exp` (expiry timestamp). We're not using a full JWT library for the demo — just a simplified encode/decode with HMAC-SHA256.

Password storage uses SHA-256 hashing. In production you'd use bcrypt, but this is a demo.

## Links

- Belongs to: [[COMP-auth-service]]
- Provides: [[API-AUTH-V1]]
- Decided by: [[ADR-0002]]
- Gates: [[GATE-0002]]

## Acceptance Criteria

- [ ] Registration creates a user and returns a valid token
- [ ] Login with correct credentials returns a token
- [ ] Login with wrong credentials returns 401
- [ ] Token verification rejects expired tokens
- [ ] Passwords are never stored or returned in plaintext
