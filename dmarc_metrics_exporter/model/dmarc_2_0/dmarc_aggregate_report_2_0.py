from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import List, Optional

__NAMESPACE__ = "urn:ietf:params:xml:ns:dmarc-2.0"


class ActionDispositionType(Enum):
    NONE = "none"
    PASS = "pass"
    QUARANTINE = "quarantine"
    REJECT = "reject"


class AlignmentType(Enum):
    R = "r"
    S = "s"


class DkimresultType(Enum):
    NONE = "none"
    PASS = "pass"
    FAIL = "fail"
    POLICY = "policy"
    NEUTRAL = "neutral"
    TEMPERROR = "temperror"
    PERMERROR = "permerror"


class DmarcresultType(Enum):
    PASS = "pass"
    FAIL = "fail"


@dataclass
class DateRangeType:
    begin: Optional[int] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
            "required": True,
        },
    )
    end: Optional[int] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
            "required": True,
        },
    )


class DiscoveryType(Enum):
    PSL = "psl"
    TREEWALK = "treewalk"


class DispositionType(Enum):
    NONE = "none"
    QUARANTINE = "quarantine"
    REJECT = "reject"


@dataclass
class ExtensionType:
    any_element: List[object] = field(
        default_factory=list,
        metadata={
            "type": "Wildcard",
            "namespace": "##any",
        },
    )


@dataclass
class IdentifierType:
    header_from: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
            "required": True,
        },
    )
    envelope_from: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
        },
    )
    envelope_to: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
        },
    )


class PolicyOverrideType(Enum):
    LOCAL_POLICY = "local_policy"
    MAILING_LIST = "mailing_list"
    OTHER = "other"
    POLICY_TEST_MODE = "policy_test_mode"
    TRUSTED_FORWARDER = "trusted_forwarder"


class SpfdomainScope(Enum):
    MFROM = "mfrom"


class SpfresultType(Enum):
    NONE = "none"
    PASS = "pass"
    FAIL = "fail"
    SOFTFAIL = "softfail"
    POLICY = "policy"
    NEUTRAL = "neutral"
    TEMPERROR = "temperror"
    PERMERROR = "permerror"


class TestingType(Enum):
    N = "n"
    Y = "y"


@dataclass
class LangAttrString:
    class Meta:
        name = "langAttrString"

    value: str = field(
        default="",
        metadata={
            "required": True,
        },
    )
    lang: str = field(
        default="en",
        metadata={
            "type": "Attribute",
        },
    )


@dataclass
class DkimauthResultType:
    class Meta:
        name = "DKIMAuthResultType"

    domain: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
            "required": True,
        },
    )
    selector: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
            "required": True,
        },
    )
    result: Optional[DkimresultType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
            "required": True,
        },
    )
    human_result: Optional[LangAttrString] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
        },
    )


@dataclass
class PolicyOverrideReason:
    type_value: Optional[PolicyOverrideType] = field(
        default=None,
        metadata={
            "name": "type",
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
            "required": True,
        },
    )
    comment: Optional[LangAttrString] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
        },
    )


@dataclass
class PolicyPublishedType:
    domain: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
            "required": True,
        },
    )
    p: Optional[DispositionType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
            "required": True,
        },
    )
    sp: Optional[DispositionType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
        },
    )
    np: Optional[DispositionType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
        },
    )
    adkim: Optional[AlignmentType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
        },
    )
    aspf: Optional[AlignmentType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
        },
    )
    discovery_method: Optional[DiscoveryType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
        },
    )
    fo: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
        },
    )
    testing: Optional[TestingType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
        },
    )


@dataclass
class ReportMetadataType:
    org_name: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
            "required": True,
        },
    )
    email: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
            "required": True,
        },
    )
    extra_contact_info: Optional[LangAttrString] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
        },
    )
    report_id: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
            "required": True,
        },
    )
    date_range: Optional[DateRangeType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
            "required": True,
        },
    )
    error: Optional[LangAttrString] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
        },
    )
    generator: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
        },
    )


@dataclass
class SpfauthResultType:
    class Meta:
        name = "SPFAuthResultType"

    domain: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
            "required": True,
        },
    )
    scope: Optional[SpfdomainScope] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
        },
    )
    result: Optional[SpfresultType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
            "required": True,
        },
    )
    human_result: Optional[LangAttrString] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
        },
    )


@dataclass
class AuthResultType:
    dkim: List[DkimauthResultType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
        },
    )
    spf: Optional[SpfauthResultType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
        },
    )


@dataclass
class PolicyEvaluatedType:
    disposition: Optional[ActionDispositionType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
            "required": True,
        },
    )
    dkim: Optional[DmarcresultType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
            "required": True,
        },
    )
    spf: Optional[DmarcresultType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
            "required": True,
        },
    )
    reason: List[PolicyOverrideReason] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
        },
    )


@dataclass
class RowType:
    source_ip: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
            "required": True,
        },
    )
    count: Optional[int] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
            "required": True,
        },
    )
    policy_evaluated: Optional[PolicyEvaluatedType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
            "required": True,
        },
    )


@dataclass
class RecordType:
    row: Optional[RowType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
            "required": True,
        },
    )
    identifiers: Optional[IdentifierType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
            "required": True,
        },
    )
    auth_results: Optional[AuthResultType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:dmarc-2.0",
            "required": True,
        },
    )
    any_element: List[object] = field(
        default_factory=list,
        metadata={
            "type": "Wildcard",
            "namespace": "##any",
        },
    )


@dataclass
class Feedback:
    class Meta:
        name = "feedback"
        namespace = "urn:ietf:params:xml:ns:dmarc-2.0"

    version: Optional[Decimal] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    report_metadata: Optional[ReportMetadataType] = field(
        default=None,
        metadata={
            "type": "Element",
            "required": True,
        },
    )
    policy_published: Optional[PolicyPublishedType] = field(
        default=None,
        metadata={
            "type": "Element",
            "required": True,
        },
    )
    extension: Optional[ExtensionType] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    record: List[RecordType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "min_occurs": 1,
        },
    )
