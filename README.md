# avatcado

Official Python SDK for the [Avatcado](https://avatcado.com) VAT validation API. Validate EU, UK, Swiss, Norwegian, and Australian VAT/GST numbers and look up VAT rates by country. See the full [API reference](https://docs.avatcado.com/api-reference).

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
    cache=False,                          # optional, bypass 25-day cache
    request_id="my-trace-id",            # optional, for request tracing
)

print(result.data.valid)              # True
print(result.data.vat_number)         # "NL123456789B01"
print(result.data.country_code)       # "NL"
print(result.data.company.name)       # "Example BV"
print(result.data.company.address)    # "Amsterdam, Netherlands" or None
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

`meta.source` names the registry that produced the served data: `vies`, `hmrc`, `bfs`, `brreg`, `abr`, or `test` in test mode. When VIES is down for a member state, the API consults that country's national register before falling back to stale cache; `source` then names the register (`anaf`, `ares`, `dgfip`, `kas`, `prh`, `vid`, `vmi`) and `source_status` is `"fallback"`. `source` is a plain string, not an enum.

| Scenario | `source_status` | `cached` | `stale` | `cached_at` |
|---|---|---|---|---|
| Fresh upstream result | `"live"` | `False` | `False` | `None` |
| Cache hit (within 25-day TTL) | `"cached"` | `True` | `False` | set |
| Upstream down, cached row within TTL served | `"unavailable"` | `True` | `False` | set |
| Upstream down, row beyond TTL served | `"unavailable"` | `True` | `True` | set |
| VIES returned a suspected false negative, prior row served | `"degraded"` | `True` | varies | set |
| VIES down, national register answered | `"fallback"` | `False` | `False` | `None` |

Fallback responses never carry a `consultation_number` (national registers cannot issue one, even with `requester_vat_number`), and `valid` there means the number is registered for domestic VAT; for Poland an active (`Czynny`) taxpayer is valid even without VAT-UE registration. Lithuania (`vmi`) and Latvia (`vid`) return the company name only, so `company.address` is `None`. Fallback and stale responses count toward your quota because data was served; only `503` upstream errors are refunded. API versions that predate these fields omit them, in which case they are `None`.

### `avatcado.vat.validate_batch()`

Validate up to 50 VAT numbers in a single request.

```python
from avatcado import is_batch_success

result = avatcado.vat.validate_batch(
    ["NL123456789B01", "DE987654321", "XX000"],
    requester_vat_number="DE987654321",  # optional
    cache=False,                          # optional
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

> `item.meta.vat_number` is deprecated as of 0.5.0 — use `item.error.vat_number`. It remains populated for backward compatibility.

### `avatcado.async_vat.validate()`

Submit a VAT number for async validation. Results are delivered via [webhook](https://docs.avatcado.com/webhooks). Requires a Pro or Business plan and a configured webhook URL.

```python
# Sync client
response = client.async_vat.validate("DE123456789")
print(response.data.request_id)  # Track this ID
print(response.data.status)      # "pending"

# Async client
response = await client.async_vat.validate("DE123456789")
```

### `avatcado.async_vat.validate_batch()`

Submit multiple VAT numbers for async validation.

```python
response = client.async_vat.validate_batch(
    ["DE123456789", "NL987654321B01"],
    requester_vat_number="NL987654321B01",  # optional
)
print(response.data.batch_id)   # Track this ID
print(response.data.accepted)   # Number queued
print(response.data.rejected)   # Items with invalid format
```

### `avatcado.rates.list()`

List VAT rates for all supported countries.

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
| `ValidationError` | `invalid_vat_format`, `missing_parameter`, `validation_error`, `invalid_json` |
| `RateLimitError` | `rate_limit_exceeded`, `burst_limit_exceeded` |
| `UpstreamError` | `upstream_unavailable`, `upstream_member_state_unavailable` |
| `AvatcadoError` | Base class for all errors, including `timeout`, `network_error`, `parse_error`, `internal_error`, `key_limit_reached` |

### Error Properties

```python
e.message               # Human-readable message
e.code                  # Machine-readable code (e.g. "unauthorized", "rate_limit_exceeded")
e.status_code           # HTTP status (0 for network/timeout errors)
e.request_id            # Request ID (string or None)
e.docs_url              # Link to error documentation (string, empty if not provided)
e.details               # Validation details: list of {"field": ..., "message": ...} dicts, or None
e.vat_number            # Normalized VAT number from the failed request (string or None)
e.requester_vat_number  # Normalized requester VAT number from the request (string or None)
```

`vat_number` and `requester_vat_number` are echoed by the API on validation, rate-limit, upstream and server errors from the single-number validation endpoints (`vat.validate()`, `async_vat.validate()`), including `tier_insufficient` and `webhook_not_configured` from the async endpoint. They are `None` when the API rejected the request before reading it (`unauthorized`, `forbidden`, `key_revoked`), on batch-level errors (per-item batch errors carry `item.error.vat_number` instead), when no VAT number was submitted, and on responses from API versions that predate these fields.

`UpstreamError` additionally exposes `e.validation_id` (string or None): the identifier of the recorded failed validation attempt. It is present only for `upstream_unavailable` / `upstream_member_state_unavailable` and never in test mode.

### Retries

The SDK does not retry automatically. `RateLimitError` and `UpstreamError` include a `retry_after` property (seconds) when the server provides one.

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

See the [test mode docs](https://docs.avatcado.com/test-mode) for the full list of magic numbers.

## Configuration

```python
# String API key
avatcado = Avatcado("avat_live_...")

# Keyword arguments
avatcado = Avatcado(
    api_key="avat_live_...",
    base_url="https://api.avatcado.com",  # default
    timeout=30.0,                       # seconds, default
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
    is_batch_success,
)
```

## Requirements

- Python >= 3.9
- [httpx](https://www.python-httpx.org/) >= 0.27 (sole runtime dependency)

## License

MIT
