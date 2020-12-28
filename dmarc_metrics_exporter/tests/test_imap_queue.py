import asyncio
import smtplib
import time
from email.message import EmailMessage
from typing import Awaitable, Callable

import docker
import docker.models
import pytest

from dmarc_metrics_exporter.imap_queue import ConnectionConfig, ImapClient, ImapQueue


@pytest.fixture(name="docker_client")
def fixture_docker_client() -> docker.DockerClient:
    return docker.from_env()


@pytest.fixture(name="_greenmail")
def fixture_greenmail(
    docker_client: docker.DockerClient,
) -> docker.models.containers.Container:
    container = docker_client.containers.run(
        "greenmail/standalone:1.6.0",
        detach=True,
        remove=True,
        ports={"3025/tcp": 3025, "3993/tcp": 3993},
    )
    yield container
    container.stop()


async def try_until_success(
    function: Callable[[], Awaitable],
    timeout_seconds: int = 10,
    max_fn_duration_seconds: int = 1,
    poll_interval_seconds: float = 0.1,
):
    timeout = time.time() + timeout_seconds
    last_err = None
    while time.time() < timeout:
        try:
            await asyncio.wait_for(function(), max_fn_duration_seconds)
            return
        except Exception as err:  # pylint: disable=broad-except
            last_err = err
            await asyncio.sleep(poll_interval_seconds)
    raise TimeoutError(
        f"Call to {function} not successful within {timeout_seconds} seconds."
    ) from last_err


async def send_email(msg, host="localhost", port=3025):
    smtp = smtplib.SMTP(host, port)
    smtp.send_message(msg)
    smtp.quit()


async def verify_email_delivered(connection: ConnectionConfig):
    async with ImapClient(connection) as client:
        assert await client.select() > 0


@pytest.mark.asyncio
async def test_successful_processing_of_existing_queue_message(_greenmail):
    # Given
    msg = EmailMessage()
    msg.set_content("message content")
    msg["Subject"] = "Message subject"
    msg["From"] = "sender@some-domain.org"
    msg["To"] = "queue@localhost"

    connection_config = ConnectionConfig(
        host="localhost", port=3993, username="queue@localhost", password="password"
    )

    await try_until_success(lambda: send_email(msg))
    await try_until_success(lambda: verify_email_delivered(connection_config))

    is_done = asyncio.Event()

    async def handler(_queue_msg, is_done=is_done):
        is_done.set()

    # When
    queue = ImapQueue(connection=connection_config)
    queue.consume(handler)
    try:
        await asyncio.wait_for(is_done.wait(), 10)
    finally:
        await queue.stop_consumer()

    # TODO Then
