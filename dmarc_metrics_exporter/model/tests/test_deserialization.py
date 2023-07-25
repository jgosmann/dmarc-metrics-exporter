from xsdata.formats.dataclass.context import XmlContext
from xsdata.formats.dataclass.parsers import XmlParser
from xsdata.formats.dataclass.parsers.config import ParserConfig

from dmarc_metrics_exporter.model.dmarc_aggregate_report import Feedback

from .sample_data import SAMPLE_DATACLASS, create_sample_xml


def test_deserialization():
    parser = XmlParser(
        context=XmlContext(), config=ParserConfig(fail_on_unknown_properties=False)
    )
    assert parser.from_string(create_sample_xml(), Feedback) == SAMPLE_DATACLASS
