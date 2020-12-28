import io
from email.contentmanager import raw_data_manager
from email.message import EmailMessage
from typing import Generator
from zipfile import ZipFile

from xsdata.formats.dataclass.context import XmlContext
from xsdata.formats.dataclass.parsers.xml import XmlParser

from dmarc_metrics_exporter.model.dmarc_aggregate_report import Feedback


def _get_payloads_from_zip(zip_bytes: bytes) -> Generator[str, None, None]:
    with ZipFile(io.BytesIO(zip_bytes), "r") as zip_file:
        for name in zip_file.namelist():
            with zip_file.open(name, "r") as f:
                yield f.read().decode("utf-8")


def get_aggregate_report_from_email(
    msg: EmailMessage,
) -> Generator[Feedback, None, None]:
    parser = XmlParser(context=XmlContext())
    for part in msg.walk():
        if part.get_content_type() == "text/xml":
            content = raw_data_manager.get_content(part)
            yield parser.from_string(content, Feedback)
        elif part.get_content_type() == "application/zip":
            content = raw_data_manager.get_content(part)
            for payload in _get_payloads_from_zip(content):
                yield parser.from_string(payload, Feedback)
