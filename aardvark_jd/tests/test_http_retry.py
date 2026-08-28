import logging

import pytest
import requests

from aardvark_jd import http_retry
from aardvark_jd.http_retry import BackoffBudgetExhausted, RunBudget, request_with_retry

log = logging.getLogger("test_http_retry")
log.addHandler(logging.NullHandler())


class FakeResponse:
    def __init__(self, status_code=200, json_body=None, text="", headers=None):
        self.status_code = status_code
        self._json_body = json_body if json_body is not None else {}
        self.text = text
        self.content = b"{}" if json_body is not None else b""
        self.ok = 200 <= status_code < 300
        self.headers = headers or {}

    def json(self):
        return self._json_body


class FakeSession:
    """*returns each scripted item in turn; an `Exception` instance is raised, anything else returned*"""

    def __init__(self, script):
        self._script = list(script)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        item = self._script.pop(0) if self._script else self._last
        self._last = item
        if isinstance(item, Exception):
            raise item
        return item


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch):
    slept = []
    monkeypatch.setattr(http_retry, "_sleep", lambda seconds: slept.append(seconds))
    return slept


@pytest.fixture(autouse=True)
def _no_jitter(monkeypatch):
    # MAKE `_backoff_delay` DETERMINISTIC: 2 ** attempt, CLAMPED TO THE CEILING.
    monkeypatch.setattr(http_retry, "_jitter", lambda: 0.0)


def _budget():
    return RunBudget(totalSeconds=10_000)


# ---------------------------------------------------------------- RunBudget

def test_run_budget_tracks_remaining_and_charges():
    budget = RunBudget(totalSeconds=100)
    assert budget.remainingSeconds == 100
    budget.charge(30)
    assert budget.remainingSeconds == 70


def test_run_budget_raises_when_a_charge_would_overrun():
    budget = RunBudget(totalSeconds=10)
    budget.charge(8)
    with pytest.raises(BackoffBudgetExhausted):
        budget.charge(5)
    # THE OVERRUNNING CHARGE IS NOT APPLIED.
    assert budget.spentSeconds == 8


# ---------------------------------------------------------------- happy path

def test_returns_immediately_on_a_2xx(_no_real_sleep):
    session = FakeSession([FakeResponse(200)])
    response = request_with_retry(session, "GET", "https://x/y", budget=_budget())
    assert response.status_code == 200
    assert len(session.calls) == 1
    assert _no_real_sleep == []


def test_adds_a_default_timeout_but_keeps_a_caller_supplied_one():
    session = FakeSession([FakeResponse(200), FakeResponse(200)])
    request_with_retry(session, "GET", "https://x/y", budget=_budget())
    assert session.calls[0][2]["timeout"] == http_retry.HTTP_TIMEOUT
    request_with_retry(session, "GET", "https://x/y", budget=_budget(), timeout=(1, 2))
    assert session.calls[1][2]["timeout"] == (1, 2)


# ---------------------------------------------------------------- retryable statuses

def test_retries_a_429_then_succeeds(_no_real_sleep):
    session = FakeSession([FakeResponse(429), FakeResponse(429), FakeResponse(200)])
    budget = _budget()
    response = request_with_retry(session, "POST", "https://x/y", budget=budget)
    assert response.status_code == 200
    assert len(session.calls) == 3
    assert len(_no_real_sleep) == 2
    assert budget.spentSeconds == sum(_no_real_sleep)


def test_retries_a_5xx_then_succeeds(_no_real_sleep):
    session = FakeSession([FakeResponse(503), FakeResponse(200)])
    request_with_retry(session, "GET", "https://x/y", budget=_budget())
    assert len(_no_real_sleep) == 1


def test_gives_up_after_max_attempts_and_returns_the_last_response(_no_real_sleep):
    session = FakeSession([FakeResponse(429)])
    response = request_with_retry(session, "GET", "https://x/y", budget=_budget())
    assert response.status_code == 429
    assert len(session.calls) == 5
    assert len(_no_real_sleep) == 4


# ---------------------------------------------------------------- the 403 rule

def test_retries_a_rate_limit_403(_no_real_sleep):
    body = {"error": {"errors": [{"reason": "userRateLimitExceeded"}], "code": 403}}
    session = FakeSession([FakeResponse(403, json_body=body), FakeResponse(200)])
    request_with_retry(session, "GET", "https://x/y", budget=_budget())
    assert len(session.calls) == 2


def test_does_not_retry_a_plain_403(_no_real_sleep):
    body = {"error": {"errors": [{"reason": "insufficientFilePermissions"}], "code": 403}}
    session = FakeSession([FakeResponse(403, json_body=body)])
    response = request_with_retry(session, "GET", "https://x/y", budget=_budget())
    assert response.status_code == 403
    assert len(session.calls) == 1
    assert _no_real_sleep == []


def test_does_not_retry_a_plain_404(_no_real_sleep):
    session = FakeSession([FakeResponse(404)])
    request_with_retry(session, "GET", "https://x/y", budget=_budget())
    assert _no_real_sleep == []


def test_does_not_retry_a_403_whose_body_is_not_json(_no_real_sleep):
    class NonJsonResponse(FakeResponse):
        def json(self):
            raise ValueError("no json here")

    session = FakeSession([NonJsonResponse(403, text="Forbidden")])
    response = request_with_retry(session, "GET", "https://x/y", budget=_budget())
    assert response.status_code == 403
    assert _no_real_sleep == []


def test_a_retry_after_date_form_is_ignored_and_backoff_is_used(_no_real_sleep):
    session = FakeSession([
        FakeResponse(429, headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}),
        FakeResponse(200),
    ])
    request_with_retry(session, "GET", "https://x/y", budget=_budget())
    # FELL BACK TO EXPONENTIAL BACKOFF (2 ** 1) RATHER THAN PARSING THE DATE.
    assert _no_real_sleep == [2.0]


# ---------------------------------------------------------------- connection errors

def test_retries_a_connection_error_then_succeeds(_no_real_sleep):
    session = FakeSession([requests.ConnectionError("reset"), FakeResponse(200)])
    request_with_retry(session, "GET", "https://x/y", budget=_budget())
    assert len(_no_real_sleep) == 1


def test_reraises_a_connection_error_after_the_last_attempt(_no_real_sleep):
    session = FakeSession([requests.Timeout("slow")])
    with pytest.raises(requests.Timeout):
        request_with_retry(session, "GET", "https://x/y", budget=_budget())
    assert len(session.calls) == 5


# ---------------------------------------------------------------- Retry-After

def test_honours_retry_after_clamped_to_the_ceiling(_no_real_sleep):
    session = FakeSession([
        FakeResponse(429, headers={"Retry-After": "7"}),
        FakeResponse(429, headers={"Retry-After": "999"}),
        FakeResponse(200),
    ])
    request_with_retry(session, "GET", "https://x/y", budget=_budget())
    assert _no_real_sleep[0] == 7
    assert _no_real_sleep[1] == http_retry._MAX_BACKOFF_SECONDS


def test_an_outsized_retry_after_abandons_the_run_instead_of_sleeping_toward_it(_no_real_sleep):
    session = FakeSession([FakeResponse(429, headers={"Retry-After": "600"})])
    budget = RunBudget(totalSeconds=120)
    with pytest.raises(BackoffBudgetExhausted):
        request_with_retry(session, "GET", "https://x/y", budget=budget)
    # IT DID NOT SLEEP EVEN THE CLAMPED 32 s - THE BUDGET CHECK CAME FIRST.
    assert _no_real_sleep == []


# ---------------------------------------------------------------- the run budget

def test_backoff_budget_exhaustion_aborts_the_retry_loop(_no_real_sleep):
    session = FakeSession([FakeResponse(429)])
    tiny = RunBudget(totalSeconds=3)
    with pytest.raises(BackoffBudgetExhausted):
        request_with_retry(session, "GET", "https://x/y", budget=tiny)
    # IT STOPPED EARLY RATHER THAN RUNNING ALL FIVE ATTEMPTS.
    assert len(session.calls) < 5


# ---------------------------------------------------------------- observability

def test_logs_response_headers_on_a_429(monkeypatch, _no_real_sleep):
    # CAPTURE THE `log.warning` CALLS DIRECTLY - GLOBAL LOGGING STATE LEFT BY
    # OTHER TESTS IN THE SUITE MAKES caplog UNRELIABLE HERE.
    warnings = []
    monkeypatch.setattr(
        http_retry.log, "warning",
        lambda msg, *args: warnings.append(msg % args if args else msg),
    )
    session = FakeSession([FakeResponse(429, headers={"X-RateLimit-Reset": "60"}), FakeResponse(200)])
    request_with_retry(session, "GET", "https://x/y", budget=_budget())

    assert any("X-RateLimit-Reset" in message for message in warnings)


def test_announce_is_called_before_each_backoff(_no_real_sleep):
    session = FakeSession([FakeResponse(429), FakeResponse(429), FakeResponse(200)])
    announced = []
    request_with_retry(session, "GET", "https://x/y", budget=_budget(), announce=announced.append)
    assert len(announced) == 2
    assert "retrying in" in announced[0]
