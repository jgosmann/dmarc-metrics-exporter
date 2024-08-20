from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import List, Optional

__NAMESPACE__ = "http://dmarc.org/dmarc-xml/0.1"


class AlignmentType(Enum):
    R = "r"
    S = "s"


class DkimresultType(Enum):
    NONE_VALUE = "none"
    PASS_VALUE = "pass"
    FAIL = "fail"
    POLICY = "policy"
    NEUTRAL = "neutral"
    TEMPERROR = "temperror"
    PERMERROR = "permerror"


class DmarcresultType(Enum):
    PASS_VALUE = "pass"
    FAIL = "fail"


@dataclass
class DateRangeType:
    begin: Optional[int] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "",
            "required": True,
        },
    )
    end: Optional[int] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "",
            "required": True,
        },
    )


class DispositionType(Enum):
    NONE_VALUE = "none"
    QUARANTINE = "quarantine"
    REJECT = "reject"


@dataclass
class IdentifierType:
    envelope_to: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "",
        },
    )
    envelope_from: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "",
            "required": True,
        },
    )
    header_from: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "",
            "required": True,
        },
    )


class PolicyOverrideType(Enum):
    FORWARDED = "forwarded"
    SAMPLED_OUT = "sampled_out"
    TRUSTED_FORWARDER = "trusted_forwarder"
    MAILING_LIST = "mailing_list"
    LOCAL_POLICY = "local_policy"
    OTHER = "other"


class SpfdomainScope(Enum):
    HELO = "helo"
    MFROM = "mfrom"


class SpfresultType(Enum):
    NONE_VALUE = "none"
    NEUTRAL = "neutral"
    PASS_VALUE = "pass"
    FAIL = "fail"
    SOFTFAIL = "softfail"
    TEMPERROR = "temperror"
    PERMERROR = "permerror"


@dataclass
class DkimauthResultType:
    class Meta:
        name = "DKIMAuthResultType"

    domain: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "",
            "required": True,
        },
    )
    selector: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "",
        },
    )
    result: Optional[DkimresultType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "",
            "required": True,
        },
    )
    human_result: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "",
        },
    )


@dataclass
class PolicyOverrideReason:
    type: Optional[PolicyOverrideType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "",
            "required": True,
        },
    )
    comment: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "",
        },
    )


@dataclass
class PolicyPublishedType:
    domain: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "",
            "required": True,
        },
    )
    adkim: Optional[AlignmentType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "",
        },
    )
    aspf: Optional[AlignmentType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "",
        },
    )
    p: Optional[DispositionType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "",
            "required": True,
        },
    )
    sp: Optional[DispositionType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "",
            "required": True,
        },
    )
    pct: Optional[int] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "",
            "required": True,
        },
    )
    fo: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "",
            "required": True,
        },
    )


@dataclass
class ReportMetadataType:
    org_name: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "",
            "required": True,
        },
    )
    email: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "",
            "required": True,
        },
    )
    extra_contact_info: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "",
        },
    )
    report_id: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "",
            "required": True,
        },
    )
    date_range: Optional[DateRangeType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "",
            "required": True,
        },
    )
    error: List[str] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "",
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
            "namespace": "",
            "required": True,
        },
    )
    scope: Optional[SpfdomainScope] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "",
            "required": True,
        },
    )
    result: Optional[SpfresultType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "",
            "required": True,
        },
    )


@dataclass
class AuthResultType:
    dkim: List[DkimauthResultType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "",
        },
    )
    spf: List[SpfauthResultType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "",
            "min_occurs": 1,
        },
    )


@dataclass
class PolicyEvaluatedType:
    disposition: Optional[DispositionType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "",
            "required": True,
        },
    )
    dkim: Optional[DmarcresultType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "",
            "required": True,
        },
    )
    spf: Optional[DmarcresultType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "",
            "required": True,
        },
    )
    reason: List[PolicyOverrideReason] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "",
        },
    )


@dataclass
class RowType:
    source_ip: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "",
            "required": True,
            "pattern": r"((1?[0-9]?[0-9]|2[0-4][0-9]|25[0-5]).){3}                 (1?[0-9]?[0-9]|2[0-4][0-9]|25[0-5])|                 ([A-Fa-f0-9]{1,4}:){7}[A-Fa-f0-9]{1,4}",
        },
    )
    count: Optional[int] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "",
            "required": True,
        },
    )
    policy_evaluated: Optional[PolicyEvaluatedType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "",
            "required": True,
        },
    )


@dataclass
class RecordType:
    row: Optional[RowType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "",
            "required": True,
        },
    )
    identifiers: Optional[IdentifierType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "",
            "required": True,
        },
    )
    auth_results: Optional[AuthResultType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "",
            "required": True,
        },
    )


@dataclass
class Feedback:
    class Meta:
        name = "feedback"
        namespace = "http://dmarc.org/dmarc-xml/0.1"

    version: Optional[Decimal] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "",
            "required": True,
        },
    )
    report_metadata: Optional[ReportMetadataType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "",
            "required": True,
        },
    )
    policy_published: Optional[PolicyPublishedType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "",
            "required": True,
        },
    )
    record: List[RecordType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "",
            "min_occurs": 1,
        },
    )
