import ssl
from contextlib import contextmanager
from dataclasses import dataclass
from email.message import EmailMessage
from smtplib import SMTP
from typing import ContextManager, Generator


@dataclass
class ConnectionConfig:
    username: str
    password: str
    host: str = "localhost"
    port: int = 465


class _EstablishedSmtpConnection:
    def __init__(self, smtp: SMTP):
        self._smtp = smtp

    def send_message(self, msg: EmailMessage) -> None:
        self._smtp.send_message(msg)


ConnectionManager = ContextManager[_EstablishedSmtpConnection]


@contextmanager
def smtp_connection(
    connection: ConnectionConfig,
) -> Generator[_EstablishedSmtpConnection, None, None]:
    context = ssl.create_default_context()
    context.check_hostname = True
    with SMTP(connection.host, connection.port) as smtp:
        smtp.starttls(context=context)
        smtp.login(connection.username, connection.password)
        yield _EstablishedSmtpConnection(smtp)
