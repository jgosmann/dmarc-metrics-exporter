import io
from email.message import EmailMessage
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
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


def create_email_with_xml_attachment(
    to="dmarc-feedback@mydomain.de", *, report_id="12598866915817748661"
):
    xml = MIMEText(create_sample_xml(report_id=report_id), "xml")
    xml.add_header(
        "Content-Disposition",
        "attachment",
        filename="reporter.com!localhost!1601510400!1601596799.xml",
    )
    msg = EmailMessage()
    msg.add_attachment(xml)
    msg["Subject"] = "DMARC Aggregate Report"
    msg["From"] = "noreply-dmarc-support@google.com"
    msg["To"] = to
    return msg


def create_email_with_zip_attachment(
    to="dmarc-feedback@mydomain.de", *, report_id="12598866915817748661"
):
    compressed = io.BytesIO()
    with ZipFile(compressed, "w") as zip_file:
        zip_file.writestr(
            "reporter.com!localhost!1601510400!1601596799.xml",
            create_sample_xml(report_id=report_id),
        )

    xml = MIMEApplication(compressed.getvalue(), "zip")
    xml.add_header(
        "Content-Disposition",
        "attachment",
        filename="reporter.com!localhost!1601510400!1601596799.zip",
    )
    msg = EmailMessage()
    msg.add_attachment(xml)
    msg["Subject"] = "DMARC Aggregate Report"
    msg["From"] = "noreply-dmarc-support@google.com"
    msg["To"] = to
    return msg
