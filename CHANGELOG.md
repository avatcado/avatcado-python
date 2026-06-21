# Changelog

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
