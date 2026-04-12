import gzip
import io
import os.path
from email.contentmanager import raw_data_manager
from email.message import EmailMessage
from typing import Callable, Generator, Mapping, Union
from zipfile import ZipFile

import xsdata
from xsdata.formats.dataclass.context import XmlContext
from xsdata.formats.dataclass.parsers.config import ParserConfig
from xsdata.formats.dataclass.parsers.xml import XmlParser

from dmarc_metrics_exporter.dmarc_event import (
    Disposition,
    DmarcEvent,
    DmarcResult,
    Meta,
)
from dmarc_metrics_exporter.model import dmarc_0_1, dmarc_2_0


def handle_octet_stream(filename: str, buffer: bytes) -> Generator[str, None, None]:
    _, file_extension = os.path.splitext(filename)
    return file_extension_handlers[file_extension](filename, buffer)


def handle_application_gzip(
    _filename: str, gzip_bytes: bytes
) -> Generator[str, None, None]:
    yield gzip.decompress(gzip_bytes).decode("utf-8")


def handle_application_zip(
    _filename: str, zip_bytes: bytes
) -> Generator[str, None, None]:
    with ZipFile(io.BytesIO(zip_bytes), "r") as zip_file:
        for name in zip_file.namelist():
            with zip_file.open(name, "r") as f:
                yield f.read().decode("utf-8")


def handle_text_xml(_filename: str, content: str) -> Generator[str, None, None]:
    yield content


content_type_handlers: Mapping[str, Callable[..., Generator[str, None, None]]] = {
    "application/octet-stream": handle_octet_stream,
    "application/gzip": handle_application_gzip,
    "application/zip": handle_application_zip,
    "text/xml": handle_text_xml,
}

file_extension_handlers: Mapping[str, Callable[..., Generator[str, None, None]]] = {
    ".gz": handle_application_gzip,
    ".zip": handle_application_zip,
}


class ReportExtractionError(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        from_email = self.msg.get("from", "<from missing>")
        subject = self.msg.get("subject", "<no subject>")
        return f"Failed to extract report from email by {from_email} with subject '{subject}'."


def get_aggregate_report_from_email(
    msg: EmailMessage,
) -> Generator[Union[dmarc_0_1.Feedback, dmarc_2_0.Feedback], None, None]:
    parser = XmlParser(
        context=XmlContext(), config=ParserConfig(fail_on_unknown_properties=True)
    )
    fallback_parser = XmlParser(
        context=XmlContext(), config=ParserConfig(fail_on_unknown_properties=False)
    )
    has_found_a_report = False
    for part in msg.walk():
        if part.get_content_type() in content_type_handlers:
            handler = content_type_handlers[part.get_content_type()]
            content = raw_data_manager.get_content(part)
            has_found_a_report = True
            for payload in handler(part.get_filename(), content):
                try:
                    yield parser.from_string(payload, dmarc_2_0.Feedback)
                except xsdata.exceptions.ParserError:
                    yield fallback_parser.from_string(payload, dmarc_0_1.Feedback)
    if not has_found_a_report:
        raise ReportExtractionError(msg)


def _map_disposition(
    disposition: Union[
        None, dmarc_0_1.DispositionType, dmarc_2_0.ActionDispositionType
    ],
) -> Disposition:
    if disposition is None:
        return Disposition.NONE_VALUE
    return {
        dmarc_0_1.DispositionType.NONE: Disposition.NONE_VALUE,
        dmarc_0_1.DispositionType.QUARANTINE: Disposition.QUARANTINE,
        dmarc_0_1.DispositionType.REJECT: Disposition.REJECT,
        dmarc_2_0.ActionDispositionType.NONE: Disposition.NONE_VALUE,
        dmarc_2_0.ActionDispositionType.QUARANTINE: Disposition.QUARANTINE,
        dmarc_2_0.ActionDispositionType.REJECT: Disposition.REJECT,
    }[disposition]


def convert_to_events(
    feedback: Union[dmarc_0_1.Feedback, dmarc_2_0.Feedback],
) -> Generator[DmarcEvent, None, None]:
    for record in feedback.record:
        if record.row is None:
            continue

        if feedback.report_metadata:
            reporter = feedback.report_metadata.org_name or ""
        else:
            reporter = ""

        if record.identifiers:
            from_domain = record.identifiers.header_from or ""
        else:
            from_domain = ""

        if record.auth_results and len(record.auth_results.dkim) > 0:
            dkim = record.auth_results.dkim[0]
            dkim_domain = dkim.domain or ""
            dkim_pass = dkim.result in (
                dmarc_0_1.DkimresultType.PASS,
                dmarc_2_0.DkimresultType.PASS,
            )
        else:
            dkim_domain = ""
            dkim_pass = False

        spf_domain = ""
        spf_pass = False
        if record.auth_results:
            spf = record.auth_results.spf
            if isinstance(spf, list) and len(spf) > 0:
                spf_domain = spf[0].domain or ""
                spf_pass = spf[0].result == dmarc_0_1.SpfresultType.PASS
            elif isinstance(spf, dmarc_2_0.SpfauthResultType):
                spf_domain = spf.domain or ""
                spf_pass = spf.result == dmarc_2_0.SpfresultType.PASS

        if record.row.policy_evaluated:
            disposition = _map_disposition(record.row.policy_evaluated.disposition)
            dkim_aligned = record.row.policy_evaluated.dkim in (
                dmarc_0_1.DmarcresultType.PASS,
                dmarc_2_0.DmarcresultType.PASS,
            )
            spf_aligned = record.row.policy_evaluated.spf in (
                dmarc_0_1.DmarcresultType.PASS,
                dmarc_2_0.DmarcresultType.PASS,
            )
        else:
            disposition = Disposition.NONE_VALUE
            dkim_aligned = False
            spf_aligned = False

        yield DmarcEvent(
            count=record.row.count or 1,
            meta=Meta(
                reporter=reporter,
                from_domain=from_domain,
                dkim_domain=dkim_domain,
                spf_domain=spf_domain,
            ),
            result=DmarcResult(
                disposition=disposition,
                dkim_aligned=dkim_aligned,
                spf_aligned=spf_aligned,
                dkim_pass=dkim_pass,
                spf_pass=spf_pass,
            ),
        )
