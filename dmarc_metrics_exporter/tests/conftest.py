import asyncio
import smtplib
import ssl
import time
from dataclasses import astuple, dataclass
from email.message import EmailMessage
from typing import Any, Awaitable, Callable, Union

import pytest
import requests

from dmarc_metrics_exporter.imap_client import ImapClient
from dmarc_metrics_exporter.imap_queue import ConnectionConfig


@dataclass
class NetworkAddress:
    host: str
    port: int


@dataclass
class Greenmail:
    smtp: NetworkAddress
    imap: ConnectionConfig
    api: NetworkAddress

    @property
    def api_url(self) -> str:
        return f"http://{self.api.host}:{self.api.port}/api"

    def is_ready(self) -> bool:
        return (
            requests.get(f"{self.api_url}/service/readiness", timeout=1).status_code
            == requests.codes.ok
        )

    def purge_mails(self):
        requests.post(f"{self.api_url}/mail/purge", timeout=5).raise_for_status()

    async def restart(self):
        requests.post(f"{self.api_url}/service/reset", timeout=5)
        await try_until_success(self.is_ready)


@pytest.fixture(name="greenmail")
def fixture_greenmail() -> Greenmail:
    greenmail = Greenmail(
        smtp=NetworkAddress("localhost", 3025),
        imap=ConnectionConfig(
            host="localhost",
            port=3993,
            username="queue@localhost",
            password="password",
            use_ssl=True,
            verify_certificate=False,
            # The Java SSL/TLS impplementation that Greenmail is relying on
            # is sending a "user_cancelled" alert before the "close_notify"
            # when logging out. This is in violation of the the TLS spec and
            # OpenSSL (used by Python) will give an error for this, when
            # using TLS 1.3, starting with OpenSSL 3.2.
            # This has been previously reported as bug JDK-8282600, but the
            # fix only omits the "user_cancelled" alert if the client already
            # closed its end of the TLS connection. This we cannot easily do
            # as we first want to receive the IMAP server's confirmation of the
            # logout. It would also require to handle the SSL/TLS connection
            # on a lower level where we can actually control sending the
            # "close_notify" alert.
            #
            # JDK-8282600: https://bugs.openjdk.org/browse/JDK-8282600
            tls_maximum_version=ssl.TLSVersion.TLSv1_2,
        ),
        api=NetworkAddress("localhost", 8080),
    )
    greenmail.purge_mails()
    return greenmail


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
        except asyncio.TimeoutError as err:
            raise TimeoutError(
                f"Function execution duration exceeded {max_fn_duration_seconds} seconds."
            ) from err
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
