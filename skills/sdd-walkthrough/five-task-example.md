# Five-Task Example: Email Validation for Python/FastAPI

## Project Context

Adding email validation capabilities to an existing FastAPI service. The implementation plan has five tasks:

1. `validate_email_format()` — regex-based format check
2. `check_domain_reachability()` — DNS lookup to verify domain exists
3. `EmailRateLimiter` — in-memory throttle (max 100 checks per IP per hour)
4. `POST /validate-email` endpoint — wires the above together
5. `email_error_handler` — maps domain errors to JSON error responses

---

## Task 1: Validate Email Format (Happy Path)

**Spec:** Implement `validate_email_format(email: str) -> bool` in `app/validators/email.py`.
Returns `True` for valid RFC-5322 format, `False` otherwise. Tests in `tests/test_email_validator.py`.

### Orchestrator dispatches implementer

```python
delegate(
    agent="superpowers:implementer",
    instruction="""
    TASK: Implement validate_email_format() — email format validator

    SCENE: Adding email validation to a FastAPI service. This is Task 1 of 5.
    You are implementing the foundation — a pure format check, no network calls.

    SPEC:
    - File: app/validators/email.py
    - Function: validate_email_format(email: str) -> bool
    - Returns True for valid RFC-5322 email format, False otherwise
    - Tests in: tests/test_email_validator.py
    - Cover: valid emails, missing @, missing domain, empty string, None input

    Follow TDD. Commit when all tests pass.
    """,
    context_depth="none",
    model_role="coding",
)
```

### Implementer returns: DONE

```
## Task Complete: validate_email_format()

### What I Did
- Created app/validators/email.py with validate_email_format()
- Used re module with RFC-5322-compatible pattern
- Added explicit None guard (returns False)
- Created tests/test_email_validator.py with 8 tests

### Tests Added
- test_valid_simple_email: Tests user@example.com → True
- test_valid_subdomain: Tests user@mail.example.com → True
- test_missing_at_sign: Tests "notanemail" → False
- test_missing_domain: Tests "user@" → False
- test_empty_string: Tests "" → False
- test_none_input: Tests None → False
- test_consecutive_dots: Tests "user..name@example.com" → False
- test_valid_plus_addressing: Tests "user+tag@example.com" → True

### Commits
- a3f1b2c: feat: implement validate_email_format with RFC-5322 pattern

### Self-Review
- [x] Test failed before implementation
- [x] Implementation is minimal
- [x] All tests pass (8/8)
- [x] Ready for spec review
```

### Orchestrator dispatches spec reviewer

```python
delegate(
    agent="superpowers:spec-reviewer",
    instruction="""
    Review commit a3f1b2c against the spec for Task 1.

    SPEC:
    - File: app/validators/email.py
    - Function: validate_email_format(email: str) -> bool
    - Returns True for valid RFC-5322 format, False otherwise
    - Tests cover: valid, missing @, missing domain, empty string, None input

    Confirm: (1) all spec requirements are present, (2) no extra scope was added.
    """,
    context_depth="recent",
    context_scope="agents",
)
```

### Spec reviewer returns: PASS

```
✅ SPEC COMPLIANT

All required behaviors implemented. None guard present. Test coverage matches spec.
No out-of-scope additions detected.
```

### Orchestrator dispatches code quality reviewer

```python
delegate(
    agent="superpowers:code-quality-reviewer",
    instruction="""
    Review commit a3f1b2c for code quality.

    Changed files: app/validators/email.py, tests/test_email_validator.py
    """,
    context_depth="recent",
    context_scope="agents",
)
```

### Code quality reviewer returns: PASS

```
✅ APPROVED

Strengths: Clear function name, proper type hints, docstring present, tests are
readable and well-named. Pattern is compiled at module level (good for performance).

No issues found.
```

**Task 1 complete ✅**

---

## Task 2: Domain Reachability Check (Spec Reviewer Catches Gap)

**Spec:** Implement `check_domain_reachability(email: str) -> bool` in `app/validators/email.py`.
Returns `True` if the domain has a valid MX or A record, `False` if the domain does not exist
or is unreachable. Must not raise exceptions — unreachable domains return `False`.

### Orchestrator dispatches implementer

```python
delegate(
    agent="superpowers:implementer",
    instruction="""
    TASK: Implement check_domain_reachability() — DNS-based domain check

    SCENE: Task 2 of 5. Task 1 (format validator) is already merged.
    This function checks whether an email's domain actually exists in DNS.

    SPEC:
    - File: app/validators/email.py (extend existing file)
    - Function: check_domain_reachability(email: str) -> bool
    - Returns True if domain has MX or A record
    - Returns False if domain does not exist or DNS lookup fails
    - Must NOT raise exceptions — all failures return False
    - Use dnspython (dns.resolver)
    - Tests in: tests/test_email_validator.py

    Follow TDD. Commit when tests pass.
    """,
    context_depth="none",
    model_role="coding",
)
```

### Implementer returns: DONE

```
## Task Complete: check_domain_reachability()

### What I Did
- Added check_domain_reachability() to app/validators/email.py
- Uses dns.resolver to check MX records, falls back to A record
- Added 4 tests with mocked DNS responses

### Commits
- b7e4d91: feat: implement check_domain_reachability with dns.resolver
```

### Orchestrator dispatches spec reviewer

```python
delegate(
    agent="superpowers:spec-reviewer",
    instruction="""
    Review commit b7e4d91 against the spec for Task 2.

    SPEC:
    - Function: check_domain_reachability(email: str) -> bool
    - Returns True if domain has MX or A record
    - Returns False if domain does not exist OR is unreachable
    - CRITICAL: Must NOT raise exceptions — all failures return False

    Verify the exception handling covers all dns.resolver error types.
    """,
    context_depth="recent",
    context_scope="agents",
)
```

### Spec reviewer returns: FAIL — gap found

```
❌ SPEC GAP FOUND

Issue: The implementation catches dns.resolver.NXDOMAIN (domain not found) and
returns False correctly. However, dns.resolver.NoNameservers and
dns.resolver.Timeout are NOT caught — these propagate as exceptions.

The spec says "unreachable domains return False." NoNameservers and Timeout
are exactly "unreachable" scenarios. The implementation raises NetworkError
instead of returning False in those cases.

Required fix: Expand the except clause to catch all dns.resolver exceptions
(or use a bare `except Exception` as a backstop).
```

### Orchestrator re-dispatches implementer with gap description

```python
delegate(
    agent="superpowers:implementer",
    instruction="""
    FIX SPEC GAP in check_domain_reachability() (Task 2).

    PREVIOUS COMMIT: b7e4d91

    GAP IDENTIFIED BY SPEC REVIEWER:
    dns.resolver.NoNameservers and dns.resolver.Timeout are not caught.
    These raise exceptions instead of returning False.

    The spec requires: ALL failure modes return False, no exceptions propagate.

    Fix: Catch dns.resolver.NoNameservers, dns.resolver.Timeout, and
    dns.exception.DNSException as a base class catch for any future DNS errors.
    Add tests that mock each of these exception types and verify False is returned.

    Commit the fix.
    """,
    context_depth="none",
    model_role="coding",
)
```

### Implementer returns: DONE (gap fixed)

```
## Task Complete: fix spec gap in check_domain_reachability()

### What I Did
- Expanded exception handling to catch NoNameservers, Timeout, DNSException
- Added 3 new tests mocking each failure type
- All 7 tests pass

### Commits
- c2a18f3: fix: catch all dns.resolver exceptions in check_domain_reachability
```

### Spec reviewer re-review: PASS

```python
delegate(
    agent="superpowers:spec-reviewer",
    instruction="""
    Re-review commit c2a18f3. Verify the gap is closed:
    NoNameservers, Timeout, and DNSException all return False.
    """,
    context_depth="recent",
    context_scope="agents",
)
```

```
✅ SPEC COMPLIANT

Gap is closed. All DNS failure modes now return False. No remaining issues.
```

### Code quality reviewer: PASS

```
✅ APPROVED

Broad exception catch is intentional and appropriate here — spec requires
defensive behavior. Comment explains why. Tests are comprehensive.
```

**Task 2 complete ✅**

---

## Task 3: In-Memory Rate Limiter (DONE_WITH_CONCERNS)

**Spec:** Implement `EmailRateLimiter` class in `app/validators/rate_limiter.py`.
Tracks per-IP email validation requests. Raises `RateLimitExceeded` after 100 requests
per IP within a rolling 60-minute window. Thread-safe for single-process use.

### Orchestrator dispatches implementer

```python
delegate(
    agent="superpowers:implementer",
    instruction="""
    TASK: Implement EmailRateLimiter — per-IP rate limiting for email validation

    SCENE: Task 3 of 5. Format validator and domain checker are complete.
    This class will be used by the /validate-email endpoint in Task 4.

    SPEC:
    - File: app/validators/rate_limiter.py
    - Class: EmailRateLimiter
    - Method: check_and_record(ip: str) -> None
      Raises RateLimitExceeded if IP has exceeded 100 requests in 60 minutes
      Otherwise records the request timestamp and returns
    - Exception: RateLimitExceeded in app/validators/exceptions.py
    - Thread-safe for single-process use (use threading.Lock)
    - Tests in: tests/test_rate_limiter.py

    Follow TDD. Commit when tests pass.
    """,
    context_depth="none",
    model_role="coding",
)
```

### Implementer returns: DONE_WITH_CONCERNS

```
## Task Complete: EmailRateLimiter

### What I Did
- Created app/validators/rate_limiter.py with EmailRateLimiter
- Uses collections.deque per IP to track timestamps, evicts entries older than 60 min
- Added threading.Lock for thread safety
- Created app/validators/exceptions.py with RateLimitExceeded
- 9 tests pass

### Commits
- d4f5a71: feat: implement EmailRateLimiter with sliding window

### Self-Review
- [x] Test failed before implementation
- [x] Implementation is minimal
- [x] All tests pass (9/9)
- [x] Ready for spec review

### ⚠️ CONCERN
This implementation stores rate limit state in process memory. The spec says
"thread-safe for single-process use" which I've satisfied, but in production
FastAPI is typically run with multiple Gunicorn workers or behind a load balancer.
In that deployment, each worker has its own memory — an IP could send 100 requests
to worker 1 and 100 more to worker 2 without triggering the limit.

If the deployment uses multiple workers, this rate limiter will not work correctly.
A Redis-backed implementation would be needed for multi-worker correctness.

I'm flagging this because the spec says "single-process" but I want to make sure
that constraint is intentional, not an oversight.
```

### Orchestrator reads concern and decides

> The concern is valid and architecturally important. The spec explicitly scoped this to
> single-process, so the implementation is correct per spec. But the implementer is right
> that multi-worker deployments are the norm. I'll note this concern in the task summary
> to surface to the user, then proceed to review.

### Orchestrator dispatches spec reviewer

```python
delegate(
    agent="superpowers:spec-reviewer",
    instruction="""
    Review commit d4f5a71 against the spec for Task 3.

    SPEC:
    - Class: EmailRateLimiter with check_and_record(ip: str) -> None
    - Raises RateLimitExceeded after 100 requests per IP in 60-minute window
    - Thread-safe for single-process use

    Note: implementer flagged that multi-worker deployments won't be covered.
    This is a design observation, not a spec violation — the spec says single-process.
    Verify the implementation meets the spec as written.
    """,
    context_depth="recent",
    context_scope="agents",
)
```

```
✅ SPEC COMPLIANT

Implementation meets spec as written. Single-process thread-safety is satisfied.
The multi-worker concern is a valid architectural observation, not a spec gap.
```

### Orchestrator dispatches code quality reviewer

```python
delegate(
    agent="superpowers:code-quality-reviewer",
    instruction="""
    Review commit d4f5a71 for code quality.

    Changed files: app/validators/rate_limiter.py, tests/test_rate_limiter.py
    Note: implementer flagged a multi-worker concern — valid design observation,
    not a code quality issue. Evaluate the implementation quality as written.
    """,
    context_depth="recent",
    context_scope="agents",
)
```

### Code quality reviewer returns: PASS

```
✅ QUALITY APPROVED

Clean implementation. Sliding window with deque is an appropriate choice.
Lock usage is correct. The concern about multi-worker is noted in the commit message.
```

**Task 3 complete ✅ — concern noted: in-memory rate limiting won't work in multi-worker deployments**

---

## Task 4: POST /validate-email Endpoint (Code Quality Issue)

**Spec:** Add `POST /validate-email` endpoint to `app/routers/email.py`. Accepts JSON body
`{"email": str}`. Returns `{"valid": bool, "checks": {"format": bool, "domain": bool}}`.
Rate-limited using `EmailRateLimiter`. Responds 429 when rate limit exceeded.

### Orchestrator dispatches implementer

```python
delegate(
    agent="superpowers:implementer",
    instruction="""
    TASK: Implement POST /validate-email endpoint

    SCENE: Task 4 of 5. Validators (format, domain) and rate limiter are complete.
    Wire them together in a FastAPI router.

    SPEC:
    - File: app/routers/email.py
    - Endpoint: POST /validate-email
    - Request body: {"email": str}
    - Response: {"valid": bool, "checks": {"format": bool, "domain": bool}}
      valid = True only if both format and domain checks pass
    - Rate limit using EmailRateLimiter.check_and_record(client_ip)
    - On RateLimitExceeded: return HTTP 429
    - Register router in app/main.py
    - Tests in tests/test_email_endpoint.py (use FastAPI TestClient)

    Follow TDD. Commit when tests pass.
    """,
    context_depth="none",
    model_role="coding",
)
```

### Implementer returns: DONE

```
## Task Complete: POST /validate-email

### Commits
- e8b3c44: feat: add POST /validate-email endpoint with rate limiting
```

### Spec review: PASS

```
✅ SPEC COMPLIANT — all fields present, rate limiting wired, 429 on exceeded.
```

### Code quality reviewer returns: FAIL — two issues

```
❌ CODE QUALITY ISSUES

Issue 1 (Important): Magic number
  app/routers/email.py line 12: `limiter = EmailRateLimiter(100, 60)`
  The values 100 and 60 are magic numbers. Extract as named constants:
  RATE_LIMIT_REQUESTS = 100
  RATE_LIMIT_WINDOW_MINUTES = 60

Issue 2 (Important): Missing error handling for malformed request bodies
  If the client sends a request with a missing "email" field or wrong type,
  FastAPI raises a 422 Unprocessable Entity automatically, but there is no
  test verifying this behavior. Add a test for malformed input (missing field,
  wrong type) to ensure the endpoint behaves predictably for bad clients.
```

### Orchestrator re-dispatches implementer (fix attempt 1 of 3)

```python
delegate(
    agent="superpowers:implementer",
    instruction="""
    FIX CODE QUALITY ISSUES in POST /validate-email (Task 4) — fix attempt 1 of 3

    PREVIOUS COMMIT: e8b3c44

    Issues found by code quality reviewer:

    1. Magic numbers in EmailRateLimiter instantiation (line 12)
       Extract: RATE_LIMIT_REQUESTS = 100 and RATE_LIMIT_WINDOW_MINUTES = 60
       as module-level constants in app/routers/email.py

    2. No test for malformed request body
       Add tests in tests/test_email_endpoint.py:
       - POST with missing "email" field → expect 422
       - POST with email as integer instead of string → expect 422

    Commit the fixes.
    """,
    context_depth="none",
    model_role="coding",
)
```

### Implementer returns: DONE

```
## Task Complete: fix code quality issues

### What I Did
- Extracted RATE_LIMIT_REQUESTS and RATE_LIMIT_WINDOW_MINUTES constants
- Added 2 tests for malformed request body (missing field, wrong type)
- All 11 tests pass

### Commits
- f1c2d55: fix: extract rate limit constants, add malformed body tests
```

### Code quality reviewer re-review: PASS

```
✅ APPROVED

Both issues resolved. Constants are well-named and placed logically.
Malformed input tests confirm correct FastAPI 422 behavior.
```

**Task 4 complete ✅**

---

## Task 5: Error Response Handler (NEEDS_CONTEXT)

**Spec:** Implement `email_error_handler` in `app/error_handlers.py`. Registers exception
handlers on the FastAPI app for `RateLimitExceeded` and `ValidationError`. Returns consistent
JSON error format matching the project's existing error shape.

### Orchestrator dispatches implementer

```python
delegate(
    agent="superpowers:implementer",
    instruction="""
    TASK: Implement email_error_handler — exception handlers for email validation errors

    SCENE: Task 5 of 5. All validators and the endpoint are complete.
    Register FastAPI exception handlers to produce consistent JSON error responses.

    SPEC:
    - File: app/error_handlers.py
    - Register handlers for: RateLimitExceeded, ValidationError
    - Return consistent JSON error format matching the project's existing error shape
    - Register handlers in app/main.py
    - Tests in tests/test_error_handlers.py

    Follow TDD. Commit when tests pass.
    """,
    context_depth="none",
    model_role="coding",
)
```

### Implementer returns: NEEDS_CONTEXT

```
## Status: NEEDS_CONTEXT

I cannot find the project's existing error response format. The spec says
"matching the project's existing error shape" but I need to know what that shape is.

I searched for existing error handlers and found none. I checked the existing
endpoints and they all return success responses. I cannot invent the error format
without risking incompatibility with other parts of the system.

Questions:
1. What JSON structure should error responses use?
   Options I've seen in FastAPI projects:
   a. {"detail": "message"}  (FastAPI default)
   b. {"error": {"code": "...", "message": "..."}}
   c. {"status": "error", "message": "...", "code": 429}

2. Is there a shared error model or schema file I should reference?
```

### Orchestrator investigates

> The implementer is right to ask — I should discover the error format rather than guess.
> Let me grep the codebase for existing error patterns.

```python
# Orchestrator runs investigation
grep(pattern=r'HTTPException|raise.*Error|JSONResponse', path='app/', output_mode='content')
grep(pattern=r'"detail"|"error"|"message"', path='app/', output_mode='content')
grep(pattern=r'exception_handler|error_handler', path='app/', output_mode='content')
```

> Found it. `app/routers/auth.py` line 34 uses:
> `raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "..."})`
> FastAPI wraps this as `{"detail": {"code": "...", "message": "..."}}`.
> The project's error shape is: `{"detail": {"code": str, "message": str}}`

### Orchestrator re-dispatches with discovered context

```python
delegate(
    agent="superpowers:implementer",
    instruction="""
    TASK: Implement email_error_handler (Task 5) — re-dispatch with discovered context

    SCENE: Task 5 of 5. I investigated the codebase to find the error format.

    DISCOVERED ERROR FORMAT (from app/routers/auth.py:34):
    The project uses FastAPI's HTTPException with a structured detail dict:
      raise HTTPException(
          status_code=429,
          detail={"code": "RATE_LIMIT_EXCEEDED", "message": "Too many requests"}
      )
    FastAPI serializes this to: {"detail": {"code": "...", "message": "..."}}

    SPEC:
    - File: app/error_handlers.py
    - Register handlers for RateLimitExceeded and ValidationError
    - RateLimitExceeded → HTTP 429, code="RATE_LIMIT_EXCEEDED"
    - ValidationError → HTTP 422, code="VALIDATION_ERROR"
    - Both use {"detail": {"code": str, "message": str}} shape
    - Register handlers in app/main.py
    - Tests verify the JSON shape matches exactly

    Follow TDD. Commit when tests pass.
    """,
    context_depth="none",
    model_role="coding",
)
```

### Implementer returns: DONE

```
## Task Complete: email_error_handler

### What I Did
- Created app/error_handlers.py with handlers for RateLimitExceeded and ValidationError
- Both return {"detail": {"code": "...", "message": "..."}} matching auth.py pattern
- Registered handlers in app/main.py
- 6 tests verify exact JSON shape for each error type

### Commits
- a9b3c07: feat: implement email error handlers with consistent JSON error shape

### Self-Review
- [x] Test failed before implementation
- [x] Implementation is minimal
- [x] All tests pass (6/6)
- [x] Ready for spec review
```

### Orchestrator dispatches spec reviewer

```python
delegate(
    agent="superpowers:spec-reviewer",
    instruction="""
    Review commit a9b3c07 against the spec for Task 5.

    SPEC:
    - File: app/error_handlers.py
    - Register handlers for RateLimitExceeded → HTTP 429, code="RATE_LIMIT_EXCEEDED"
    - Register handlers for ValidationError → HTTP 422, code="VALIDATION_ERROR"
    - Both use {"detail": {"code": str, "message": str}} shape
    - Handlers registered in app/main.py

    Verify handler registration and response shapes match the spec exactly.
    """,
    context_depth="recent",
    context_scope="agents",
)
```

### Spec reviewer returns: PASS

```
✅ SPEC COMPLIANT — both handlers registered, correct status codes, correct shape.
```

### Orchestrator dispatches code quality reviewer

```python
delegate(
    agent="superpowers:code-quality-reviewer",
    instruction="""
    Review commit a9b3c07 for code quality.

    Changed files: app/error_handlers.py, app/main.py, tests/test_error_handlers.py
    """,
    context_depth="recent",
    context_scope="agents",
)
```

### Code quality reviewer returns: PASS

```
✅ QUALITY APPROVED — consistent with project patterns, tests verify exact contract.
```

**Task 5 complete ✅**

---

## Completion Summary

| Task | Description | Status | Notes |
|------|-------------|--------|-------|
| 1 | `validate_email_format()` | ✅ DONE | Clean happy path, 8 tests |
| 2 | `check_domain_reachability()` | ✅ DONE | Spec gap caught and fixed (NetworkError vs False) |
| 3 | `EmailRateLimiter` | ✅ DONE | Complete per spec |
| 4 | `POST /validate-email` | ✅ DONE | 2 quality fixes applied (magic numbers, malformed body test) |
| 5 | `email_error_handler` | ✅ DONE | NEEDS_CONTEXT resolved via grep investigation |

**Total commits:** 7 (including 2 fix commits)

### ⚠️ Concerns Surfaced for User

**Task 3 — In-memory rate limiting (multi-worker incompatibility)**
The `EmailRateLimiter` stores state in process memory. In production with Gunicorn
multi-worker or any horizontally-scaled deployment, each process has independent state.
An IP could exceed the rate limit on one worker without being throttled on another.

**Recommendation:** If this service runs with more than one worker process, replace
`EmailRateLimiter` with a Redis-backed implementation before production deployment.

### Next Steps

1. Run `/verify` to confirm the full test suite passes end-to-end
2. Review the multi-worker concern above and decide if Redis is needed
3. Run `/finish` to merge or create a PR
