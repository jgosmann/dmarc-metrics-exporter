import asyncio
from email.message import EmailMessage

import pytest

from dmarc_metrics_exporter.imap_queue import ImapClient, ImapQueue

from .conftest import (
    run_greenmail,
    send_email,
    try_until_success,
    verify_email_delivered,
    verify_imap_available,
)


def create_dummy_email(to: str):
    msg = EmailMessage()
    msg.set_content("message content")
    msg["Subject"] = "Message subject"
    msg["From"] = "sender@some-domain.org"
    msg["To"] = to
    return msg


def assert_emails_equal(a: EmailMessage, b: EmailMessage):
    assert all(a[header] == b[header] for header in ("Subject", "From", "To"))
    assert a.get_content().strip() == b.get_content().strip()


@pytest.mark.asyncio
async def test_successful_processing_of_existing_queue_message(greenmail):
    # Given
    msg = create_dummy_email(greenmail.imap.username)
    await try_until_success(lambda: send_email(msg, greenmail.smtp))
    await try_until_success(lambda: verify_email_delivered(greenmail.imap))

    is_done = asyncio.Event()

    async def handler(queue_msg: EmailMessage, is_done=is_done):
        is_done.set()
        assert_emails_equal(queue_msg, msg)

    # When
    queue = ImapQueue(connection=greenmail.imap)
    queue.consume(handler)
    try:
        await asyncio.wait_for(is_done.wait(), 10)
    finally:
        await queue.stop_consumer()

    # Then
    async with ImapClient(greenmail.imap) as client:
        assert await client.select() == 0
        assert await client.select(queue.folders.done) == 1


@pytest.mark.asyncio
async def test_successful_processing_of_incoming_queue_message(greenmail):
    # Given
    msg = create_dummy_email(greenmail.imap.username)

    is_done = asyncio.Event()

    async def handler(queue_msg: EmailMessage, is_done=is_done):
        is_done.set()
        assert_emails_equal(queue_msg, msg)

    # When
    await try_until_success(lambda: verify_imap_available(greenmail.imap))
    queue = ImapQueue(connection=greenmail.imap, poll_interval_seconds=0.1)
    queue.consume(handler)

    await asyncio.sleep(0.5)
    await try_until_success(lambda: send_email(msg, greenmail.smtp))
    await try_until_success(
        lambda: verify_email_delivered(
            greenmail.imap, mailboxes=("INBOX", queue.folders.done)
        )
    )

    try:
        await asyncio.wait_for(is_done.wait(), 10)
    finally:
        await queue.stop_consumer()

    # Then
    async with ImapClient(greenmail.imap) as client:
        assert await client.select() == 0
        assert await client.select(queue.folders.done) == 1


@pytest.mark.asyncio
async def test_error_handling_when_processing_queue_message(greenmail):
    # Given
    msg = create_dummy_email(greenmail.imap.username)
    await try_until_success(lambda: send_email(msg, greenmail.smtp))
    await try_until_success(lambda: verify_email_delivered(greenmail.imap))

    is_done = asyncio.Event()

    async def handler(_queue_msg: EmailMessage, is_done=is_done):
        is_done.set()
        raise Exception("Error raised on purpose.")

    # When
    queue = ImapQueue(connection=greenmail.imap)
    queue.consume(handler)
    try:
        await asyncio.wait_for(is_done.wait(), 10)
    finally:
        await queue.stop_consumer()

    # Then
    async with ImapClient(greenmail.imap) as client:
        assert await client.select() == 0
        assert await client.select(queue.folders.error) == 1


@pytest.mark.asyncio
async def test_reconnects_if_imap_connection_is_lost(docker_client):
    is_done = asyncio.Event()

    async def handler(queue_msg: EmailMessage, is_done=is_done):
        is_done.set()
        assert_emails_equal(queue_msg, msg)

    queue = None
    try:
        with run_greenmail(docker_client) as greenmail:
            await try_until_success(lambda: verify_imap_available(greenmail.imap))
            queue = ImapQueue(
                connection=greenmail.imap,
                poll_interval_seconds=0.1,
                timeout_seconds=0.5,
            )
            queue.consume(handler)
            msg = create_dummy_email(greenmail.imap.username)
            await try_until_success(lambda: send_email(msg, greenmail.smtp))
            await asyncio.wait_for(is_done.wait(), 10)

        is_done.clear()
        with run_greenmail(docker_client) as greenmail:
            msg = create_dummy_email(greenmail.imap.username)
            await try_until_success(lambda: send_email(msg, greenmail.smtp))
            await asyncio.wait_for(is_done.wait(), 10)
    finally:
        if queue is not None:
            await queue.stop_consumer()
