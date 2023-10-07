from unittest.mock import MagicMock

import pytest


class AsyncMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)


@pytest.fixture
def mock_transport():
    return AsyncMock()
