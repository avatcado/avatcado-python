from __future__ import annotations

from avatcado import AsyncAvatcado, Avatcado
from avatcado._async_resources.rates import AsyncRatesResource
from avatcado._async_resources.vat import AsyncVatResource
from avatcado._resources.rates import RatesResource
from avatcado._resources.vat import VatResource


class TestSyncClient:
    def test_has_vat_resource(self) -> None:
        client = Avatcado("avat_live_key")
        assert isinstance(client.vat, VatResource)
        client.close()

    def test_has_rates_resource(self) -> None:
        client = Avatcado("avat_live_key")
        assert isinstance(client.rates, RatesResource)
        client.close()

    def test_context_manager(self) -> None:
        with Avatcado("avat_live_key") as client:
            assert client.vat is not None
            assert client.rates is not None

    def test_close(self) -> None:
        client = Avatcado("avat_live_key")
        client.close()


class TestAsyncClient:
    def test_has_vat_resource(self) -> None:
        client = AsyncAvatcado("avat_live_key")
        assert isinstance(client.vat, AsyncVatResource)

    def test_has_rates_resource(self) -> None:
        client = AsyncAvatcado("avat_live_key")
        assert isinstance(client.rates, AsyncRatesResource)

    async def test_async_context_manager(self) -> None:
        async with AsyncAvatcado("avat_live_key") as client:
            assert client.vat is not None
            assert client.rates is not None

    async def test_close(self) -> None:
        client = AsyncAvatcado("avat_live_key")
        await client.close()
