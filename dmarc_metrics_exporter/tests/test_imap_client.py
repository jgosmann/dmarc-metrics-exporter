import asyncio
import io
import logging
import re
from asyncio import (
    Condition,
    Event,
    IncompleteReadError,
    StreamReader,
    StreamWriter,
    create_task,
    start_server,
    wait_for,
)
from typing import Callable, Coroutine, Dict

import pytest

from dmarc_metrics_exporter.imap_client import (
    ConnectionConfig,
    ImapClient,
    ImapServerError,
    IncompleteResponse,
    ResponseType,
    parse_imap_responses,
)
from dmarc_metrics_exporter.tests.conftest import send_email, try_until_success
from dmarc_metrics_exporter.tests.sample_emails import create_minimal_email

logger = logging.getLogger(__name__)


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
    @pytest.mark.xfail(reason="Feature not supported by Greenmail.", run=False)
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

    @pytest.mark.asyncio
    async def test_executes_same_command_type_sequentially(self):
        continue_triggers_change = Condition()
        continue_triggers = []

        async def select_handler():
            continue_event = Event()
            async with continue_triggers_change:
                continue_triggers.append(continue_event)
                continue_triggers_change.notify_all()
            await continue_event.wait()

        async with MockImapServer(
            host="localhost", port=4143, command_handlers={b"SELECT": select_handler}
        ) as mock_server:
            async with ImapClient(mock_server.connection_config) as client:
                select_tasks = [
                    create_task(client.select("INBOX")),
                    create_task(client.select("foo")),
                ]
                async with continue_triggers_change:
                    await asyncio.wait_for(
                        continue_triggers_change.wait_for(
                            lambda: len(continue_triggers) >= 1
                        ),
                        timeout=5,
                    )
                assert len(continue_triggers) == 1
                continue_triggers[0].set()
                # Lambda required because list access must be revaluated each time
                # pylint: disable=unnecessary-lambda
                await try_until_success(lambda: continue_triggers[1].set())
                await asyncio.gather(*select_tasks)

    @pytest.mark.asyncio
    async def test_executes_different_commands_in_parallel(self):
        continue_fetch = Event()
        continue_store = Event()
        num_commands_received_condition = Condition()
        num_commands_received = 0

        async def fetch_handler():
            nonlocal num_commands_received
            logger.debug("fetch handle")
            async with num_commands_received_condition:
                num_commands_received += 1
                num_commands_received_condition.notify_all()
            await continue_fetch.wait()

        async def store_handler():
            nonlocal num_commands_received
            logger.debug("store handle")
            async with num_commands_received_condition:
                num_commands_received += 1
                num_commands_received_condition.notify_all()
            await continue_store.wait()

        async with MockImapServer(
            host="localhost",
            port=4143,
            command_handlers={b"FETCH": fetch_handler, b"UID": store_handler},
        ) as mock_server:
            async with ImapClient(mock_server.connection_config) as client:
                await client.select("INBOX")
                tasks = [
                    create_task(client.fetch(b"1", b"(UID)")),
                    create_task(client.uid_store(123, rb"+FLAGS (\Seen)")),
                ]
                async with num_commands_received_condition:
                    await asyncio.wait_for(
                        num_commands_received_condition.wait_for(
                            lambda: num_commands_received >= 2
                        ),
                        timeout=5,
                    )
                continue_store.set()
                continue_fetch.set()
                await asyncio.gather(*tasks)


class MockImapServer:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 4143,
        command_handlers: Dict[bytes, Callable[[], Coroutine]] = None,
    ):
        self.host = host
        self.port = port
        self.command_handlers = command_handlers or {}
        self._server = None
        self._write_lock = asyncio.Lock()

    @property
    def connection_config(self) -> ConnectionConfig:
        return ConnectionConfig(
            "username", "password", self.host, self.port, use_ssl=False
        )

    async def __aenter__(self):
        self._server = await start_server(
            self._client_connected_cb, host="localhost", port=4143
        )
        await self._server.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return await self._server.__aexit__(exc_type, exc, traceback)

    async def _client_connected_cb(self, reader: StreamReader, writer: StreamWriter):
        writer.write(b"* OK hello\r\n")
        await writer.drain()

        while not reader.at_eof():
            line = await reader.readline()
            logger.debug("MockImapServer received: %s", line)
            parsed = re.match(
                rb"^(?P<tag>\w+)\s+(?P<command>\w+)(?P<remainder>.*)$", line
            )
            if not parsed:
                continue
            tag, command, remainder = (
                parsed.group("tag"),
                parsed.group("command"),
                parsed.group("remainder") + b"\n",
            )
            async with self._write_lock:
                while remainder.endswith(b"}\r\n"):
                    writer.write(b"+ OK continue\r\n")
                    await writer.drain()
                    remainder += await reader.readline()

            asyncio.create_task(self._finish_command_handling(tag, command, writer))

    async def _finish_command_handling(
        self, tag: bytes, command: bytes, writer: StreamWriter
    ):
        handled = False
        if command in self.command_handlers:
            handled = True
            await self.command_handlers[command]()

        async with self._write_lock:
            if handled:
                pass
            elif command == b"CAPABILITY":
                writer.write(b"* CAPABILITY IMAP4rev1\r\n")
            elif command == b"LOGOUT":
                writer.write(b"* BYE see you soon\r\n")
            writer.write(b" ".join((tag, b"OK", command, b"completed\r\n")))

            if command == b"LOGOUT":
                writer.write_eof()
            await writer.drain()
