# Changelog

## 0.7.0

EORI number checks, the `fallback` argument, opt-in retries, and fixes for request options the SDK could not send. No breaking changes; see "Changed" for two behaviours that differ from 0.6.0.

### Added

- `avatcado.eori.validate(eori_number, *, cache=None, request_id=None)` on `Avatcado` and `AsyncAvatcado`, for `GET /v1/eori/validate`. Checks one EORI number: GB with HMRC, the 27 EU member states and XI with the European Commission's EORI validation service. Returns `EoriValidateResponse` with `data` (`valid`, `eori_number`, `country_code`, `company`, `requested_at`), `meta` and `rate_limit`. `company` is `None` when the holder published no details
- `meta.source` is `"ec_eos"`, `"hmrc"` or `"test"`; `meta.source_status` is `"live"`, `"cached"` or `"unavailable"` (the register was down and a stored answer was served). Every `EoriResponseMeta` field except `request_id` is `None` when the server omits it
- `AvatcadoError.eori_number` (`Optional[str]`): the normalized EORI number echoed by the API on errors from `eori.validate()`. `None` on every other error
- Error code `invalid_eori_format` (HTTP 422) raises `ValidationError`
- New exports: `EoriValidateResponse`, `EoriValidationResult`, `EoriResponseMeta`, `EoriSourceStatus`
- `fallback` (`Optional[bool]`) on `vat.validate()`, `vat.validate_batch()`, `async_vat.validate()` and `async_vat.validate_batch()`. `False` stops a VIES outage from being answered by a national register; `True` next to `requester_vat_number` accepts a register answer. Pro and Business plans
- Opt-in retries: client arguments `max_retries` (default `0`, off) and `max_retry_delay` (default `60` seconds) on `Avatcado` and `AsyncAvatcado`. A burst-limit 429 and a 503 are retried on every method; a timeout, a network error, a 502 and a 504 on GET requests only. The SDK waits for `Retry-After`, otherwise 0.5 s doubling up to 8 s. See the README section "Timeouts and retries"
- `AvatcadoError.retry_after` (`Optional[float]`) on the base class and every subclass, not only `RateLimitError` and `UpstreamError`. The API also sends `Retry-After` on a 503 `internal_error`
- `rates.list()` and `rates.get()` accept `request_id`, sent as `X-Request-Id`
- `tests/test_live.py`: runs the SDK against a real API in test mode when `AVATCADO_TEST_API_KEY` is set
- CI workflow: ruff, black, mypy and pytest on Python 3.9 to 3.13 for every pull request

### Changed

- `cache` is now `Optional[bool] = None` on every method (it was `bool = True`), and an explicit `cache=True` is sent to the API. Before, `cache` was sent only when `False`, so the documented way to opt back in to cached and stored results next to `requester_vat_number` did nothing. Code that passes `cache=True` together with `requester_vat_number` now gets what it asked for: a cached result when one exists. Leaving `cache` unset is unchanged
- Keys with the legacy `vtly_live_` / `vtly_test_` prefix no longer trigger the "may indicate an invalid key" warning. The API accepts them permanently

### Fixed

- A `2xx` body that does not have the documented shape raises `AvatcadoError(code="parse_error")` with the HTTP status and request id, on every method. Before, `vat.validate()`, `vat.validate_batch()`, both `async_vat` methods and both `rates` methods raised a bare `KeyError` or `TypeError`, and `eori.validate()` reported `status_code` 0
- An error response without a JSON body (a gateway answering for the API) keeps `request_id` from the `X-Request-Id` header and `retry_after` from `Retry-After`. Both were dropped
- `retry_after` is `None` for a `Retry-After` header that is not a number of seconds or an HTTP date. `nan` and `inf` were accepted as numbers
- README: the national register list matches the API (`kas` and `vmi` never existed), `async_vat.validate_batch()` documents the flat shape of rejected items

## 0.6.0

Meta now reports which registry answered and distinguishes cache hits from national-registry fallback. Additive — no breaking changes.

- `SourceStatus` is widened from `live | unavailable | degraded` to `live | cached | unavailable | degraded | fallback`. `"cached"` marks a plain cache hit (previously reported with `source_status` omitted); `"fallback"` means VIES was down for that member state and the national register answered. The old alias made `meta.source_status == "fallback"` a non-overlapping comparison under mypy `--strict`
- `ResponseMeta` and `BatchItemMeta` gain `source`: the registry that produced the served data (`vies`, `hmrc`, `bfs`, `brreg`, `abr`, `test`, or a national registry id such as `anaf`, `ares`, `dgfip`, `kas`, `prh`, `vid`, `vmi` on fallback). It is a plain `Optional[str]`, not an enum, and `None` on responses from older API versions
- On current API responses `cached` and `stale` are always explicit booleans on `vat.validate()` results and batch success items, and `cached_at` is present exactly when `cached` is true. The batch envelope, rates and async responses never carry the source fields
- Fallback responses never carry a `consultation_number`, and `valid` there means domestic VAT registration; see the README "Source and fallback" section
- `BatchItemMeta` fields now all default to `None`, so `BatchItemMeta()` and `BatchItemMeta.from_dict({})` work (the shape `batch.completed` webhooks emit for rows recorded before the change)
- `BatchResultSuccess.from_dict` raises `AvatcadoError(code="parse_error")` instead of a bare `KeyError` when `data` is missing, and tolerates a missing or non-dict `meta`
- Positional parameter order is preserved: `source` is appended after the existing fields on both classes (it also appears in `repr()` / `dataclasses.asdict()` output)
- Test fixtures now mirror the real wire shape (optional fields omitted rather than `null`); explicit compatibility tests cover older-server responses

## 0.5.0

Error responses now echo the submitted VAT request context. Additive — no breaking changes.

- `AvatcadoError` (and every subclass) gains `vat_number` and `requester_vat_number`: the normalized VAT numbers from the failed request, echoed by the API on validation, rate-limit, upstream and server errors from the single-number validation endpoints (and on `tier_insufficient` / `webhook_not_configured` from the async endpoint). `None` on `unauthorized` / `forbidden` / `key_revoked`, on batch-level errors, when nothing was submitted, and on older API responses
- `UpstreamError` gains `validation_id`: the identifier of the recorded failed validation attempt (`upstream_unavailable` / `upstream_member_state_unavailable` only; never in test mode)
- `details` (list of `{"field", "message"}` dicts) is now part of the documented error schema for `validation_error` responses; its type is unchanged
- Batch: `BatchErrorDetail` gains `vat_number` (normalized), read from the item's `error.vat_number` with a fallback to `meta.vat_number` for older responses (the new field also appears in `repr()` / `dataclasses.asdict()` output)
- Batch: `BatchErrorMeta.vat_number` is **deprecated** — use `item.error.vat_number`. It remains populated (falling back to `error.vat_number` if the API omits it) and will be removed in a future major version
- All exception constructors keep their existing positional parameter order; the new parameters are trailing optionals
- Tests added for field-present, field-absent (older server) and batch fallback behaviour

## 0.4.0

Rebrand from **Vatly** to **Avatcado**. This is a **breaking change** — there are no backward-compatible aliases.

- Import package renamed: `import vatly` → `import avatcado`
- Distribution renamed on PyPI: `vatly` → `avatcado` (a new, separate project)
- Clients renamed: `Vatly` → `Avatcado`, `AsyncVatly` → `AsyncAvatcado`
- Exceptions/config renamed: `VatlyError` → `AvatcadoError`, `VatlyConfig` → `AvatcadoConfig`
  (subclasses `AuthenticationError`, `ValidationError`, `RateLimitError`, `UpstreamError` are unchanged)
- Environment variable renamed: `VATLY_API_KEY` → `AVATCADO_API_KEY`
- API key prefixes changed: `vtly_live_` / `vtly_test_` → `avat_live_` / `avat_test_`
- Default API base URL: `https://api.vatly.dev` → `https://api.avatcado.com`; docs at `https://docs.avatcado.com`
- User-Agent: `vatly-python/<version>` → `avatcado-python/<version>`

> Releases `0.1.0`–`0.3.0` below were published under the former `vatly` name; class/identifier names in those entries reflect the post-rebrand names for consistency.

## 0.3.0

Async validation support.

- `client.async_vat.validate()` and `client.async_vat.validate_batch()` on both `Avatcado` and `AsyncAvatcado`
- New types: `AsyncValidateData`, `AsyncMeta`, `AsyncValidateResponse`, `AsyncBatchRejectedItem`, `AsyncBatchData`, `AsyncBatchValidateResponse`
- Async validation requires a Pro or Business plan and a configured webhook URL

## 0.2.0

Type safety, robustness, and test coverage improvements.

- `is_batch_success()` now returns `TypeGuard[BatchResultSuccess]` for proper type narrowing
- `source_status` fields use `Literal["live", "unavailable", "degraded"]` instead of `str`
- `mode` field uses `Literal["test"]` instead of `str`
- New `SourceStatus` type alias exported for type annotations
- `from_dict` methods raise `AvatcadoError(code="parse_error")` with a descriptive message instead of raw `KeyError` on missing required fields
- Fixed quick start README example to handle `company` being `None`
- Added tests for batch network errors, non-JSON error responses, Content-Type header, async rates errors, forward-compatible deserialization, and missing required fields
- Removed unused test fixtures

## 0.1.0

Initial release.

- Sync client (`Avatcado`) and async client (`AsyncAvatcado`)
- `avatcado.vat.validate()` and `avatcado.vat.validate_batch()`
- `avatcado.rates.list()` and `avatcado.rates.get()`
- Typed exception hierarchy: `AvatcadoError`, `AuthenticationError`, `ValidationError`, `RateLimitError`, `UpstreamError`
- Full type annotations with `py.typed` marker
- API key resolution: explicit arg, `AVATCADO_API_KEY` env var
