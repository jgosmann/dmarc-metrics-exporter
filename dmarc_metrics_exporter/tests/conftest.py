import asyncio
import smtplib
import time
from contextlib import contextmanager
from dataclasses import astuple, dataclass
from email.message import EmailMessage
from typing import Any, Awaitable, Callable, Generator, Union

import docker.models
import pytest

from dmarc_metrics_exporter.imap_queue import ConnectionConfig, ImapClient


@dataclass
class NetworkAddress:
    host: str
    port: int


@dataclass
class Greenmail:
    smtp: NetworkAddress
    imap: ConnectionConfig


@pytest.fixture(name="docker_client")
def fixture_docker_client() -> docker.DockerClient:
    return docker.from_env()


@pytest.fixture(name="greenmail")
def fixture_greenmail(
    docker_client: docker.DockerClient,
) -> Generator[Greenmail, None, None]:
    with run_greenmail(docker_client) as greenmail:
        yield greenmail


@contextmanager
def run_greenmail(
    docker_client: docker.DockerClient,
) -> Generator[Greenmail, None, None]:
    container = docker_client.containers.run(
        "greenmail/standalone:1.6.0",
        detach=True,
        remove=True,
        ports={"3025/tcp": 3025, "3993/tcp": 3993},
    )
    yield Greenmail(
        smtp=NetworkAddress("localhost", 3025),
        imap=ConnectionConfig(
            host="localhost", port=3993, username="queue@localhost", password="password"
        ),
    )
    container.stop()


async def try_until_success(
    function: Union[Callable[[], Awaitable], Callable[[], Any]],
    timeout_seconds: int = 10,
    max_fn_duration_seconds: int = 1,
    poll_interval_seconds: float = 0.1,
):
    timeout = time.time() + timeout_seconds
    last_err = None
    while time.time() < timeout:
        try:
            result = function()
            if hasattr(result, "__await__"):
                return await asyncio.wait_for(result, max_fn_duration_seconds)
            else:
                return result
        except Exception as err:  # pylint: disable=broad-except
            last_err = err
            await asyncio.sleep(poll_interval_seconds)
    raise TimeoutError(
        f"Call to {function} not successful within {timeout_seconds} seconds."
    ) from last_err


async def send_email(msg: EmailMessage, network_address: NetworkAddress):
    smtp = smtplib.SMTP(*astuple(network_address))
    smtp.send_message(msg)
    smtp.quit()


async def verify_email_delivered(connection: ConnectionConfig, mailboxes=("INBOX",)):
    async with ImapClient(connection) as client:
        msg_counts = await asyncio.gather(
            *(client.select(mailbox) for mailbox in mailboxes)
        )
        assert any(count > 0 for count in msg_counts)


async def verify_imap_available(connection: ConnectionConfig):
    async with ImapClient(connection):
        pass
