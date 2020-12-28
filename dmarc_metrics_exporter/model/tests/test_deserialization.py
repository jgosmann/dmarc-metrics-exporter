from xsdata.formats.dataclass.context import XmlContext
from xsdata.formats.dataclass.parsers import XmlParser

from dmarc_metrics_exporter.model.dmarc_aggregate_report import Feedback

from .sample_data import SAMPLE_DATACLASS, SAMPLE_XML


def test_deserialization():
    parser = XmlParser(context=XmlContext())
    assert parser.from_string(SAMPLE_XML, Feedback) == SAMPLE_DATACLASS
