import re

from pyparsing import (
    CaselessKeyword,
    Combine,
    Group,
    Literal,
    Opt,
    Regex,
    StringEnd,
    common,
    dbl_quoted_string,
    remove_quotes,
)
from pyparsing.core import ParserElement
from pyparsing.helpers import counted_array, nested_expr

nil = CaselessKeyword("NIL")
atom_char = Regex(r'[^(){ %*"\\\]\x00-\x1f\x7f-\x9f]')
atom = atom_char[1, ...]
resp_specials = Literal("]")
astring_char = atom_char | resp_specials

literal_string = Combine(
    counted_array(
        Regex(".", re.DOTALL).leave_whitespace(),
        Literal("{").suppress() + common.integer + Literal("}\r\n").suppress(),
    )
)
string = dbl_quoted_string.set_parse_action(remove_quotes) | literal_string

astring = astring_char[1, ...] | string
nstring = string | nil


def parenthesized_list(items_expr: ParserElement) -> ParserElement:
    return Literal("(").suppress() + Group(items_expr[...]) + Literal(")").suppress()


def pair(keyword_expr: ParserElement, expr: ParserElement) -> ParserElement:
    return Group(keyword_expr.set_results_name("key") + expr.set_results_name("value"))


address = parenthesized_list(nstring)

header_field_name = astring
header_list = parenthesized_list(header_field_name)

section_msgtext = (
    CaselessKeyword("HEADER")
    | (CaselessKeyword("HEADER.FIELDS") + Opt(CaselessKeyword(".NOT")) + header_list)
    | CaselessKeyword("TEXT")
)
section_text = section_msgtext | CaselessKeyword("MIME")
section_part = common.integer + (Literal(".").suppress() + common.integer)[...]
section_spec = section_msgtext | (
    Group(section_part + Opt(Literal(".").suppress() + section_text))
)
section = (
    Literal("[").suppress()
    + Opt(section_spec, default="").set_results_name("section")
    + Literal("]").suppress()
)

body_structure = pair(
    CaselessKeyword("BODY") | CaselessKeyword("BODYSTRUCTURE"),
    nested_expr(ignore_expr=string),
)
body_section = pair(
    Group(
        CaselessKeyword("BODY")
        + section
        + Opt(
            Literal("<").suppress() + common.integer + Literal(">").suppress()
        ).set_results_name("offset")
    ),
    nstring,
)
envelope = pair(
    CaselessKeyword("ENVELOPE"),
    parenthesized_list(parenthesized_list(address) | nstring),
)
flag = Combine(Literal("\\") + atom)
flags = pair(CaselessKeyword("FLAGS"), parenthesized_list(flag))
internaldate = pair(
    CaselessKeyword("INTERNALDATE"), dbl_quoted_string.set_parse_action(remove_quotes)
)
rfc822 = pair(CaselessKeyword("RFC822"), nstring)
rfc822_header = pair(CaselessKeyword("RFC822.HEADER"), nstring)
rfc822_text = pair(CaselessKeyword("RFC822.TEXT"), nstring)
rfc822_size = pair(CaselessKeyword("RFC822.SIZE"), common.integer)
uid = pair(CaselessKeyword("UID"), common.integer)
fetch_response_pair = (
    body_section
    | body_structure
    | envelope
    | flags
    | internaldate
    | rfc822
    | rfc822_header
    | rfc822_text
    | rfc822_size
    | uid
)

fetch_response_line = (
    common.integer + CaselessKeyword("FETCH") + parenthesized_list(fetch_response_pair)
)

fetch_response = Group(fetch_response_line[...])

text = Regex(r"[^\r\n]+")
flag_perm = flag | Literal(r"\*")
auth_type = atom
capability = (CaselessKeyword("AUTH=") + auth_type) | atom
capability_data = (
    CaselessKeyword("CAPABILITY")
    + capability[...]
    + CaselessKeyword("IMAP4rev1")
    + capability[...]
)
response_text_code = (
    CaselessKeyword("ALERT")
    | (CaselessKeyword("BADCHARSET") + Opt(parenthesized_list(astring)))
    | capability_data
    | CaselessKeyword("PARSE")
    | (CaselessKeyword("PERMANENTFLAGS") + parenthesized_list(flag_perm))
    | CaselessKeyword("READ-ONLY")
    | CaselessKeyword("READ-WRITE")
    | CaselessKeyword("TRYCREATE")
    | (CaselessKeyword("UIDNEXT") + common.integer)
    | (CaselessKeyword("UIDVALIDITY") + common.integer)
    | (CaselessKeyword("UNSEEN") + common.integer)
    | (atom + Opt(Regex(r"[^\r\r\]]+")))
)
resp_text = Group(
    Opt(Literal("[").suppress() + response_text_code + Literal("]").suppress())
) + (~Literal("[") + text)
resp_cond_state = (
    CaselessKeyword("OK") | CaselessKeyword("NO") | CaselessKeyword("BAD")
) + resp_text
tag = Combine((~Literal("+") + astring_char)[1, ...])
response_tagged = tag.leave_whitespace() + resp_cond_state + StringEnd()
