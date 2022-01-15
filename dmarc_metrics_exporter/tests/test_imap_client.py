import io
from asyncio import IncompleteReadError

import pytest

from dmarc_metrics_exporter.imap_client import ImapReader, ResponseType


class MockReader:
    def __init__(self, input_buf: bytes):
        self.reader = io.BytesIO(input_buf)

    async def read(self, n=-1) -> bytes:
        return self.reader.read(n)

    async def readline(self) -> bytes:
        return self.reader.readline()

    async def readexactly(self, n) -> bytes:
        buf = await self.read(n)
        if len(buf) < n:
            raise IncompleteReadError(buf, n)
        return buf

    async def readuntil(self, separator=b"\n") -> bytes:
        raise NotImplementedError()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "input_buf, expected",
    [
        (
            b"+ Ready for additional input\r\n",
            [(ResponseType.ContinueReq, b"Ready for additional input\r\n")],
        )
    ],
)
async def test_imap_reader(input_buf, expected):
    imap_reader = ImapReader(MockReader(input_buf))
    for response in expected:
        assert await imap_reader.read_response() == response
