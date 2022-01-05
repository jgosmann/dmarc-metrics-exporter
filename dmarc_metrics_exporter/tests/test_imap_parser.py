import pytest

from dmarc_metrics_exporter.imap_parser import fetch_response_line, string


@pytest.mark.parametrize(
    "given_string, expected",
    [
        ('"quoted string"', "quoted string"),
        ("{14}\r\nliteral string", "literal string"),
        ("{13}\r\nwith\r\nnewline", "with\r\nnewline"),
    ],
)
def test_parses_strings(given_string, expected):
    assert string.parse_string(given_string).as_list() == [expected]


RFC822_HEADER = (
    "Return-Path: <sender@some-domain.org>\r\n"
    "Received: from 172.10.0.1 "
    "(HELO xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx); "
    "Wed Jan 05 10:26:45 UTC 2022\r\n"
    'Content-Type: text/plain; charset="utf-8"\r\n'
    "Content-Transfer-Encoding: 7bit\r\n"
    "MIME-Version: 1.0\r\n"
    "Subject: Message subject\r\n"
    "From: sender@some-domain.org\r\n"
    "To: queue@localhost\r\n\r\n"
)
RFC822_BODY = "message content\r\n"
RFC822_MESSAGE = f"{RFC822_HEADER}{RFC822_BODY}"


@pytest.mark.parametrize(
    "given_string, expected",
    [
        # RFC822 body at end
        (
            f"1 FETCH (FLAGS (\\Seen) UID 6 RFC822 {{{len(RFC822_MESSAGE)}}}\r\n"
            + RFC822_MESSAGE
            + ")\r\n",
            [
                1,
                "FETCH",
                [
                    ["FLAGS", ["\\Seen"]],
                    ["UID", 6],
                    ["RFC822", RFC822_MESSAGE],
                ],
            ],
        ),
        # RFC822 body followed by flags
        (
            f"2 FETCH (UID 7 RFC822 {{{len(RFC822_MESSAGE)}}}\r\n"
            + RFC822_MESSAGE
            + "FLAGS (\\Seen))\r\n",
            [
                2,
                "FETCH",
                [
                    ["UID", 7],
                    ["RFC822", RFC822_MESSAGE],
                    ["FLAGS", ["\\Seen"]],
                ],
            ],
        ),
        # Test each allowed pair
        (
            '4 FETCH (BODY ("MESSAGE" "text/html" '
            '("a" "b(") "body-fld-id" "body-fld-desc" "8BIT" 123))\r\n',
            [
                4,
                "FETCH",
                [
                    [
                        "BODY",
                        [
                            "MESSAGE",
                            "text/html",
                            ["a", "b("],
                            "body-fld-id",
                            "body-fld-desc",
                            "8BIT",
                            "123",
                        ],
                    ]
                ],
            ],
        ),
        (
            f"5 FETCH (BODY[] {{{len(RFC822_MESSAGE)}}}\r\n{RFC822_MESSAGE})\r\n",
            [5, "FETCH", [[["BODY", ""], RFC822_MESSAGE]]],
        ),
        (
            f"6 FETCH (BODY[]<42> {{{len(RFC822_MESSAGE) - 42}}}\r\n{RFC822_MESSAGE[42:]}))\r\n",
            [6, "FETCH", [[["BODY", "", 42], RFC822_MESSAGE[42:]]]],
        ),
        (
            f"7 FETCH (BODY[HEADER] {{{len(RFC822_HEADER)}}}\r\n{RFC822_HEADER})\r\n",
            [7, "FETCH", [[["BODY", "HEADER"], RFC822_HEADER]]],
        ),
        (
            '8 FETCH (BODYSTRUCTURE ("MESSAGE" "text/html" '
            '("a" "b(") "body-fld-id" "body-fld-desc" "8BIT" 123))\r\n',
            [
                8,
                "FETCH",
                [
                    [
                        "BODYSTRUCTURE",
                        [
                            "MESSAGE",
                            "text/html",
                            ["a", "b("],
                            "body-fld-id",
                            "body-fld-desc",
                            "8BIT",
                            "123",
                        ],
                    ]
                ],
            ],
        ),
        (
            '9 FETCH (ENVELOPE ("date" "subject" '
            '(("from" NIL "from" "example.com")) '
            '(("sender" NIL "sender" "example.com")) NIL '
            '(("to" NIL "to" "example.com")) NIL NIL NIL "message-id"'
            "))\r\n",
            [
                9,
                "FETCH",
                [
                    [
                        "ENVELOPE",
                        [
                            "date",
                            "subject",
                            [["from", "NIL", "from", "example.com"]],
                            [["sender", "NIL", "sender", "example.com"]],
                            "NIL",
                            [["to", "NIL", "to", "example.com"]],
                            "NIL",
                            "NIL",
                            "NIL",
                            "message-id",
                        ],
                    ]
                ],
            ],
        ),
        (
            "10 FETCH (FLAGS (\\Seen \\Foo))\r\n",
            [10, "FETCH", [["FLAGS", ["\\Seen", "\\Foo"]]]],
        ),
        (
            '11 FETCH (INTERNALDATE " 2-Mar-2022 12:34:56 +0200")\r\n',
            [11, "FETCH", [["INTERNALDATE", " 2-Mar-2022 12:34:56 +0200"]]],
        ),
        (
            f"12 FETCH (RFC822 {{{len(RFC822_MESSAGE)}}}\r\n{RFC822_MESSAGE})\r\n",
            [12, "FETCH", [["RFC822", RFC822_MESSAGE]]],
        ),
        (
            f"13 FETCH (RFC822.HEADER {{{len(RFC822_HEADER)}}}\r\n{RFC822_HEADER})\r\n",
            [13, "FETCH", [["RFC822.HEADER", RFC822_HEADER]]],
        ),
        ("14 FETCH (RFC822.SIZE 12345)\r\n", [14, "FETCH", [["RFC822.SIZE", 12345]]]),
        (
            f"15 FETCH (RFC822.TEXT {{{len(RFC822_BODY)}}}\r\n{RFC822_BODY})\r\n",
            [15, "FETCH", [["RFC822.TEXT", RFC822_BODY]]],
        ),
        ("16 FETCH (UID 42)\r\n", [16, "FETCH", [["UID", 42]]]),
    ],
)
def test_parses_fetch_response_line(given_string, expected):
    assert fetch_response_line.parse_string(given_string).as_list() == expected
