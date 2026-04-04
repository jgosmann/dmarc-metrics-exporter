from email.mime.text import MIMEText

from xsdata.formats.dataclass.context import XmlContext
from xsdata.formats.dataclass.parsers import XmlParser
from xsdata.formats.dataclass.parsers.config import ParserConfig

from dmarc_metrics_exporter.deserialization import get_aggregate_report_from_email
from dmarc_metrics_exporter.model.dmarc_aggregate_report import Feedback
from dmarc_metrics_exporter.tests.sample_emails import create_email_with_attachment

from .sample_data import SAMPLE_DATACLASS, create_sample_xml


def test_deserialization():
    parser = XmlParser(
        context=XmlContext(), config=ParserConfig(fail_on_unknown_properties=False)
    )
    assert parser.from_string(create_sample_xml(), Feedback) == SAMPLE_DATACLASS


def test_deserialization_with_default_namespace():
    namespaced_xml = create_sample_xml().replace(
        "<feedback>",
        '<feedback xmlns="http://dmarc.org/dmarc-xml/0.1">',
        1,
    )
    attachment = MIMEText(namespaced_xml, "xml")
    attachment.add_header(
        "Content-Disposition",
        "attachment",
        filename="reporter.com!localhost!1601510400!1601596799.xml",
    )
    msg = create_email_with_attachment(attachment)

    assert list(get_aggregate_report_from_email(msg)) == [SAMPLE_DATACLASS]
