import asyncio
import contextlib
import email.policy
import logging
from asyncio.tasks import Task
from dataclasses import astuple, dataclass
from email.message import EmailMessage
from email.parser import BytesParser
from typing import Any, Awaitable, Callable, Optional, Tuple, cast
from urllib.parse import ParseResult

from dmarc_metrics_exporter.imap_client import ConnectionConfig, ImapClient

logger = logging.getLogger(__name__)


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
        self._client = ImapClient(connection, timeout_seconds)
        self._stop = asyncio.Event()
        self._poll_task: Optional[Task[Any]] = None

    def consume(self, handler: Callable[[Any], Awaitable[None]]):
        self._poll_task = asyncio.create_task(self._poll_imap(handler))

    async def _poll_imap(self, handler: Callable[[Any], Awaitable[None]]):
        while not self._stop.is_set():
            logger.debug("Polling IMAP ...")
            try:
                async with ImapClient(self.connection, self.timeout_seconds) as client:
                    for folder in astuple(self.folders):
                        await client.create_if_not_exists(folder)

                    msg_count = await client.select(self.folders.inbox)
                    logger.debug("%s messages to fetch.", msg_count)
                    if msg_count > 0:
                        fetch_task = asyncio.create_task(
                            client.fetch(
                                b"1:" + str(msg_count).encode("ascii"), b"(UID RFC822)"
                            )
                        )
                        while not fetch_task.done() or not client.fetched_queue.empty():
                            uid, msg = self._extract_uid_and_msg(
                                await client.fetched_queue.get()
                            )
                            if uid is not None and msg is not None:
                                try:
                                    logger.debug("Processing UID %s", uid)
                                    await handler(msg)
                                except Exception:  # pylint: disable=broad-except
                                    logger.exception(
                                        "Handler for message in IMAP queue failed."
                                    )
                                    await client.uid_move_graceful(
                                        uid, self.folders.error
                                    )
                                else:
                                    logger.debug("foo")
                                    await client.uid_move_graceful(
                                        uid, self.folders.done
                                    )
                                    logger.debug("bar")
                        logger.debug("Processed all messages.")
                        await fetch_task
            except (asyncio.TimeoutError, Exception):  # pylint: disable=broad-except
                logger.exception("Error during IMAP queue polling.")
            logger.debug(
                "Going to sleep for %s seconds until next poll.",
                self.poll_interval_seconds,
            )
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(self._stop.wait(), self.poll_interval_seconds)

    @classmethod
    def _extract_uid_and_msg(
        cls, parsed_response: ParseResult
    ) -> Tuple[Optional[int], Optional[EmailMessage]]:
        uid, msg = None, None
        if parsed_response[1] == b"FETCH":
            for key, value in cast(Tuple[Any, Any], parsed_response[2]):
                mail_body = None
                if key == b"UID":
                    uid = cast(int, value)
                elif key == b"RFC822":
                    mail_body = value
            if uid and mail_body:
                msg = cast(
                    EmailMessage,
                    BytesParser(policy=email.policy.default).parsebytes(mail_body),
                )
        return uid, msg

    async def stop_consumer(self):
        self._stop.set()
        await self._poll_task
