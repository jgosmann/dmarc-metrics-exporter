import bite
import pytest
from bite.parse_functions import parse_bytes

from dmarc_metrics_exporter.imap_parser import (
    fetch_response_line,
    response,
    response_tagged,
    string,
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "given_input, expected",
    [
        (b'"quoted string"', b"quoted string"),
        (b"{14}\r\nliteral string", b"literal string"),
        (b"{13}\r\nwith\r\nnewline", b"with\r\nnewline"),
    ],
)
async def test_parses_strings(given_input, expected):
    parse_tree = await parse_bytes(string, given_input, parse_all=True)
    assert parse_tree.values == (expected,)


RFC822_HEADER = (
    b"Return-Path: <sender@some-domain.org>\r\n"
    b"Received: from 172.10.0.1 "
    b"(HELO xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx); "
    b"Wed Jan 05 10:26:45 UTC 2022\r\n"
    b'Content-Type: text/plain; charset="utf-8"\r\n'
    b"Content-Transfer-Encoding: 7bit\r\n"
    b"MIME-Version: 1.0\r\n"
    b"Subject: Message subject\r\n"
    b"From: sender@some-domain.org\r\n"
    b"To: queue@localhost\r\n\r\n"
)
RFC822_BODY = b"message content\r\n"
RFC822_MESSAGE = RFC822_HEADER + RFC822_BODY


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "given_input, expected",
    [
        # RFC822 body at end
        (
            f"1 FETCH (FLAGS (\\Seen) UID 6 RFC822 {{{len(RFC822_MESSAGE)}}}\r\n".encode(
                "ascii"
            )
            + RFC822_MESSAGE
            + b")",
            (
                1,
                b"FETCH",
                (
                    (b"FLAGS", (b"\\Seen",)),
                    (b"UID", 6),
                    (b"RFC822", RFC822_MESSAGE),
                ),
            ),
        ),
        # RFC822 body followed by flags
        (
            f"2 FETCH (UID 7 RFC822 {{{len(RFC822_MESSAGE)}}}\r\n".encode("ascii")
            + RFC822_MESSAGE
            + b" FLAGS (\\Seen))",
            (
                2,
                b"FETCH",
                (
                    (b"UID", 7),
                    (b"RFC822", RFC822_MESSAGE),
                    (b"FLAGS", (b"\\Seen",)),
                ),
            ),
        ),
        # Test each allowed pair
        # (body is not actually reproduced in the parsed value)
        (
            b'4 FETCH (BODY ("MESSAGE" "text/html" '
            b'("a" "b(") "body-fld-id" "body-fld-desc" "8BIT" 123))',
            (
                4,
                b"FETCH",
                ((b"BODY", ()),),
            ),
        ),
        (
            f"5 FETCH (BODY[] {{{len(RFC822_MESSAGE)}}}\r\n".encode("ascii")
            + RFC822_MESSAGE
            + b")",
            (5, b"FETCH", ((b"BODY", (), RFC822_MESSAGE),)),
        ),
        (
            f"6 FETCH (BODY[]<42> {{{len(RFC822_MESSAGE) - 42}}}\r\n".encode("ascii")
            + RFC822_MESSAGE[42:]
            + b")",
            (6, b"FETCH", (((b"BODY", (), 42, RFC822_MESSAGE[42:])),)),
        ),
        (
            f"7 FETCH (BODY[HEADER] {{{len(RFC822_HEADER)}}}\r\n".encode("ascii")
            + RFC822_HEADER
            + b")",
            (7, b"FETCH", ((b"BODY", (b"HEADER",), RFC822_HEADER),)),
        ),
        (
            b'8 FETCH (BODYSTRUCTURE ("MESSAGE" "text/html" '
            b'("a" "b(") "body-fld-id" "body-fld-desc" "8BIT" 123))',
            (
                8,
                b"FETCH",
                ((b"BODYSTRUCTURE", ()),),
            ),
        ),
        (
            b'9 FETCH (ENVELOPE ("date" "subject" '
            b'(("from" NIL "from" "example.com")) '
            b'(("sender" NIL "sender" "example.com")) NIL '
            b'(("to" NIL "to" "example.com")) NIL NIL NIL "message-id"'
            b"))",
            (
                9,
                b"FETCH",
                (
                    (
                        b"ENVELOPE",
                        (
                            b"date",
                            b"subject",
                            ((b"from", b"NIL", b"from", b"example.com"),),
                            ((b"sender", b"NIL", b"sender", b"example.com"),),
                            b"NIL",
                            ((b"to", b"NIL", b"to", b"example.com"),),
                            b"NIL",
                            b"NIL",
                            b"NIL",
                            b"message-id",
                        ),
                    ),
                ),
            ),
        ),
        (
            b"10 FETCH (FLAGS (\\Seen \\Foo))",
            (10, b"FETCH", ((b"FLAGS", (b"\\Seen", b"\\Foo")),)),
        ),
        (
            b'11 FETCH (INTERNALDATE " 2-Mar-2022 12:34:56 +0200")',
            (11, b"FETCH", ((b"INTERNALDATE", b" 2-Mar-2022 12:34:56 +0200"),)),
        ),
        (
            f"12 FETCH (RFC822 {{{len(RFC822_MESSAGE)}}}\r\n".encode("ascii")
            + RFC822_MESSAGE
            + b")",
            (12, b"FETCH", ((b"RFC822", RFC822_MESSAGE),)),
        ),
        (
            f"13 FETCH (RFC822.HEADER {{{len(RFC822_HEADER)}}}\r\n".encode("ascii")
            + RFC822_HEADER
            + b")",
            (13, b"FETCH", ((b"RFC822.HEADER", RFC822_HEADER),)),
        ),
        (
            b"14 FETCH (RFC822.SIZE 12345)",
            (14, b"FETCH", ((b"RFC822.SIZE", 12345),)),
        ),
        (
            f"15 FETCH (RFC822.TEXT {{{len(RFC822_BODY)}}}\r\n".encode("ascii")
            + RFC822_BODY
            + b")",
            (15, b"FETCH", ((b"RFC822.TEXT", RFC822_BODY),)),
        ),
        (
            b"16 FETCH (UID 42)",
            (
                16,
                b"FETCH",
                ((b"UID", 42),),
            ),
        ),
        (
            b"1 FETCH (FLAGS (\\Seen) BODY[HEADER.FIELDS (SUBJECT)] {24}\r\n"
            b"Subject: Minimal email\r\n)",
            (
                1,
                b"FETCH",
                (
                    (b"FLAGS", (b"\\Seen",)),
                    (
                        b"BODY",
                        (b"HEADER.FIELDS", (b"SUBJECT",)),
                        b"Subject: Minimal email\r\n",
                    ),
                ),
            ),
        ),
        (
            b"1 FETCH (UNKNOWN NIL)",
            (
                1,
                b"FETCH",
                ((b"UNKNOWN", b"NIL"),),
            ),
        ),
        (
            b"1 FETCH (UNKNOWN 123)",
            (
                1,
                b"FETCH",
                ((b"UNKNOWN", 123),),
            ),
        ),
        (
            b'1 FETCH (UNKNOWN "foo")',
            (
                1,
                b"FETCH",
                ((b"UNKNOWN", b"foo"),),
            ),
        ),
        (
            b"1 FETCH (UNKNOWN {3}\r\nfoo)",
            (
                1,
                b"FETCH",
                ((b"UNKNOWN", b"foo"),),
            ),
        ),
        (
            b"1 FETCH (UNKNOWN (foo 123 ({6}\r\nfoobar)))",
            (
                1,
                b"FETCH",
                ((b"UNKNOWN", (b"foo", b"123", (b"foobar",))),),
            ),
        ),
        (
            b"1 FETCH (UNKNOWN.FOO NIL)",
            (
                1,
                b"FETCH",
                ((b"UNKNOWN.FOO", b"NIL"),),
            ),
        ),
        (
            b"1 FETCH (UNKNOWN.FOO[FIELD1 FIELD2 (ITEM1 ITEM2)] NIL)",
            (
                1,
                b"FETCH",
                ((b"UNKNOWN.FOO", b"[FIELD1 FIELD2 (ITEM1 ITEM2)]", b"NIL"),),
            ),
        ),
        (
            b"1 FETCH (UNKNOWN.FOO<42> NIL)",
            (
                1,
                b"FETCH",
                ((b"UNKNOWN.FOO", 42, b"NIL"),),
            ),
        ),
        (
            b"1 FETCH (UNKNOWN.FOO[FIELD1 FIELD2 (ITEM1 ITEM2)]<42> NIL)",
            (
                1,
                b"FETCH",
                ((b"UNKNOWN.FOO", b"[FIELD1 FIELD2 (ITEM1 ITEM2)]", 42, b"NIL"),),
            ),
        ),
    ],
)
async def test_parses_fetch_response_line(given_input, expected):
    parse_tree = await parse_bytes(fetch_response_line, given_input, parse_all=True)
    assert parse_tree.values == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "given_input, expected",
    [
        (b"tag123 OK some text", (b"tag123", b"OK", (b"some text"))),
        (
            b"tag123 OK [UIDNEXT 456] some text",
            (
                b"tag123",
                b"OK",
                (b"UIDNEXT", 456),
                b"some text",
            ),
        ),
        (
            b"tag123 OK [BADCHARSET ({8}\r\nfoo\r\nbar)] some text",
            (
                b"tag123",
                b"OK",
                (
                    b"BADCHARSET",
                    (b"foo\r\nbar",),
                ),
                b"some text",
            ),
        ),
        (
            b"tag123 OK [FOO 123] some text",
            (b"tag123", b"OK", (b"FOO", b"123"), b"some text"),
        ),
    ],
)
async def test_parses_tagged_response_line(given_input, expected):
    parse_tree = await parse_bytes(response_tagged, given_input, parse_all=True)
    assert parse_tree.values == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "given_input",
    [
        b"tag123 OK [BADCHARSET ({8}\r\n",
        b"tag123 OK [BADCHARSET ({8}\r\nfoo\r\n",
    ],
)
async def test_parses_tagged_response_line_exceptions(given_input):
    with pytest.raises(bite.ParseError):
        await parse_bytes(response_tagged, given_input)


@pytest.mark.asyncio
async def test_continue_response():
    given_input = b"+ foobar\r\n"
    parse_tree = await parse_bytes(response, given_input, parse_all=True)
    assert parse_tree.values == (b"+", b"foobar")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "given_input,expected",
    [
        (
            b"* OK IMAP4rev1 Server GreenMail v1.6.5 ready\r\n",
            (
                b"*",
                b"OK",
                b"IMAP4rev1 Server GreenMail v1.6.5 ready",
            ),
        ),
        (b"* BYE cu later alligator\r\n", (b"*", b"BYE", b"cu later alligator")),
        (
            b"* CAPABILITY IMAP4rev1 LITERAL+ SORT UIDPLUS IDLE QUOTA\r\n",
            (
                b"*",
                b"CAPABILITY",
                b"IMAP4rev1 LITERAL+ SORT UIDPLUS IDLE QUOTA",
            ),
        ),
        (b"* 1 EXISTS\r\n", (b"*", 1, b"EXISTS")),
        (b"* 2 EXPUNGE\r\n", (b"*", 2, b"EXPUNGE")),
        (b"* 3 FETCH (UID 42)\r\n", (b"*", 3, b"FETCH", ((b"UID", 42),))),
        (
            b'* foo {10}\r\n0123456789 "xyz" (A B C)\r\n',
            (b"*", b"foo ", b"0123456789", b' "xyz" (A B C)'),
        ),
    ],
)
async def test_untagged_response(given_input, expected):
    parse_tree = await parse_bytes(response, given_input, parse_all=True)
    assert parse_tree.values == expected
