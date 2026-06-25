# Tasks — add-user-api

> Discrete steps in order. The implementer marks `[x]` upon completing each one.
> Replace `{ext}` with the project's file extension (e.g. `.py`, `.go`, `.ts`).

---

## Implementation

- [ ] **T1** — Create input validation schema in `src/users/schema.{ext}`: email (RFC 5321), password (min 8 chars). Covers: R2.
- [ ] **T2** — Create `src/users/repository.{ext}` with `create(email, password_hash)` and `find_by_email(email)` methods. Covers: R3, R4, R5.
- [ ] **T3** — Add `enqueue_welcome(user_id)` to `src/notifications/client.{ext}`. Covers: R6.
- [ ] **T4** — Create `src/users/service.{ext}` with `register_user(email, password)`: validate → check uniqueness → hash password → persist → enqueue (non-fatal). Covers: R2, R3, R4, R6, R7.
- [ ] **T5** — Create `src/users/handler.{ext}`: parse request body, call service, map errors to HTTP status codes (201, 409, 422, 500). Covers: R1, R5.
- [ ] **T6** — Register `POST /users` route in the application router. Covers: R1.

---

## Tests

- [ ] **T7** — Unit test: `register_user` with invalid email returns `ValidationError`. Covers: R2.
- [ ] **T8** — Unit test: `register_user` with password < 8 chars returns `ValidationError`. Covers: R2.
- [ ] **T9** — Unit test: `register_user` with existing email returns `DuplicateEmailError`. Covers: R3.
- [ ] **T10** — Unit test: persisted `password_hash` differs from plaintext input; plaintext is not present in the record. Covers: R4.
- [ ] **T11** — Integration test: `POST /users` with valid body returns 201 and a body containing `id`, `email`, `created_at` — no password field. Covers: R1, R5.
- [ ] **T12** — Unit test: notification `enqueue_welcome` is called once on successful registration. Covers: R6.
- [ ] **T13** — Unit test: when `enqueue_welcome` raises an error, `register_user` still returns the created user (no exception propagated). Covers: R7.

---

## Closure

- [ ] **T14** — Document traceability `R<n> ↔ test` in `progress/impl_add-user-api.md`.
- [ ] **T15** — Run `./check.sh` and verify everything passes.
- [ ] **T16** — Update `feature_list.json`: set FEAT-EX-001 to status `"done"`.
- [ ] **T17** — Log summary in `progress/progress.md`.
