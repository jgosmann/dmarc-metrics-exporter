import io
from email.message import EmailMessage
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from zipfile import ZipFile

from dmarc_metrics_exporter.deserialization import (
    convert_to_events,
    get_aggregate_report_from_email,
)
from dmarc_metrics_exporter.dmarc_event import (
    Disposition,
    DmarcEvent,
    DmarcResult,
    Meta,
)
from dmarc_metrics_exporter.model.tests.sample_data import SAMPLE_DATACLASS, SAMPLE_XML


def test_extracts_plain_xml_from_email():
    xml = MIMEText(SAMPLE_XML, "xml")
    xml.add_header(
        "Content-Disposition",
        "attachment",
        filename="reporter.com!localhost!1601510400!1601596799.xml",
    )
    msg = EmailMessage()
    msg.add_attachment(xml)

    assert list(get_aggregate_report_from_email(msg)) == [SAMPLE_DATACLASS]


def test_extracts_zipped_xml_from_email():
    compressed = io.BytesIO()
    with ZipFile(compressed, "w") as zip_file:
        zip_file.writestr(
            "reporter.com!localhost!1601510400!1601596799.xml", SAMPLE_XML
        )

    xml = MIMEApplication(compressed.getvalue(), "zip")
    xml.add_header(
        "Content-Disposition",
        "attachment",
        filename="reporter.com!localhost!1601510400!1601596799.zip",
    )
    msg = EmailMessage()
    msg.add_attachment(xml)

    assert list(get_aggregate_report_from_email(msg)) == [SAMPLE_DATACLASS]


def test_convert_to_events():
    assert list(convert_to_events(SAMPLE_DATACLASS)) == [
        DmarcEvent(
            count=1,
            meta=Meta(
                reporter="google.com",
                from_domain="mydomain.de",
                dkim_domain="mydomain.de",
                spf_domain="my-spf-domain.de",
            ),
            result=DmarcResult(
                disposition=Disposition.NONE_VALUE,
                dkim_pass=True,
                dkim_aligned=True,
                spf_pass=True,
                spf_aligned=False,
            ),
        )
    ]
