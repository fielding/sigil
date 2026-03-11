---
id: SPEC-0005
status: accepted
---

# Order Notifications

## Intent

Send confirmation emails when orders are placed. Users need to know their order went through, and we need a notification abstraction that can grow to support more channels later.

## Context

Right now we only send order confirmations via email. But the notification service is designed as a standalone component so we can add push notifications, SMS, or webhook integrations later without changing the order service.

## Goals

- Send email notification on order confirmation
- Abstract the notification channel (email today, push/SMS later)
- Log all sent notifications for debugging

## Non-goals

- Delivery guarantees (best-effort is fine for a demo)
- User notification preferences
- Template engine for email formatting
- Retry logic for failed sends

## Design

The notification service exposes a simple internal function (not a REST API in v1) that the order service calls directly. It takes a user_id, order_id, and channel, then formats and "sends" the notification.

For the demo, "sending" means appending to an in-memory list. In production, this would be a queue + worker pattern.

The service uses [[API-AUTH-V1]] only to resolve user email from user_id if needed.

## Links

- Belongs to: [[COMP-notification-service]]
- Consumes: [[API-AUTH-V1]]
- Depends on: [[COMP-auth-service]]
- Decided by: [[ADR-0005]]

## Acceptance Criteria

- [ ] Order confirmation creates a notification record with correct order ID
- [ ] Notification includes user ID and channel
- [ ] Sent notifications are retrievable for debugging
- [ ] Service handles missing user gracefully (logs warning, doesn't crash)
