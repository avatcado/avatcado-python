# Changelog

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
