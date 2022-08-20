from bite import (
    And,
    CaselessLiteral,
    CharacterSet,
    Combine,
    Counted,
    FixedByteCount,
    Forward,
    Literal,
    Opt,
    Parser,
    Suppress,
    TransformValues,
)
from bite.transformers import Group

nil = CaselessLiteral(b"NIL")
atom_char = CharacterSet(
    rb'(){ %*"\]' + bytes(range(0x1F + 1)) + bytes(range(0x7F, 0x9F + 1)), invert=True
)
atom = Combine(atom_char[1, ...])
resp_specials = Literal(b"]")
astring_char = atom_char | resp_specials

sp = Suppress(CharacterSet(b" \t")[1, ...])
crlf = Suppress(Literal(b"\r\n"))

integer = TransformValues(
    Combine(CharacterSet(b"0123456789")[1, ...]),
    lambda values: tuple(int(v) for v in values),
)
literal_string = Counted(
    Suppress(Literal(b"{")) + integer + Suppress(Literal(b"}") + crlf),
    FixedByteCount,
)
dbl_quoted_string = (
    Suppress(Literal(b'"'))
    + Combine(CharacterSet(b'"', invert=True)[0, ...])
    + Suppress(Literal(b'"'))
)
string = dbl_quoted_string | literal_string

astring = Combine(astring_char[1, ...]) | string
nstring = string | nil


def parenthesized_list(items_expr: Parser) -> Parser:
    return Group(
        Suppress(Literal(b"("))
        + Opt(sp)
        + Opt(items_expr + (sp + items_expr)[0, ...])
        + Opt(sp)
        + Suppress(Literal(b")"))
    )


def pair(keyword_expr: Parser, expr: Parser) -> Parser:
    return Group(And([keyword_expr, sp, expr]))


address = parenthesized_list(nstring)

header_field_name = astring
header_list = parenthesized_list(header_field_name)

section_msgtext = (
    (
        CaselessLiteral(b"HEADER.FIELDS")
        + Opt(CaselessLiteral(b".NOT"))
        + Opt(sp)
        + header_list
    )
    | CaselessLiteral(b"HEADER")
    | CaselessLiteral(b"TEXT")
)
section_text = section_msgtext | CaselessLiteral(b"MIME")
section_part = integer + (Suppress(Literal(b".")) + integer)[0, ...]
section_spec = section_msgtext | (
    section_part + Opt(Suppress(Literal(b".")) + section_text)
)
section = Suppress(Literal(b"[")) + Group(Opt(section_spec)) + Suppress(Literal(b"]"))

nested_lists = Forward()
nested_lists.assign(
    parenthesized_list(
        nstring | nested_lists | Combine(CharacterSet(b" )", invert=True)[1, ...])
    )
)


body_structure = Group(
    (CaselessLiteral(b"BODYSTRUCTURE") | CaselessLiteral(b"BODY"))
    + sp
    + Group(Suppress(nested_lists))
)
length = Suppress(Literal(b"<")) + integer + Suppress(Literal(b">"))
body_section = pair(
    CaselessLiteral(b"BODY") + section + Opt(length),
    nstring,
)
envelope = pair(
    CaselessLiteral(b"ENVELOPE"),
    parenthesized_list(parenthesized_list(address) | nstring),
)
flag = Combine(Literal(b"\\") + atom)
flags = pair(CaselessLiteral(b"FLAGS"), parenthesized_list(flag))
internaldate = pair(CaselessLiteral(b"INTERNALDATE"), dbl_quoted_string)
rfc822 = pair(
    CaselessLiteral(b"RFC822"),
    nstring,
)
rfc822_header = pair(CaselessLiteral(b"RFC822.HEADER"), nstring)
rfc822_text = pair(CaselessLiteral(b"RFC822.TEXT"), nstring)
rfc822_size = pair(CaselessLiteral(b"RFC822.SIZE"), integer)
uid = pair(CaselessLiteral(b"UID"), integer)
unknown_fetch_response_pair = pair(
    Combine(CharacterSet(b" \t\r\n[<", invert=True)[1, ...])
    + Opt(
        Combine(Literal(b"[") + CharacterSet(b"]", invert=True)[0, ...] + Literal(b"]"))
    )
    + Opt(length),
    nil | integer | nstring | nested_lists,
)
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
    | unknown_fetch_response_pair
)

fetch_response_line = (
    integer
    + sp
    + CaselessLiteral(b"FETCH")
    + Opt(sp)
    + parenthesized_list(fetch_response_pair)
)

text = Combine(CharacterSet(b"\r\n", invert=True)[0, ...])
flag_perm = flag | Literal(rb"\*")
auth_type = atom
capability = (CaselessLiteral(b"AUTH=") + auth_type) | atom
capability_data = (
    CaselessLiteral(b"CAPABILITY")
    + capability[0, ...]
    + CaselessLiteral(b"IMAP4rev1")
    + capability[0, ...]
)
response_text_code = (
    CaselessLiteral(b"ALERT")
    | Group(CaselessLiteral(b"BADCHARSET") + Opt(sp) + Opt(parenthesized_list(astring)))
    | capability_data
    | CaselessLiteral(b"PARSE")
    | Group(
        CaselessLiteral(b"PERMANENTFLAGS") + Opt(sp) + parenthesized_list(flag_perm)
    )
    | CaselessLiteral(b"READ-ONLY")
    | CaselessLiteral(b"READ-WRITE")
    | CaselessLiteral(b"TRYCREATE")
    | Group(CaselessLiteral(b"UIDNEXT") + sp + integer)
    | Group(CaselessLiteral(b"UIDVALIDITY") + sp + integer)
    | Group(CaselessLiteral(b"UNSEEN") + sp + integer)
    | Group(atom + Opt(sp + Combine(CharacterSet(b"\r\n]", invert=True)[1, ...])))
)
resp_text = Opt(
    Suppress(Literal(b"["))
    + response_text_code
    + Suppress(Literal(b"]"))
    + Suppress(Opt(sp))
) + (~Literal(b"[") + text)
resp_cond_state = (
    CaselessLiteral(b"OK") | CaselessLiteral(b"NO") | CaselessLiteral(b"BAD")
)
tag = ~Literal(b"+") + Combine(astring_char[1, ...])
response_tagged = tag + sp + resp_cond_state + sp + resp_text

server_greeting = Literal(b"OK") + sp + text
server_goodbye = Literal(b"BYE") + sp + text

capability = CaselessLiteral(b"CAPABILITY") + sp + text
response_untagged = (
    Literal(b"*")
    + sp
    + (
        server_goodbye
        | capability
        | (integer + sp + Literal(b"EXISTS"))
        | (integer + sp + Literal(b"EXPUNGE"))
        | fetch_response_line
        | server_greeting
        | (
            (
                Combine(CharacterSet(b"{\r\n", invert=True)[1, ...])
                + Opt(literal_string)
            )[0, ...]
        )
    )
)
response_continue = Literal(b"+") + sp + text
response = (response_continue | response_untagged | response_tagged) + crlf
