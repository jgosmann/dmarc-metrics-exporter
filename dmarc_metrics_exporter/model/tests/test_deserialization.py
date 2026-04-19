from xsdata.formats.dataclass.context import XmlContext
from xsdata.formats.dataclass.parsers import XmlParser
from xsdata.formats.dataclass.parsers.config import ParserConfig

from dmarc_metrics_exporter.model import dmarc_0_1, dmarc_2_0

from .sample_data_0_1 import SAMPLE_DATACLASS_0_1, create_sample_xml_0_1
from .sample_data_2_0 import SAMPLE_DATACLASS_2_0, create_sample_xml_2_0


def test_deserialization_0_1():
    parser = XmlParser(
        context=XmlContext(), config=ParserConfig(fail_on_unknown_properties=False)
    )
    assert (
        parser.from_string(create_sample_xml_0_1(), dmarc_0_1.Feedback)
        == SAMPLE_DATACLASS_0_1
    )


def test_deserialization_2_0():
    parser = XmlParser(
        context=XmlContext(), config=ParserConfig(fail_on_unknown_properties=False)
    )
    assert (
        parser.from_string(create_sample_xml_2_0(), dmarc_2_0.Feedback)
        == SAMPLE_DATACLASS_2_0
    )
