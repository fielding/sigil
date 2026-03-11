---
id: API-AUTH-V1
type: api
status: active
---

# Auth API

## Description

Handles user registration, login, and token verification. Issues JWT tokens consumed by all other services for authentication. This is the security boundary — every authenticated request must carry a valid token issued by this service.

## Contract

### `POST /api/auth/register`

```json
{ "email": "user@example.com", "password": "..." }
```

Returns `201` with `{ "token": "..." }`.

### `POST /api/auth/login`

```json
{ "email": "user@example.com", "password": "..." }
```

Returns `200` with `{ "token": "..." }` or `401`.

### `GET /api/auth/verify`

Header: `Authorization: Bearer <token>`

Returns `200` with `{ "sub": "user-id", "email": "..." }` or `401`.

## Links

- Provided by: [[COMP-auth-service]]
- Consumed by: [[COMP-web-app]] [[COMP-order-service]] [[COMP-notification-service]]
- Gates: [[GATE-0002]]
