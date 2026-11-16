# avatcado

Official Python SDK for the [Avatcado](https://avatcado.com) VAT validation API. Validate EU, UK, Swiss, Norwegian, and Australian VAT/GST numbers, look up VAT rates by country, and check EORI numbers for the EU, Northern Ireland and Great Britain. See the full [API reference](https://docs.avatcado.com/api-reference).

## Installation

```bash
pip install avatcado
```

## Quick Start

```python
from avatcado import Avatcado

avatcado = Avatcado("avat_live_...")

result = avatcado.vat.validate("NL123456789B01")
print(result.data.valid)  # True
if result.data.company:
    print(result.data.company.name)
```

## Usage

### `avatcado.vat.validate()`

Validate a single VAT number.

```python
result = avatcado.vat.validate(
    "NL123456789B01",
    requester_vat_number="DE987654321",  # optional, for consultation number
    cache=False,                          # optional, see "Cache and fallback"
    fallback=False,                       # optional, see "Cache and fallback"
    request_id="my-trace-id",            # optional, for request tracing
)

print(result.data.valid)              # True
print(result.data.vat_number)         # "NL123456789B01"
print(result.data.country_code)       # "NL"
print(result.data.company)            # Company(name="Example BV", address=...) or None
print(result.data.consultation_number)  # None or string (EU/UK only; never on fallback)
print(result.data.requested_at)       # "2026-03-18T12:00:00Z"

print(result.meta.request_id)         # "req_abc123"
print(result.meta.source)             # "vies", "hmrc", ... or e.g. "anaf" on fallback
print(result.meta.source_status)      # "live", "cached", "unavailable", "degraded", "fallback"
print(result.meta.cached)             # True/False (None on older API versions)
print(result.meta.stale)              # True/False (None on older API versions)
print(result.meta.cached_at)          # ISO timestamp when cached, else None

print(result.rate_limit.remaining)    # 99
print(result.rate_limit.burst_limit)  # int or None
```

#### Source and fallback

`meta.source` names the registry that produced the served data: `vies`, `hmrc`, `bfs`, `brreg`, `abr`, or `test` in test mode. When VIES is down for a member state, the API consults that country's national register before falling back to stale cache (Pro and Business plans); `source` then names the register (`anaf`, `ares`, `dgfip`, `fssr`, `furs`, `kbo`, `porezna`, `prh`, `rik`, `vid`) and `source_status` is `"fallback"`. `source` is a plain string, not an enum: new registers appear without an SDK release.

| Scenario | `source_status` | `cached` | `stale` | `cached_at` |
|---|---|---|---|---|
| Fresh upstream result | `"live"` | `False` | `False` | `None` |
| Cache hit (within 25-day TTL) | `"cached"` | `True` | `False` | set |
| Upstream down, cached row within TTL served | `"unavailable"` | `True` | `False` | set |
| Upstream down, row beyond TTL served | `"unavailable"` | `True` | `True` | set |
| VIES returned a suspected false negative, prior row served | `"degraded"` | `True` | varies | set |
| VIES down, national register answered | `"fallback"` | `False` | `False` | `None` |

Fallback responses never carry a `consultation_number` (national registers cannot issue one, even with `requester_vat_number`), and `valid` there means the number is registered for domestic VAT. Some registers publish less than VIES: Latvia (`vid`) returns the company name only, so `company.address` is `None`, and Croatia (`porezna`) returns no company at all. The [supported countries page](https://docs.avatcado.com/supported-countries) lists every register. Fallback and stale responses count toward your quota because data was served; only `503` upstream errors are refunded. API versions that predate these fields omit them, in which case they are `None`.

#### Cache and fallback

Leave `cache` and `fallback` unset to get the API defaults. Both are on by default, and both switch off when you pass `requester_vat_number`, so a consultation number always comes from a fresh VIES or HMRC check.

| Argument | Effect |
|---|---|
| `cache=False` | Skip the cache and ask the registry again |
| `cache=True` with a requester | Accept a cached or stored result next to `requester_vat_number` |
| `fallback=False` | Never answer a VIES outage from a national register |
| `fallback=True` with a requester | Accept a national register answer, which carries no consultation number |

`fallback` applies on Pro and Business plans and is ignored on Free. The same two arguments exist on `vat.validate_batch()`, `async_vat.validate()` and `async_vat.validate_batch()`.

```python
# A consultation number when VIES answers, the stored result when it does not
result = avatcado.vat.validate(
    "NL123456789B01",
    requester_vat_number="DE987654321",
    cache=True,
)
```

### `avatcado.vat.validate_batch()`

Validate up to 50 VAT numbers in a single request.

```python
from avatcado import is_batch_success

result = avatcado.vat.validate_batch(
    ["NL123456789B01", "DE987654321", "XX000"],
    requester_vat_number="DE987654321",  # optional
    cache=False,                          # optional
    fallback=False,                       # optional
    request_id="my-trace-id",            # optional
)

print(result.summary.total)      # 3
print(result.summary.succeeded)  # 2
print(result.summary.failed)     # 1

for item in result.results:
    if is_batch_success(item):
        print(f"{item.data.vat_number} is {'valid' if item.data.valid else 'invalid'}")
    else:
        print(f"{item.error.vat_number} failed: {item.error.message}")
```

> `item.meta.vat_number` is deprecated as of 0.5.0: use `item.error.vat_number`. It remains populated for backward compatibility.

### `avatcado.async_vat.validate()`

Submit a VAT number for async validation. Results are delivered via [webhook](https://docs.avatcado.com/webhooks). Requires a Pro or Business plan and a configured webhook URL.

"Async" here names the API's queued endpoints, not Python's `async`: `async_vat` is a blocking call on `Avatcado` and an awaitable on `AsyncAvatcado`.

```python
# Sync client
response = avatcado.async_vat.validate("DE123456789")
print(response.data.request_id)  # Track this ID
print(response.data.status)      # "pending"

# Async client
response = await avatcado.async_vat.validate("DE123456789")
```

### `avatcado.async_vat.validate_batch()`

Submit multiple VAT numbers for async validation.

```python
response = avatcado.async_vat.validate_batch(
    ["DE123456789", "NL987654321B01", "XX000"],
    requester_vat_number="NL987654321B01",  # optional
)
print(response.data.batch_id)   # Track this ID (None when every item was rejected)
print(response.data.accepted)   # Number queued

for item in response.data.rejected:  # Items with invalid format, never queued
    print(item.vat_number, item.error_code, item.error_message)
```

Rejected items are flat: `vat_number`, `error_code` and `error_message`.

### `avatcado.rates.list()`

List VAT rates for all supported countries. Both rates calls accept an optional `request_id` keyword.

```python
result = avatcado.rates.list()

for rate in result.data:
    print(f"{rate.country_name}: {rate.standard_rate}%")
```

### `avatcado.rates.get(country_code)`

Get VAT rates for a specific country.

```python
result = avatcado.rates.get("NL")

print(result.data.standard_rate)  # 21
print(result.data.other_rates)    # [OtherRate(rate=9, type="reduced"), ...]
```

### `avatcado.eori.validate(eori_number)`

Check an EORI number (the customs identifier a business needs to import or export goods). GB numbers are checked with HMRC; numbers from the 27 EU member states and XI are checked with the European Commission's EORI validation service. An EORI number is a separate registration from a VAT number.

```python
result = avatcado.eori.validate(
    "GB123456789000",
    cache=False,  # optional: skip the cache and ask the register again
)

print(result.data.valid)          # True
print(result.data.eori_number)    # "GB123456789000"
print(result.data.company)        # None when the holder published no details
print(result.meta.source)         # "hmrc" or "ec_eos"
print(result.meta.source_status)  # "live", "cached" or "unavailable"
```

`company` is `None` for many valid numbers: both registers publish a name and address only when the holder consented. Spaces, dots, dashes and casing are normalized by the API, and a Greek number sent with the VAT prefix `EL` is checked under the EORI prefix `GR`.

When the register is down, the API serves the most recent stored answer with `source_status` `"unavailable"`, or raises `UpstreamError` when it has none. With `cache=False` a stored answer is never served.

A malformed number raises `ValidationError` with code `invalid_eori_format`. One number per call; there is no batch or async-delivery variant. `AsyncAvatcado` has the same method: `await avatcado.eori.validate(...)`.

## Async Usage

```python
from avatcado import AsyncAvatcado

async with AsyncAvatcado("avat_live_...") as avatcado:
    result = await avatcado.vat.validate("NL123456789B01")
    print(result.data.valid)

    rates = await avatcado.rates.list()
    for rate in rates.data:
        print(f"{rate.country_name}: {rate.standard_rate}%")
```

## Error Handling

The SDK raises typed exceptions for all error conditions. Use `try`/`except` with specific exception classes:

```python
from avatcado import (
    Avatcado,
    AvatcadoError,
    AuthenticationError,
    ValidationError,
    RateLimitError,
    UpstreamError,
)

avatcado = Avatcado("avat_live_...")

try:
    result = avatcado.vat.validate("INVALID")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after}s")
except UpstreamError as e:
    print(f"Tax authority unavailable for {e.vat_number}. Retry after {e.retry_after}s")
    print(f"Failed attempt recorded as {e.validation_id}")
except AuthenticationError as e:
    print("Invalid API key or insufficient plan")
except ValidationError as e:
    print(f"Invalid input: {e.message}")
    if e.details:
        for d in e.details:
            print(f"  {d['field']}: {d['message']}")
except AvatcadoError as e:
    print(e.message, e.code, e.status_code)
```

### Error Classes

| Class | Trigger Codes |
|-------|---------------|
| `AuthenticationError` | `unauthorized`, `tier_insufficient`, `forbidden`, `key_revoked` |
| `ValidationError` | `invalid_vat_format`, `invalid_eori_format`, `missing_parameter`, `validation_error`, `invalid_json` |
| `RateLimitError` | `rate_limit_exceeded`, `burst_limit_exceeded` |
| `UpstreamError` | `upstream_unavailable`, `upstream_member_state_unavailable` |
| `AvatcadoError` | Base class for all errors, including `timeout`, `network_error`, `parse_error`, `unknown_error`, `internal_error`, `not_found`, `webhook_not_configured` |

### Error Properties

```python
e.message               # Human-readable message
e.code                  # Machine-readable code (e.g. "unauthorized", "rate_limit_exceeded")
e.status_code           # HTTP status (0 for network/timeout errors)
e.request_id            # Request ID (string or None)
e.docs_url              # Link to error documentation (string, empty if not provided)
e.details               # Validation details: list of {"field": ..., "message": ...} dicts, or None
e.vat_number            # Normalized VAT number from the failed request (string or None)
e.eori_number           # Normalized EORI number, on errors from eori.validate() (string or None)
e.requester_vat_number  # Normalized requester VAT number from the request (string or None)
e.retry_after           # Seconds from the Retry-After header (float or None)
```

`vat_number` and `requester_vat_number` are echoed by the API on validation, rate-limit, upstream and server errors from the single-number validation endpoints (`vat.validate()`, `async_vat.validate()`), including `tier_insufficient` and `webhook_not_configured` from the async endpoint. They are `None` when the API rejected the request before reading it (`unauthorized`, `forbidden`, `key_revoked`), on batch-level errors (per-item batch errors carry `item.error.vat_number` instead), when no VAT number was submitted, and on responses from API versions that predate these fields.

`UpstreamError` additionally exposes `e.validation_id` (string or None): the identifier of the recorded failed validation attempt. It is present only for `upstream_unavailable` / `upstream_member_state_unavailable` and never in test mode.

A response that is not JSON (a gateway answering for the API) raises `AvatcadoError` with code `unknown_error` and the HTTP status, and still carries `request_id` and `retry_after` from the headers. A `2xx` body that does not have the documented shape raises `AvatcadoError` with code `parse_error`. Every failure is an `AvatcadoError`; the SDK raises no bare `KeyError` or `TypeError` for a response it cannot read.

### Timeouts and retries

`timeout` is per attempt, in seconds. The default is 30. A single validation normally answers in one to three seconds, but when VIES is slow the API keeps retrying it on your behalf and can take longer than 30 seconds to answer. The SDK then raises `AvatcadoError` with code `timeout` and `status_code` 0. Raise `timeout` if you would rather wait, or set `max_retries` to have the SDK try again.

Retries are off by default. Set `max_retries` to turn them on:

```python
avatcado = Avatcado(
    "avat_live_...",
    max_retries=2,         # extra attempts, default 0
    max_retry_delay=60.0,  # seconds, longest wait before one retry, default 60
)
```

| Failure | Retried on |
|---|---|
| `burst_limit_exceeded` (429) | every method |
| any `503` | every method |
| `timeout`, `network_error`, `502`, `504` | GET only: `vat.validate`, `rates.list`, `rates.get`, `eori.validate` |
| everything else, including `rate_limit_exceeded` | never |

A POST that timed out may already have been accepted, so `vat.validate_batch()` and both `async_vat` methods are not retried after a timeout or a dropped connection.

The SDK waits for `Retry-After` when the API sends it, and otherwise 0.5 seconds doubling up to 8 seconds, with jitter. An error whose `Retry-After` is longer than `max_retry_delay` is raised at once: the monthly quota, and a register outage, where the API asks for 300 seconds. Every error exposes `retry_after` (seconds, or `None`), so you can schedule those yourself. `AsyncAvatcado` takes the same arguments and waits with `asyncio.sleep`.

## Test Mode

Use test API keys (`avat_test_*`) to validate without hitting real tax authorities.

```python
avatcado = Avatcado("avat_test_...")
result = avatcado.vat.validate("NL123456789B01")
print(result.meta.mode)  # "test"
```

| Magic VAT Number | Result |
|-----------------|--------|
| `NL123456789B01` | Valid, with company info |
| `XX000000000` | Invalid format error |
| `DE555555555` | Valid, served from stale cache: `source_status` `"unavailable"`, `stale` `True` |
| `RO555555555` | Valid via national registry fallback: `source` `"anaf"`, `source_status` `"fallback"`, no consultation number |

`eori.validate()` has its own test numbers: `NL111111111` (valid, with company), `NL222222222` (valid, `company` `None`), `NL000000000` (not valid) and `NL999999999` (`upstream_unavailable`).

See the [test mode docs](https://docs.avatcado.com/test-mode) for the full list of magic numbers.

## Configuration

```python
# String API key
avatcado = Avatcado("avat_live_...")

# Keyword arguments
avatcado = Avatcado(
    api_key="avat_live_...",
    base_url="https://api.avatcado.com",  # default
    timeout=30.0,                       # seconds per attempt, default
    max_retries=0,                      # default, see "Timeouts and retries"
    max_retry_delay=60.0,               # seconds, default
)

# Environment variable fallback
# Set AVATCADO_API_KEY=avat_live_... and omit the key:
avatcado = Avatcado()
```

The client also supports context managers for proper resource cleanup:

```python
with Avatcado("avat_live_...") as avatcado:
    result = avatcado.vat.validate("NL123456789B01")
```

## Type Hints

The package includes a `py.typed` marker (PEP 561) for full type checking support.

```python
from avatcado import (
    Avatcado,
    AsyncAvatcado,
    ValidateResponse,
    BatchValidateResponse,
    BatchResultSuccess,
    BatchResultError,
    Company,
    VatValidationResult,
    ResponseMeta,
    BatchItemMeta,
    SourceStatus,
    RateLimitInfo,
    VatRate,
    OtherRate,
    ListRatesResponse,
    GetRateResponse,
    BatchSummary,
    AsyncValidateResponse,
    AsyncBatchValidateResponse,
    AsyncBatchRejectedItem,
    EoriValidateResponse,
    EoriValidationResult,
    EoriResponseMeta,
    EoriSourceStatus,
    is_batch_success,
)
```

## Development

```bash
pip install -e ".[dev]"
pytest              # unit tests, HTTP mocked
ruff check . && black --check . && mypy src
```

`tests/test_live.py` runs the SDK against a real API in test mode. It is skipped unless a test key is set:

```bash
AVATCADO_TEST_API_KEY=avat_test_... pytest tests/test_live.py
```

Test keys use no quota and never reach a tax authority. Set `AVATCADO_BASE_URL` to point the suite at another host.

## Requirements

- Python >= 3.9
- [httpx](https://www.python-httpx.org/) >= 0.27 (sole runtime dependency)

## License

MIT
