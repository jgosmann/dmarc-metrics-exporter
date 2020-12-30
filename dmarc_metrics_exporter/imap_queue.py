import asyncio
import email.policy
import logging
import re
from asyncio.tasks import Task
from dataclasses import astuple, dataclass
from email.message import EmailMessage
from email.parser import BytesParser
from typing import Any, AsyncGenerator, Awaitable, Callable, Optional, Tuple, cast

from aioimaplib import aioimaplib

logger = logging.getLogger(__name__)


@dataclass
class ConnectionConfig:
    username: str
    password: str
    host: str = "localhost"
    port: int = 993


@dataclass
class QueueFolders:
    inbox: str = "INBOX"
    done: str = "Archive"
    error: str = "Invalid"


class ImapQueue:
    def __init__(
        self,
        *,
        connection: ConnectionConfig,
        folders: QueueFolders = QueueFolders(),
        poll_interval_seconds: int = 60,
        timeout_seconds: int = 60,
    ):
        self.connection = connection
        self.folders = folders
        self.poll_interval_seconds = poll_interval_seconds
        self.timeout_seconds = timeout_seconds
        self._stop = False
        self._consumer: Optional[Task[Any]] = None

    def consume(self, handler: Callable[[Any], Awaitable[None]]):
        self._consumer = asyncio.create_task(self._consume(handler))

    async def _consume(self, handler: Callable[[Any], Awaitable[None]]):
        while not self._stop:
            try:
                async with ImapClient(self.connection, self.timeout_seconds) as client:
                    for folder in astuple(self.folders):
                        await client.create_if_not_exists(folder)

                    msg_count = await client.select(self.folders.inbox)
                    if msg_count > 0:
                        async for uid, msg in client.fetch(1, msg_count):
                            try:
                                await handler(msg)
                            except Exception:  # pylint: disable=broad-except
                                logger.exception(
                                    "Handler for message in IMAP queue failed."
                                )
                                await client.uid_move(uid, self.folders.error)
                            else:
                                await client.uid_move(uid, self.folders.done)
            except (asyncio.TimeoutError, Exception):  # pylint: disable=broad-except
                logger.exception("Error during IMAP queue polling.")
            await asyncio.sleep(self.poll_interval_seconds)

    async def stop_consumer(self):
        self._stop = True
        await self._consumer


class ImapClient:
    def __init__(self, connection: ConnectionConfig, timeout_seconds: int = 10):
        self.connection = connection
        self.timeout_seconds = timeout_seconds
        self._client = aioimaplib.IMAP4_SSL(
            host=self.connection.host,
            port=self.connection.port,
            timeout=timeout_seconds,
        )

    async def __aenter__(self):
        await self._client.wait_hello_from_server()
        await self._check(
            "LOGIN",
            self._client.login(self.connection.username, self.connection.password),
        )
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        await self._check("LOGOUT", self._client.logout())

    async def _check(self, command: str, awaitable: Awaitable[Tuple[str, Any]]) -> Any:
        res, data = await asyncio.wait_for(awaitable, self.timeout_seconds)
        if res != "OK":
            raise ImportError(command, res, data)
        return data

    async def select(self, folder: str = "INBOX") -> int:
        """Selects a mailbox and returns the existing mail count."""
        data = await self._check("SELECT", self._client.select(folder))
        exists_regex = re.compile(r"^(\d+) EXISTS$")
        matches = (exists_regex.match(line) for line in data)
        msg_count = next(int(m.group(1)) for m in matches if m)
        return msg_count

    async def fetch(
        self, first_msg: int, last_msg: int
    ) -> AsyncGenerator[Tuple[int, EmailMessage], None]:
        lines = iter(
            await self._check(
                "FETCH", self._client.fetch(f"{first_msg}:{last_msg}", "(UID RFC822)")
            )
        )
        mail_header_regex = re.compile(r"^\d+\s+FETCH\s*\(.*UID\s+(\d+).*RFC822.*")
        try:
            while True:
                line = next(lines)
                match = mail_header_regex.match(line)
                if match:
                    uid = int(match.group(1))
                    mail = next(lines)
                    terminator = next(lines)
                    if not terminator == ")":
                        raise ImapClientError(
                            f"Expected group termination with ')', but got '{terminator}'."
                        )
                    yield uid, cast(
                        EmailMessage,
                        BytesParser(policy=email.policy.default).parsebytes(mail),
                    )
        except StopIteration:
            pass

    async def create_if_not_exists(self, mailbox_name: str):
        mailboxes = [
            line
            for line in await self._check("LIST", self._client.list(".", mailbox_name))
            if line != "LIST completed."
        ]
        if len(mailboxes) == 0:
            await self._check("CREATE", self._client.create(mailbox_name))

    async def uid_move(self, uid: int, destination: str):
        if self._client.has_capability("MOVE"):
            await self._check(
                "UID MOVE", self._client.uid("move", str(uid), destination)
            )
        else:
            await self._check(
                "UID COPY", self._client.uid("copy", str(uid), destination)
            )
            await self._check(
                "UID STORE",
                self._client.uid("store", str(uid), r"+FLAGS.SILENT (\Deleted)"),
            )
            await self._check("UID EXPUNGE", self._client.uid("expunge", str(uid)))


class ImapError(Exception):
    pass


class ImapClientError(ImapError):
    """Error class for errors encountered on the client side."""


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
