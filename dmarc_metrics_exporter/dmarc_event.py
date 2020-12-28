from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class Meta:
    reporter: str
    from_domain: str
    dkim_domain: str
    spf_domain: str


class Disposition(Enum):
    NONE_VALUE = "none"
    QUARANTINE = "quarantine"
    REJECT = "reject"


@dataclass(frozen=True)
class DmarcResult:
    disposition: Disposition
    dkim_pass: bool
    spf_pass: bool
    dkim_aligned: bool
    spf_aligned: bool

    @property
    def dmarc_compliant(self) -> bool:
        return (self.dkim_aligned and self.dkim_pass) or (
            self.spf_aligned and self.spf_pass
        )


@dataclass(frozen=True)
class DmarcEvent:
    count: int
    meta: Meta
    result: DmarcResult
