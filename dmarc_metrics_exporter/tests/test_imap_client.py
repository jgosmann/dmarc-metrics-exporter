import io
from asyncio import IncompleteReadError, wait_for

import pytest

from dmarc_metrics_exporter.imap_client import (
    ImapClient,
    ImapServerError,
    IncompleteResponse,
    ResponseType,
    parse_imap_responses,
)
from dmarc_metrics_exporter.tests.conftest import send_email
from dmarc_metrics_exporter.tests.sample_emails import create_minimal_email


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
    respone_generator = parse_imap_responses(MockReader(input_buf))
    actual = [response async for response in respone_generator]
    assert actual == expected


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
    respone_generator = parse_imap_responses(MockReader(input_buf))
    with pytest.raises(IncompleteResponse):
        await respone_generator.__anext__()


class TestImapClient:
    @pytest.mark.asyncio
    async def test_basic_connection(self, greenmail):
        async with ImapClient(greenmail.imap) as client:
            assert client.has_capability("IMAP4rev1")

    @pytest.mark.asyncio
    async def test_fetch(self, greenmail):
        await send_email(create_minimal_email(greenmail.imap.username), greenmail.smtp)
        async with ImapClient(greenmail.imap) as client:
            assert await client.select("INBOX") == 1
            await client.fetch(b"1:1", b"(BODY[HEADER.FIELDS (SUBJECT)])")
            fetched_email = await wait_for(client.fetched_queue.get(), 5)
            assert fetched_email[:2] == [1, "FETCH"]
            assert [
                value
                for key, value in fetched_email[2]
                if key[:2] == ["BODY", "HEADER.FIELDS"]
            ] == ["Subject: Minimal email\r\n"]

    @pytest.mark.asyncio
    async def test_create_delete(self, greenmail):
        async with ImapClient(greenmail.imap) as client:
            try:
                await client.delete("new mailbox")
            except ImapServerError:
                pass

            try:
                await client.create("new mailbox")
                assert await client.select("new mailbox") == 0
            finally:
                await client.select("INBOX")
                await client.delete("new mailbox")

            with pytest.raises(ImapServerError):
                await client.select("new mailbox")

    @pytest.mark.asyncio
    async def test_create_if_not_exists(self, greenmail):
        async with ImapClient(greenmail.imap) as client:
            try:
                await client.create_if_not_exists("new mailbox")
                await client.create_if_not_exists("new mailbox")
                assert await client.select("new mailbox") == 0
            finally:
                await client.select("INBOX")
                await client.delete("new mailbox")

    @pytest.mark.asyncio
    async def test_uid_copy(self, greenmail):
        await send_email(create_minimal_email(greenmail.imap.username), greenmail.smtp)
        async with ImapClient(greenmail.imap) as client:
            try:
                await client.create_if_not_exists("destination")
                assert await client.select("INBOX") == 1
                await client.fetch(b"1:1", b"(UID)")
                fetched_email = await wait_for(client.fetched_queue.get(), 5)
                assert fetched_email[:2] == [1, "FETCH"]
                uid = [value for key, value in fetched_email[2] if key == "UID"][0]
                await client.uid_copy(uid, "destination")
                assert await client.select("destination") == 1
            finally:
                await client.select("INBOX")
                await client.delete("destination")

    @pytest.mark.asyncio
    @pytest.mark.xfail(reason="Feature not supported by Greenmail.")
    async def test_uid_move(self, greenmail):
        await send_email(create_minimal_email(greenmail.imap.username), greenmail.smtp)
        async with ImapClient(greenmail.imap) as client:
            try:
                await client.create_if_not_exists("destination")
                assert await client.select("INBOX") == 1
                await client.fetch(b"1:1", b"(UID)")
                fetched_email = await wait_for(client.fetched_queue.get(), 5)
                assert fetched_email[:2] == [1, "FETCH"]
                uid = [value for key, value in fetched_email[2] if key == "UID"][0]
                await client.uid_move(uid, "destination")
                assert client.num_exists == 0
                assert await client.select("destination") == 1
            finally:
                await client.select("INBOX")
                await client.delete("destination")

    @pytest.mark.asyncio
    async def test_uid_move_graceful(self, greenmail):
        await send_email(create_minimal_email(greenmail.imap.username), greenmail.smtp)
        async with ImapClient(greenmail.imap) as client:
            try:
                await client.create_if_not_exists("destination")
                assert await client.select("INBOX") == 1
                await client.fetch(b"1:1", b"(UID)")
                fetched_email = await wait_for(client.fetched_queue.get(), 5)
                assert fetched_email[:2] == [1, "FETCH"]
                uid = [value for key, value in fetched_email[2] if key == "UID"][0]
                await client.uid_move_graceful(uid, "destination")
                assert client.num_exists == 0
                assert await client.select("destination") == 1
            finally:
                await client.select("INBOX")
                await client.delete("destination")

    @pytest.mark.asyncio
    async def test_uid_store(self, greenmail):
        await send_email(create_minimal_email(greenmail.imap.username), greenmail.smtp)
        async with ImapClient(greenmail.imap) as client:
            assert await client.select("INBOX") == 1
            await client.fetch(b"1:1", b"(UID)")
            fetched_email = await wait_for(client.fetched_queue.get(), 5)
            assert fetched_email[:2] == [1, "FETCH"]
            uid = [value for key, value in fetched_email[2] if key == "UID"][0]
            await client.uid_store(uid, rb"+FLAGS (\Deleted)")

            fetched_email = await wait_for(client.fetched_queue.get(), 5)
            assert fetched_email[:2] == [1, "FETCH"]
            assert [value for key, value in fetched_email[2] if key == "FLAGS"][
                0
            ].as_list() == ["\\Deleted"]

    @pytest.mark.asyncio
    async def test_uid_expunge(self, greenmail):
        await send_email(create_minimal_email(greenmail.imap.username), greenmail.smtp)
        async with ImapClient(greenmail.imap) as client:
            assert await client.select("INBOX") == 1
            await client.fetch(b"1:1", b"(UID)")
            fetched_email = await wait_for(client.fetched_queue.get(), 5)
            assert fetched_email[:2] == [1, "FETCH"]
            uid = [value for key, value in fetched_email[2] if key == "UID"][0]
            await client.uid_store(uid, rb"+FLAGS (\Deleted)")
            await client.expunge()
            assert client.num_exists == 0
