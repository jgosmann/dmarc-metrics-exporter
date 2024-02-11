import asyncio
import io
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
from typing import Callable, Coroutine, Dict, List, Optional

import pytest
import structlog

from dmarc_metrics_exporter.imap_client import (
    ConnectionConfig,
    ImapClient,
    ImapServerError,
)
from dmarc_metrics_exporter.tests.conftest import send_email, try_until_success
from dmarc_metrics_exporter.tests.sample_emails import create_minimal_email

logger = structlog.get_logger()


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
async def test_basic_connection(greenmail):
    async with ImapClient(greenmail.imap) as client:
        assert client.has_capability("IMAP4rev1")


@pytest.mark.asyncio
async def test_fetch(greenmail):
    await send_email(create_minimal_email(greenmail.imap.username), greenmail.smtp)
    async with ImapClient(greenmail.imap) as client:
        assert await client.select("INBOX") == 1
        await client.fetch(b"1:1", b"(BODY[HEADER.FIELDS (SUBJECT)])")
        fetched_email = await wait_for(client.fetched_queue.get(), 5)
        assert fetched_email[:2] == (1, b"FETCH")
        assert [
            item[2]
            for item in fetched_email[2]
            if item[:2] == (b"BODY", (b"HEADER.FIELDS", (b"SUBJECT",)))
        ] == [b"Subject: Minimal email\r\n"]


@pytest.mark.asyncio
async def test_fetch_non_ascii_chars(greenmail):
    await send_email(
        create_minimal_email(greenmail.imap.username, "üüüü"),
        greenmail.smtp,
    )
    async with ImapClient(greenmail.imap) as client:
        assert await client.select("INBOX") == 1
        await client.fetch(b"1:1", b"(RFC822)")
        fetched_email = await wait_for(client.fetched_queue.get(), 5)
        assert fetched_email[:2] == (1, b"FETCH")
        body = next(value for key, value in fetched_email[2] if key == b"RFC822")
        assert body.endswith("üüüü".encode("utf-8"))


@pytest.mark.asyncio
async def test_create_delete(greenmail):
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
async def test_create_if_not_exists(greenmail):
    async with ImapClient(greenmail.imap) as client:
        try:
            await client.create_if_not_exists("new mailbox")
            await client.create_if_not_exists("new mailbox")
            assert await client.select("new mailbox") == 0
        finally:
            await client.select("INBOX")
            await client.delete("new mailbox")


@pytest.mark.asyncio
async def test_uid_copy(greenmail):
    await send_email(create_minimal_email(greenmail.imap.username), greenmail.smtp)
    async with ImapClient(greenmail.imap) as client:
        try:
            await client.create_if_not_exists("destination")
            assert await client.select("INBOX") == 1
            await client.fetch(b"1:1", b"(UID)")
            fetched_email = await wait_for(client.fetched_queue.get(), 5)
            assert fetched_email[:2] == (1, b"FETCH")
            uid = [value for key, value in fetched_email[2] if key == b"UID"][0]
            await client.uid_copy(uid, "destination")
            assert await client.select("destination") == 1
        finally:
            await client.select("INBOX")
            await client.delete("destination")


@pytest.mark.asyncio
async def test_uid_move(greenmail):
    await send_email(create_minimal_email(greenmail.imap.username), greenmail.smtp)
    async with ImapClient(greenmail.imap) as client:
        try:
            await client.create_if_not_exists("destination")
            assert await client.select("INBOX") == 1
            await client.fetch(b"1:1", b"(UID)")
            fetched_email = await wait_for(client.fetched_queue.get(), 5)
            assert fetched_email[:2] == (1, b"FETCH")
            uid = [value for key, value in fetched_email[2] if key == b"UID"][0]
            await client.uid_move(uid, "destination")
            assert client.num_exists == 0
            assert await client.select("destination") == 1
        finally:
            await client.select("INBOX")
            await client.delete("destination")


@pytest.mark.asyncio
async def test_uid_move_graceful(greenmail):
    await send_email(create_minimal_email(greenmail.imap.username), greenmail.smtp)
    async with ImapClient(greenmail.imap) as client:
        try:
            await client.create_if_not_exists("destination")
            assert await client.select("INBOX") == 1
            await client.fetch(b"1:1", b"(UID)")
            fetched_email = await wait_for(client.fetched_queue.get(), 5)
            assert fetched_email[:2] == (1, b"FETCH")
            uid = [value for key, value in fetched_email[2] if key == b"UID"][0]
            await client.uid_move_graceful(uid, "destination")
            assert client.num_exists == 0
            assert await client.select("destination") == 1
        finally:
            await client.select("INBOX")
            await client.delete("destination")


@pytest.mark.asyncio
async def test_uid_store(greenmail):
    await send_email(create_minimal_email(greenmail.imap.username), greenmail.smtp)
    async with ImapClient(greenmail.imap) as client:
        assert await client.select("INBOX") == 1
        await client.fetch(b"1:1", b"(UID)")
        fetched_email = await wait_for(client.fetched_queue.get(), 5)
        assert fetched_email[:2] == (1, b"FETCH")
        uid = [value for key, value in fetched_email[2] if key == b"UID"][0]
        await client.uid_store(uid, rb"+FLAGS (\Deleted)")

        fetched_email = await wait_for(client.fetched_queue.get(), 5)
        assert fetched_email[:2] == (1, b"FETCH")
        assert [value for key, value in fetched_email[2] if key == b"FLAGS"][0] == (
            b"\\Deleted",
        )


@pytest.mark.asyncio
async def test_uid_expunge(greenmail):
    await send_email(create_minimal_email(greenmail.imap.username), greenmail.smtp)
    async with ImapClient(greenmail.imap) as client:
        assert await client.select("INBOX") == 1
        await client.fetch(b"1:1", b"(UID)")
        fetched_email = await wait_for(client.fetched_queue.get(), 5)
        assert fetched_email[:2] == (1, b"FETCH")
        uid = [value for key, value in fetched_email[2] if key == b"UID"][0]
        await client.uid_store(uid, rb"+FLAGS (\Deleted)")
        await client.expunge()
        assert client.num_exists == 0


@pytest.mark.asyncio
async def test_executes_same_command_type_sequentially():
    continue_triggers_change = Condition()
    continue_triggers = []

    async def select_handler(_: StreamWriter):
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
async def test_executes_different_commands_in_parallel():
    continue_fetch = Event()
    continue_store = Event()
    num_commands_received_condition = Condition()
    num_commands_received = 0
    log = logger.bind(logger="test_executes_different_commands_in_parallel")

    async def fetch_handler(_: StreamWriter):
        nonlocal num_commands_received
        await log.adebug("fetch handle")
        async with num_commands_received_condition:
            num_commands_received += 1
            num_commands_received_condition.notify_all()
        await continue_fetch.wait()

    async def store_handler(_: StreamWriter):
        nonlocal num_commands_received
        await log.adebug("store handle")
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


@pytest.mark.asyncio
async def test_timeout_behavior_waiting_for_server_ready():
    event = Event()

    async def client_connected_cb(reader: StreamReader, writer: StreamWriter):
        await event.wait()
        writer.close()

    server = await start_server(client_connected_cb, host="localhost", port=4143)

    async def connect():
        try:
            async with ImapClient(
                ConnectionConfig(
                    "username",
                    "password",
                    host="localhost",
                    port=4143,
                    use_ssl=False,
                ),
                timeout_seconds=0.2,
            ):
                pass
        except asyncio.TimeoutError:
            pass

    async with server:
        await asyncio.wait_for(connect(), timeout=1)
        event.set()


@pytest.mark.asyncio
async def test_command_timeout_no_response_at_all():
    async def select_handler():
        return True

    async with MockImapServer(
        host="localhost",
        port=4143,
        command_handlers={b"SELECT": select_handler},
    ) as mock_server:
        async with ImapClient(
            mock_server.connection_config,
            timeout_seconds=0.2,
        ) as client:

            async def run_command():
                try:
                    await client.select()
                except asyncio.TimeoutError:
                    pass

        await asyncio.wait_for(run_command(), timeout=1)


@pytest.mark.asyncio
async def test_command_timeout_single_untagged_response_only():
    async def select_handler(writer: StreamWriter):
        writer.write(b"* 42 EXISTS\r\n")
        await writer.drain()
        return True

    async with MockImapServer(
        host="localhost",
        port=4143,
        command_handlers={b"SELECT": select_handler},
    ) as mock_server:
        async with ImapClient(
            mock_server.connection_config,
            timeout_seconds=0.2,
        ) as client:

            async def run_command():
                try:
                    await client.select()
                except asyncio.TimeoutError:
                    pass

        await asyncio.wait_for(run_command(), timeout=1)


@pytest.mark.asyncio
async def test_command_not_timing_out_if_interresponse_time_stays_below_threshold():
    async def select_handler(writer: StreamWriter):
        await asyncio.sleep(0.1)
        writer.write(b"* 42 EXISTS\r\n")
        await writer.drain()
        await asyncio.sleep(0.1)
        writer.write(b"* 42 RECENT\r\n")
        await writer.drain()
        await asyncio.sleep(0.1)
        writer.write(b"* OK UNSEEN 23\r\n")
        await writer.drain()
        await asyncio.sleep(0.1)

    async with MockImapServer(
        host="localhost",
        port=4143,
        command_handlers={b"SELECT": select_handler},
    ) as mock_server:
        async with ImapClient(
            mock_server.connection_config,
            timeout_seconds=0.2,
        ) as client:
            assert await client.select() == 42


class MockImapServer:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 4143,
        command_handlers: Optional[
            Dict[bytes, Callable[[StreamWriter], Coroutine]]
        ] = None,
    ):
        self.host = host
        self.port = port
        self.command_handlers = command_handlers or {}
        self._server = None
        self._write_lock = asyncio.Lock()
        self._tasks: List[asyncio.Task] = []
        self._log = logger.bind(logger=self.__class__.__name__)

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
            await self._log.adebug("MockImapServer received line.", line=line)
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

            self._tasks.append(
                asyncio.create_task(self._finish_command_handling(tag, command, writer))
            )

        await asyncio.gather(*self._tasks)
        writer.close()

    async def _finish_command_handling(
        self, tag: bytes, command: bytes, writer: StreamWriter
    ):
        handled = False
        suppress_tagged_response = False
        if command in self.command_handlers:
            handled = True
            suppress_tagged_response = await self.command_handlers[command](writer)

        async with self._write_lock:
            if handled:
                pass
            elif command == b"CAPABILITY":
                writer.write(b"* CAPABILITY IMAP4rev1\r\n")
            elif command == b"LOGOUT":
                writer.write(b"* BYE see you soon\r\n")

            if not suppress_tagged_response:
                writer.write(b" ".join((tag, b"OK", command, b"completed\r\n")))
                if command == b"LOGOUT":
                    writer.write_eof()
            await writer.drain()
