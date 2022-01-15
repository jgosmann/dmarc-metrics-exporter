import re
from asyncio import IncompleteReadError, StreamReader
from enum import Enum
from typing import AsyncGenerator, Tuple

from pyparsing import ParseException

from .imap_parser import response_tagged


class ImapException(Exception):
    pass


class IncompleteResponse(ImapException):
    pass


class ResponseType(Enum):
    ContinueReq = "+"
    Untagged = "*"
    Tagged = "tagged"


def _parses_as_tagged_response(line: bytes) -> bool:
    try:
        response_tagged.parse_string(line.decode("ascii"), parse_all=True)
        return True
    except ParseException:
        return False


async def parse_imap_responses(
    reader: StreamReader,
) -> AsyncGenerator[Tuple[ResponseType, bytes], None]:
    literal_follows = re.compile(rb".*\{(\d+)\}\r\n$")

    while not reader.at_eof():
        line = await reader.readline()
        if line.startswith(b"+ "):
            yield (ResponseType.ContinueReq, line[2:])
        elif line.startswith(b"* "):
            match = literal_follows.match(line)
            while match:
                try:
                    line += (
                        await reader.readexactly(int(match.group(1)))
                        + await reader.readline()
                    )
                except IncompleteReadError as err:
                    raise IncompleteResponse(line) from err
                match = literal_follows.match(line)
            yield (ResponseType.Untagged, line[2:])
        else:
            while not _parses_as_tagged_response(line):
                if reader.at_eof():
                    raise IncompleteResponse(line)
                line += await reader.readline()
            yield (ResponseType.Tagged, line)
