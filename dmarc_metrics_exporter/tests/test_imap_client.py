import io
from asyncio import IncompleteReadError

import pytest

from dmarc_metrics_exporter.imap_client import (
    ImapReader,
    IncompleteResponse,
    ResponseType,
)


class MockReader:
    def __init__(self, input_buf: bytes):
        self.reader = io.BytesIO(input_buf)
        self.eol_pos = self.reader.seek(0, io.SEEK_END)
        self.reader.seek(0, io.SEEK_SET)

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

    def at_eof(self) -> bool:
        return self.reader.tell() >= self.eol_pos


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "input_buf, expected",
    [
        (
            b"+ Ready for additional input\r\n",
            [(ResponseType.ContinueReq, b"Ready for additional input\r\n")],
        ),
        (
            b"* some untagged one line response\r\n",
            [(ResponseType.Untagged, b"some untagged one line response\r\n")],
        ),
        (
            (b"* some untagged {23}\r\n+ multiline\r\n* response\r\n"),
            [
                (
                    ResponseType.Untagged,
                    b"some untagged {23}\r\n+ multiline\r\n* response\r\n",
                )
            ],
        ),
        (
            b"tag123 OK some text\r\n",
            [(ResponseType.Tagged, b"tag123 OK some text\r\n")],
        ),
        (
            b"tag123 OK [FOO bar] some text\r\n",
            [(ResponseType.Tagged, b"tag123 OK [FOO bar] some text\r\n")],
        ),
        (
            b"tag123 OK [UIDNEXT 456] some text\r\n",
            [(ResponseType.Tagged, b"tag123 OK [UIDNEXT 456] some text\r\n")],
        ),
        (
            b"tag123 OK [BADCHARSET ({8}\r\nfoo\r\nbar)] some text\r\n",
            [
                (
                    ResponseType.Tagged,
                    b"tag123 OK [BADCHARSET ({8}\r\nfoo\r\nbar)] some text\r\n",
                )
            ],
        ),
        (
            (
                b"* some untagged {23}\r\n+ multiline\r\n* response\r\ntag123 OK some text\r\n"
            ),
            [
                (
                    ResponseType.Untagged,
                    b"some untagged {23}\r\n+ multiline\r\n* response\r\n",
                ),
                (ResponseType.Tagged, b"tag123 OK some text\r\n"),
            ],
        ),
    ],
)
async def test_imap_reader(input_buf, expected):
    imap_reader = ImapReader(MockReader(input_buf))
    for response in expected:
        assert await imap_reader.read_response() == response


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "input_buf",
    [
        b"tag123 INVALID foo\r\n",
        b"tag123 OK [BADCHARSET ({8}\r\n",
        b"+invalid OK foo\r\n",
        b"* cutoff {4}\r\n",
    ],
)
async def test_imap_reader_parse_error(input_buf):
    imap_reader = ImapReader(MockReader(input_buf))
    with pytest.raises(IncompleteResponse):
        await imap_reader.read_response()
