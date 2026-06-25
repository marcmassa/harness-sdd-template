# Requirements — add-user-api

> Feature FEAT-EX-001 — Adds a user registration endpoint to an existing REST API backend.
> Stack-agnostic example demonstrating how to write EARS requirements for a software feature.
> Each requirement is written in strict EARS and is verifiable by at least one concrete test.

---

## EARS Format Reference

| Pattern | Syntax | When to use |
|---------|--------|-------------|
| **Ubiquitous** | `SHALL ...` | Always true |
| **Event** | `WHEN <event> SHALL ...` | Only when something happens |
| **State** | `WHILE <state> SHALL ...` | While a condition holds |
| **Optional** | `WHERE <option> SHALL ...` | Behavior that varies by configuration |
| **Unwanted** | `IF <condition> THEN SHALL ...` | Response to failures or edge cases |

---

## Requirements

### R1 — Registration Endpoint

- **Pattern:** Ubiquitous
- The system SHALL expose a `POST /users` endpoint that accepts `email` and `password` in the request body.

### R2 — Input Validation

- **Pattern:** Event + Unwanted
- WHEN a registration request is received, the system SHALL validate that `email` is a valid RFC 5321 address and that `password` is at least 8 characters long.
- IF validation fails, THEN the system SHALL return HTTP 422 with a structured error body listing each invalid field and the reason.

### R3 — Uniqueness Check

- **Pattern:** Event + Unwanted
- WHEN a registration request passes validation, the system SHALL verify that no existing user record shares the same `email`.
- IF the email is already registered, THEN the system SHALL return HTTP 409 with a machine-readable `"email_taken"` error code.

### R4 — Password Storage

- **Pattern:** Ubiquitous
- The system SHALL persist the password as a salted hash using a recognized algorithm (e.g., bcrypt, argon2). The plaintext password SHALL NOT be stored or logged at any point.

### R5 — Successful Registration Response

- **Pattern:** Event
- WHEN a user is created successfully, the system SHALL return HTTP 201 with a JSON body containing `id`, `email`, and `created_at`. The password hash SHALL NOT appear in the response.

### R6 — Welcome Notification

- **Pattern:** Event
- WHEN a user is created successfully, the system SHALL enqueue a welcome notification for asynchronous delivery. The registration response SHALL NOT block on notification delivery.

### R7 — Resilience Under Partial Failure

- **Pattern:** Unwanted
- IF the persistence step succeeds but the notification enqueue fails, THEN the user record SHALL remain persisted, the failure SHALL be logged with full context, and the endpoint SHALL still return HTTP 201.

---

## Traceability Summary

| Requirement | Verifiable by |
|-------------|---------------|
| R1 | Integration test: `POST /users` returns 201 with valid body |
| R2 | Unit tests: invalid email → 422; short password → 422 |
| R3 | Integration test: duplicate email → 409 with `email_taken` code |
| R4 | Unit test: persisted record contains hash, not plaintext |
| R5 | Integration test: response body does not include password field |
| R6 | Unit test: notification queue receives one message after successful registration |
| R7 | Unit test: notification enqueue failure does not roll back user record; 201 returned |
