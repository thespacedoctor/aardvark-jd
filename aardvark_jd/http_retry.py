#!/usr/bin/env python
# encoding: utf-8
"""
*Shared retry, backoff and timeout policy for the mirror HTTP clients*

`craft_client`, `gdrive_client`, `todoist_client` and `dropbox_client` are
each hand-rolled on `requests` with a near-identical `_request`, and none
of them set a timeout or retry anything. That is a data-drift risk once a
mutating command hands sync to a detached process (see
`docs/adr/0001-...`): a hung connection would hold the sync lock forever,
and a single rate-limited call would abandon a mirror that one retry would
have saved.

`request_with_retry` is the one place all four clients route through. It:

- sets a `(connect, read)` timeout on every request, so a background sync
  always eventually ends;
- retries `429`, `5xx`, connection errors and timeouts, and - narrowly -
  a `403` whose body reason is one of Google Drive's rate-limit reasons
  (`userRateLimitExceeded` / `rateLimitExceeded`), because Drive signals
  throttling with a `403`, not a `429`. A plain `403` is *your credentials
  do not permit this* and is never retried;
- backs off with truncated exponential backoff plus jitter, honouring
  `Retry-After` when present (the sleep itself is clamped to the
  per-request ceiling, but the *budget* is charged the server's full
  requested wait, so an outsized `Retry-After` abandons the run cleanly
  rather than retrying toward a deadline it will miss);
- charges every backoff against a per-run `RunBudget`, so a pathological
  run abandons after a bounded total rather than backing off for the sum
  of every request's worst case.

A `RunBudget` covers **one invocation**, not one mirror.
`background_sync.run_mirrors` builds a single budget and threads it
through all three engines, so a command's total backoff is bounded at
`RUN_BACKOFF_BUDGET_SECONDS` however many mirrors it runs. That is what
`background_sync.STALE_LOCK_CUTOFF_SECONDS` is derived from: per-mirror
budgets would put a legitimate run's worst case at three times the
cutoff's own basis, and a healthy-but-throttled sync could then have its
lock stolen mid-flight.

The trade-off is deliberate and it does bite: a mirror that stalls early
spends allowance the later mirrors might have wanted. Bounding the run
wins because the lock, not the mirror, is what a wrong number breaks -
and a mirror starved of retries still records a drift marker and is
repaired by the next whole-tree run.

Author
: David Young
"""

import logging
import random
import time

import requests

log = logging.getLogger(__name__)

# A REQUEST WITH NO TIMEOUT BLOCKS FOREVER. THE READ CEILING IS WHAT
# GUARANTEES A BACKGROUND SYNC EVENTUALLY ENDS, WHICH IS WHAT MAKES
# TICKET 12'S LOCK SAFE AT ALL.
CONNECT_TIMEOUT_SECONDS = 5
READ_TIMEOUT_SECONDS = 30
HTTP_TIMEOUT = (CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS)

_MAX_ATTEMPTS = 5
_BASE_BACKOFF_SECONDS = 1
_MAX_BACKOFF_SECONDS = 32

# CUMULATIVE BACKOFF ONE MIRROR SYNC WILL TOLERATE BEFORE IT ABANDONS AND
# RECORDS DRIFT (SEE THE MODULE DOCSTRING FOR THE PER-INVOCATION CEILING).
# ~30-45 REQUESTS AT ~63 s WORST CASE EACH WOULD OTHERWISE BACK OFF FOR
# FORTY MINUTES.
RUN_BACKOFF_BUDGET_SECONDS = 300

_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
_RATE_LIMIT_403_REASONS = frozenset({"userratelimitexceeded", "ratelimitexceeded"})

# INDIRECTION SO TESTS CAN RUN THE RETRY LOOP DETERMINISTICALLY.
_sleep = time.sleep
_jitter = random.random


class BackoffBudgetExhausted(Exception):
    """*raised when a run's cumulative backoff sleep would exceed its `RunBudget`*"""
    pass


class RunBudget(object):
    """
    *the cumulative backoff-sleep allowance for one mirror sync*

    Mutable by design - it is an accumulator threaded through a single
    run's HTTP clients and charged as backoff sleeps happen. Kept local to
    one `*_sync.get()` call; not shared between mirrors.

    **Key Arguments:**

    - ``totalSeconds`` -- the sleep allowance. Default `RUN_BACKOFF_BUDGET_SECONDS`.
    """

    def __init__(self, totalSeconds=RUN_BACKOFF_BUDGET_SECONDS):
        self.totalSeconds = totalSeconds
        self.spentSeconds = 0.0

    @property
    def remainingSeconds(self):
        """*seconds of backoff sleep still available*"""
        return max(0.0, self.totalSeconds - self.spentSeconds)

    def charge(self, seconds):
        """
        *record a backoff sleep, or raise if it would overrun the budget*

        **Key Arguments:**

        - ``seconds`` -- the sleep about to happen
        """
        if seconds > self.remainingSeconds:
            raise BackoffBudgetExhausted(
                f"backoff budget of {self.totalSeconds:.0f}s exhausted "
                f"({self.spentSeconds:.0f}s already spent, {seconds:.0f}s more requested)"
            )
        self.spentSeconds += seconds


def _reason_strings(response):
    """*every lowercased `reason`/`status` string in a Google-style error body, or an empty set*"""
    try:
        body = response.json()
    except (ValueError, AttributeError):
        return set()
    if not isinstance(body, dict):
        return set()
    error = body.get("error")
    if not isinstance(error, dict):
        return set()
    reasons = {
        (item.get("reason") or "").lower()
        for item in (error.get("errors") or [])
        if isinstance(item, dict)
    }
    reasons.add((error.get("status") or "").lower())
    return reasons


def _is_retryable_response(response):
    """*should this non-2xx response be retried?*"""
    if response.status_code in _RETRYABLE_STATUS:
        return True
    # A 403 IS RETRYABLE ONLY WHEN ITS BODY SAYS RATE LIMIT - OTHERWISE IT
    # MEANS THE CREDENTIALS ARE NOT PERMITTED AND RETRYING HIDES THE FAILURE.
    if response.status_code == 403:
        return bool(_reason_strings(response) & _RATE_LIMIT_403_REASONS)
    return False


def _is_rate_limited(response):
    """*is this a throttle signal whose headers are worth logging?*"""
    return response.status_code == 429 or (
        response.status_code == 403
        and bool(_reason_strings(response) & _RATE_LIMIT_403_REASONS)
    )


def _retry_after_seconds(response):
    """*the `Retry-After` header as whole seconds, or `None` if absent or a date form*"""
    raw = (getattr(response, "headers", None) or {}).get("Retry-After")
    if raw is None:
        return None
    try:
        return max(0, int(str(raw).strip()))
    except ValueError:
        # HTTP-DATE FORM - NONE OF THE THREE APIS USE IT; FALL BACK TO BACKOFF.
        return None


def _backoff_delay(attempt, retryAfterSeconds):
    """
    *how long to wait before the next attempt, and how much to charge the budget*

    Truncated exponential backoff with jitter - Google's prescribed
    algorithm - unless the server sent a `Retry-After`. `Retry-After`
    wins, but the *sleep* is clamped to the per-request ceiling while the
    *budget charge* is the server's full requested wait: an outsized
    `Retry-After` then trips `BackoffBudgetExhausted` and abandons the run
    cleanly rather than sleeping 32 s at a time toward a deadline it will
    miss.

    **Key Arguments:**

    - ``attempt`` -- the 1-based number of the attempt that just failed
    - ``retryAfterSeconds`` -- a server-sent wait, or `None`

    **Return:**

    - ``sleepSeconds``, ``budgetSeconds`` -- the actual sleep, and the amount to charge the run budget
    """
    if retryAfterSeconds is not None:
        return min(retryAfterSeconds, _MAX_BACKOFF_SECONDS), retryAfterSeconds
    delay = min(_MAX_BACKOFF_SECONDS, (2 ** attempt) * _BASE_BACKOFF_SECONDS + _jitter())
    return delay, delay


def request_with_retry(session, method, url, *, budget, announce=None, **kwargs):
    """
    *issue `session.request`, retrying transient failures within a per-run backoff budget*

    Returns the `requests.Response` for the caller to handle exactly as
    before - including a non-2xx response once retries are exhausted, so
    each client still raises its own `<Service>ApiError`. Connection
    errors and timeouts are re-raised after the last attempt.

    **Key Arguments:**

    - ``session`` -- the client's `requests.Session`
    - ``method`` -- the HTTP method
    - ``url`` -- the absolute URL
    - ``budget`` -- the run's `RunBudget`; a backoff that would overrun it raises `BackoffBudgetExhausted`
    - ``announce`` -- optional callable given a one-line message before each backoff sleep (foreground prints it, background logs it). Default `None`.
    - ``kwargs`` -- passed to `session.request`; a `timeout` is added if the caller did not set one

    **Return:**

    - ``response`` -- the `requests.Response` from the first success, or the last attempt
    """
    kwargs.setdefault("timeout", HTTP_TIMEOUT)
    attempt = 0
    while True:
        attempt += 1
        try:
            response = session.request(method, url, **kwargs)
        except (requests.ConnectionError, requests.Timeout):
            if attempt >= _MAX_ATTEMPTS:
                raise
            sleepSeconds, budgetSeconds = _backoff_delay(attempt, None)
            reason = f"{method} {url} - connection error"
        else:
            if response.ok or not _is_retryable_response(response):
                return response
            if _is_rate_limited(response):
                log.warning(
                    "rate limited: %s %s (%s) - response headers: %s",
                    method, url, response.status_code, dict(getattr(response, "headers", {}) or {}),
                )
            if attempt >= _MAX_ATTEMPTS:
                return response
            sleepSeconds, budgetSeconds = _backoff_delay(attempt, _retry_after_seconds(response))
            reason = f"{method} {url} - HTTP {response.status_code}"

        budget.charge(budgetSeconds)
        message = f"{reason}; retrying in {sleepSeconds:.0f}s (attempt {attempt}/{_MAX_ATTEMPTS})"
        if announce:
            announce(message)
        else:
            log.warning(message)
        _sleep(sleepSeconds)
