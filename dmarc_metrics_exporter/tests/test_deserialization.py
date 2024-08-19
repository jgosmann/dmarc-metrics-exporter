import pytest

from dmarc_metrics_exporter.deserialization import (
    ReportExtractionError,
    convert_to_events,
    get_aggregate_report_from_email,
)
from dmarc_metrics_exporter.dmarc_event import (
    Disposition,
    DmarcEvent,
    DmarcResult,
    Meta,
)
from dmarc_metrics_exporter.model.tests.sample_data import SAMPLE_DATACLASS
from dmarc_metrics_exporter.tests.sample_emails import (
    create_email_with_attachment,
    create_gzip_report,
    create_minimal_email,
    create_xml_report,
    create_zip_report,
)


def test_extracts_plain_xml_from_email():
    msg = create_email_with_attachment(create_xml_report())
    assert list(get_aggregate_report_from_email(msg)) == [SAMPLE_DATACLASS]


def test_extracts_zipped_xml_from_email():
    msg = create_email_with_attachment(create_zip_report())
    assert list(get_aggregate_report_from_email(msg)) == [SAMPLE_DATACLASS]


def test_extracts_gzipped_xml_from_email():
    msg = create_email_with_attachment(create_gzip_report())
    assert list(get_aggregate_report_from_email(msg)) == [SAMPLE_DATACLASS]


def test_extracts_zipped_xml_from_email_with_octet_stream_content_type():
    msg = create_email_with_attachment(create_zip_report(subtype="octet-stream"))
    assert list(get_aggregate_report_from_email(msg)) == [SAMPLE_DATACLASS]


def test_extracts_gzipped_xml_from_email_with_octet_stream_content_type():
    msg = create_email_with_attachment(create_gzip_report(subtype="octet-stream"))
    assert list(get_aggregate_report_from_email(msg)) == [SAMPLE_DATACLASS]


def test_returns_err_if_no_report_can_be_extracted():
    msg = create_minimal_email()
    with pytest.raises(ReportExtractionError) as err:
        list(get_aggregate_report_from_email(msg))
    assert err.value.msg is msg


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
