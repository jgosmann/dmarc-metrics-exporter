import io
from email.message import EmailMessage
from email.mime.application import MIMEApplication
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from gzip import GzipFile
from zipfile import ZipFile

from dmarc_metrics_exporter.model.tests.sample_data import create_sample_xml


def create_minimal_email(to="dmarc-feedback@mydomain.de", content=None):
    msg = EmailMessage()
    msg["Subject"] = "Minimal email"
    msg["From"] = "noreply-dmarc-support@google.com"
    msg["To"] = to
    if content:
        msg.set_content(content)
    return msg


def create_xml_report(*, report_id="12598866915817748661") -> MIMEText:
    xml = MIMEText(create_sample_xml(report_id=report_id), "xml")
    xml.add_header(
        "Content-Disposition",
        "attachment",
        filename="reporter.com!localhost!1601510400!1601596799.xml",
    )
    return xml


def create_zip_report(
    *, report_id="12598866915817748661", subtype="zip"
) -> MIMEApplication:
    compressed = io.BytesIO()
    with ZipFile(compressed, "w") as zip_file:
        zip_file.writestr(
            "reporter.com!localhost!1601510400!1601596799.xml",
            create_sample_xml(report_id=report_id),
        )

    zip_mime = MIMEApplication(compressed.getvalue(), subtype)
    zip_mime.add_header(
        "Content-Disposition",
        "attachment",
        filename="reporter.com!localhost!1601510400!1601596799.zip",
    )
    return zip_mime


def create_gzip_report(
    *, report_id="12598866915817748661", subtype="gzip"
) -> MIMEApplication:
    compressed = io.BytesIO()
    filename = "reporter.com!localhost!1601510400!1601596799.xml.gz"
    with GzipFile(filename, mode="wb", fileobj=compressed) as gzip_file:
        gzip_file.write(create_sample_xml(report_id=report_id).encode("utf-8"))

    gzip_mime = MIMEApplication(compressed.getvalue(), subtype)
    gzip_mime.add_header(
        "Content-Disposition",
        "attachment",
        filename="reporter.com!localhost!1601510400!1601596799.xml.gz",
    )
    return gzip_mime


def create_email_with_attachment(
    attachment: MIMEBase, *, to="dmarc-feedback@mydomain.de"
):
    msg = EmailMessage()
    msg.add_attachment(attachment)
    msg["Subject"] = "DMARC Aggregate Report"
    msg["From"] = "noreply-dmarc-support@google.com"
    msg["To"] = to
    return msg
