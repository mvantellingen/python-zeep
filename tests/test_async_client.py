import pytest

from zeep import AsyncClient


@pytest.mark.requests
@pytest.mark.asyncio
async def test_context_manager():
    async with AsyncClient("tests/wsdl_files/soap.wsdl") as cli:
        assert cli
