import asyncio
import contextlib
import itertools
import ssl
import time
from asyncio import (
    Event,
    Lock,
    Queue,
    StreamReader,
    StreamWriter,
    create_task,
    open_connection,
    wait_for,
)
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Coroutine, Dict, FrozenSet, Literal, Optional, Union

import structlog
from bite import parse_incremental
from bite.parsers import ParsedNode

from .imap_parser import response as response_grammar

logger = structlog.get_logger()


@dataclass
class ConnectionConfig:
    username: str
    password: str
    host: str = "localhost"
    port: int = 993
    use_ssl: bool = True
    verify_certificate: bool = True
    tls_maximum_version: ssl.TLSVersion = ssl.TLSVersion.MAXIMUM_SUPPORTED

    def create_ssl_context(self) -> Union[Literal[False], ssl.SSLContext]:
        if self.use_ssl:
            ssl_context = ssl.create_default_context()
            if not self.verify_certificate:
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
            ssl_context.maximum_version = self.tls_maximum_version
            return ssl_context
        else:
            return False


class ImapError(Exception):
    pass


class IncompleteResponse(ImapError):
    pass


class ResponseType(Enum):
    CONTINUE_REQ = "+"
    UNTAGGED = "*"
    TAGGED = "tagged"


class _ImapTag:
    state: Optional[bytes]
    text: Optional[bytes]

    def __init__(self, name: bytes):
        self.name = name
        self._response_received = Event()
        self.state = None
        self.text = None

    async def wait_response(self):
        await self._response_received.wait()

    def has_response(self) -> bool:
        return self._response_received.is_set()

    def set_response(self, state: bytes, text: bytes):
        logger.debug(
            "IMAP command completed with ",
            command=self.name,
            state=state,
            state_description=text,
            logger=ImapClient.__name__,
        )
        self.state = state
        self.text = text
        self._response_received.set()


class _ImapCommandWriter:
    def __init__(self, writer: StreamWriter, server_ready: Event, timeout_seconds: int):
        self.writer = writer
        self._server_ready = server_ready
        self.timeout_seconds = timeout_seconds

    async def _drain(self):
        await asyncio.wait_for(self.writer.drain(), timeout=self.timeout_seconds)

    async def write_raw(self, buf: bytes):
        self.writer.write(buf)
        await self._drain()

    async def write_int(self, num: int):
        self.writer.write(str(num).encode("ascii"))
        await self._drain()

    async def write_string_literal(self, string: str):
        encoded = string.encode("utf-8")
        self._server_ready.clear()
        await self.write_raw(b"{" + str(len(encoded)).encode("ascii") + b"}\r\n")
        await self._server_ready.wait()

        await self.write_raw(encoded)


class _CommandsInUse:
    def __init__(self):
        self._in_use = set()
        self._change_condition = asyncio.Condition()

    async def acquire(self, name: str):
        async with self._change_condition:
            await self._change_condition.wait_for(lambda: name not in self._in_use)
            self._in_use.add(name)

    async def release(self, name: str):
        async with self._change_condition:
            self._in_use.remove(name)
            self._change_condition.notify_all()


# pylint: disable=too-many-instance-attributes
class ImapClient:
    num_exists: Optional[int]
    fetched_queue: Queue
    _capabilities: FrozenSet[str]
    _tag_completions: Dict[bytes, _ImapTag]

    def __init__(self, connection: ConnectionConfig, timeout_seconds: int = 10):
        self.connection = connection
        self.timeout_seconds = timeout_seconds
        self.num_exists = None
        self.fetched_queue = Queue()
        self._last_response = time.time()
        self._capabilities = frozenset()
        self._ongoing_commands = _CommandsInUse()
        self._command_lock = Lock()
        self._server_ready = Event()
        self._process_responses_task = None
        self._writer = None
        self._tag_gen = (f"a{i}".encode("ascii") for i in itertools.count())
        self._tag_completions = {}
        self._log = logger.bind(logger=self.__class__.__name__)

    async def __aenter__(self):
        reader, self._writer = await open_connection(
            self.connection.host,
            self.connection.port,
            ssl=self.connection.create_ssl_context(),
        )
        self._process_responses_task = create_task(self._process_responses(reader))

        try:
            await wait_for(self._server_ready.wait(), self.timeout_seconds)
            await self._log.adebug("IMAP server ready.")
            await self._capability()
            await self._login(self.connection.username, self.connection.password)
        except:
            self._process_responses_task.cancel()
            raise
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        if not self._writer.is_closing():
            await self._log.adebug("Logging out.", timeout=self.timeout_seconds)
            with contextlib.suppress(asyncio.TimeoutError):
                await wait_for(self._logout(), self.timeout_seconds)
            self._writer.close()
            await asyncio.gather(
                self._log.adebug("Waiting for writer to be closed."),
                self._writer.wait_closed(),
            )
        await asyncio.gather(
            self._log.adebug("Processing remaining responses after connection close."),
            self._process_responses_task,
        )
        self._server_ready.clear()
        await self._log.adebug("Connection closed.")

    async def _process_responses(self, reader: StreamReader):
        try:
            async for parse_tree in parse_incremental(response_grammar, reader):
                response = parse_tree.values
                await self._log.adebug("IMAP response.", response=response)

                self._last_response = time.time()

                if response[0] == b"+":
                    self._server_ready.set()
                elif response[0] == b"*":
                    await self._process_untagged_response(response)
                else:
                    tag_name, state, text = response[0:3]
                    self._tag_completions[tag_name].set_response(state, text)
            await self._log.adebug("End of response stream.")
        except Exception:  # pylint: disable=broad-except
            await self._log.aexception("Error while processing server responses.")
            for tag_completion in self._tag_completions.values():
                if not tag_completion.has_response():
                    tag_completion.set_response(b"NO", b"")

    async def _process_untagged_response(self, response: ParsedNode):
        if response[1] == b"OK":
            self._server_ready.set()
        elif response[1] == b"CAPABILITY":
            await self._log.adebug(
                "IMAP server reported capabilities.", capabilities=response[2]
            )
            self._capabilities = frozenset(
                c.strip().upper() for c in response[2].decode("utf-8").split(" ")
            )
        elif len(response) >= 3 and response[2] == b"EXISTS":
            self.num_exists = response[1]
        elif len(response) >= 3 and response[2] == b"EXPUNGE":
            if self.num_exists is not None:
                self.num_exists -= 1
        elif len(response) >= 3 and response[2] == b"FETCH":
            await self.fetched_queue.put(response[1:])
        else:
            await self._log.adebug(
                "Ignored untagged IMAP response.", response=response[1]
            )

    async def _command(
        self, name: str, write_command: Callable[[_ImapCommandWriter], Coroutine]
    ):
        assert self._writer
        tag = _ImapTag(next(self._tag_gen))
        self._tag_completions[tag.name] = tag
        wait_response = asyncio.ensure_future(tag.wait_response())
        try:
            await self._ongoing_commands.acquire(name)

            async with self._command_lock:
                self._writer.write(tag.name)
                self._writer.write(b" ")
                cmd_writer = _ImapCommandWriter(
                    self._writer, self._server_ready, self.timeout_seconds
                )
                _, pending = await asyncio.wait(
                    [asyncio.ensure_future(write_command(cmd_writer)), wait_response],
                    return_when=asyncio.FIRST_COMPLETED,
                )

            while not wait_response.done():
                _, pending = await asyncio.wait(
                    [wait_response], timeout=self.timeout_seconds
                )
                if (
                    not wait_response.done()
                    and self.timeout_seconds < time.time() - self._last_response
                ):
                    for future in pending:
                        future.cancel()
                    raise asyncio.TimeoutError("Waiting for response timed out.")

            if tag.state and not tag.state.upper() == b"OK":
                raise ImapServerError(name, tag.state, tag.text)
        finally:
            del self._tag_completions[tag.name]
            if not wait_response.done():
                wait_response.cancel()
            await self._ongoing_commands.release(name)

    async def _login(self, username: str, password: str):
        async def login_writer(cmd_writer: _ImapCommandWriter):
            await cmd_writer.write_raw(b"LOGIN ")
            await cmd_writer.write_string_literal(username)
            await cmd_writer.write_raw(b" ")
            await cmd_writer.write_string_literal(password)
            await cmd_writer.write_raw(b"\r\n")

        await self._command("LOGIN", login_writer)

    async def _logout(self):
        async def logout_writer(cmd_writer: _ImapCommandWriter):
            await cmd_writer.write_raw(b"LOGOUT\r\n")

        await self._command("LOGOUT", logout_writer)

    async def _capability(self):
        async def capability_writer(cmd_writer: _ImapCommandWriter):
            await cmd_writer.write_raw(b"CAPABILITY\r\n")

        await self._command("CAPABILITY", capability_writer)

    def has_capability(self, capability: str) -> bool:
        return capability.upper() in self._capabilities

    async def select(self, mailbox: str = "INBOX") -> Optional[int]:
        async def select_writer(cmd_writer: _ImapCommandWriter):
            await cmd_writer.write_raw(b"SELECT ")
            await cmd_writer.write_string_literal(mailbox)
            await cmd_writer.write_raw(b"\r\n")

        await self._command("SELECT", select_writer)
        return self.num_exists

    async def fetch(self, sequence_set: bytes, attrs: bytes):
        async def fetch_writer(cmd_writer: _ImapCommandWriter):
            await cmd_writer.write_raw(b"FETCH ")
            await cmd_writer.write_raw(sequence_set)
            await cmd_writer.write_raw(b" ")
            await cmd_writer.write_raw(attrs)
            await cmd_writer.write_raw(b"\r\n")

        await self._command("FETCH", fetch_writer)

    async def create(self, name: str):
        async def create_writer(cmd_writer: _ImapCommandWriter):
            await cmd_writer.write_raw(b"CREATE ")
            await cmd_writer.write_string_literal(name)
            await cmd_writer.write_raw(b"\r\n")

        await self._command("CREATE", create_writer)

    async def create_if_not_exists(self, name: str):
        try:
            await self.select(name)
        except ImapServerError:
            await self.create(name)

    async def delete(self, name: str):
        async def create_writer(cmd_writer: _ImapCommandWriter):
            await cmd_writer.write_raw(b"DELETE ")
            await cmd_writer.write_string_literal(name)
            await cmd_writer.write_raw(b"\r\n")

        await self._command("DELETE", create_writer)

    async def uid_copy(self, uid: int, destination: str):
        async def uid_copy_writer(cmd_writer: _ImapCommandWriter):
            await cmd_writer.write_raw(b"UID COPY ")
            await cmd_writer.write_int(uid)
            await cmd_writer.write_raw(b" ")
            await cmd_writer.write_string_literal(destination)
            await cmd_writer.write_raw(b"\r\n")

        await self._command("UID COPY", uid_copy_writer)

    async def uid_move(self, uid: int, destination: str):
        async def uid_move_writer(cmd_writer: _ImapCommandWriter):
            await cmd_writer.write_raw(b"UID MOVE ")
            await cmd_writer.write_int(uid)
            await cmd_writer.write_raw(b" ")
            await cmd_writer.write_string_literal(destination)
            await cmd_writer.write_raw(b"\r\n")

        await self._command("UID MOVE", uid_move_writer)

    async def uid_move_graceful(self, uid: int, destination: str):
        if self.has_capability("MOVE"):
            await self.uid_move(uid, destination)
        else:
            await self.uid_copy(uid, destination)
            await self.uid_store(uid, rb"+FLAGS.SILENT (\Deleted)")
            await self.expunge()

    async def uid_store(self, uid: int, flags: bytes):
        async def uid_store_writer(cmd_writer: _ImapCommandWriter):
            await cmd_writer.write_raw(b"UID STORE ")
            await cmd_writer.write_int(uid)
            await cmd_writer.write_raw(b" ")
            await cmd_writer.write_raw(flags)
            await cmd_writer.write_raw(b"\r\n")

        await self._command("STORE", uid_store_writer)

    async def expunge(self):
        async def expunge_writer(cmd_writer: _ImapCommandWriter):
            await cmd_writer.write_raw(b"EXPUNGE\r\n")

        await self._command("EXPUNGE", expunge_writer)


class ImapServerError(ImapError):
    """Error class for errors reported from the server."""

    def __init__(self, command, result, server_response):
        self.command = command
        self.result = result
        self.server_response = server_response
        super().__init__(command, result, server_response)

    def __str__(self):
        return (
            f"IMAP error: Command {self.command} returned {self.result} "
            f"with response data: {self.server_response}"
        )
