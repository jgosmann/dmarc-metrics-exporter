import re
from asyncio import IncompleteReadError, StreamReader
from enum import Enum
from typing import Tuple

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


# pylint: disable=too-few-public-methods
class ImapReader:
    LITERAL_FOLLOWS = re.compile(rb".*\{(\d+)\}\r\n$")

    def __init__(self, reader: StreamReader):
        self.reader = reader

    async def read_response(self) -> Tuple[ResponseType, bytes]:
        line = await self.reader.readline()
        if line.startswith(b"+ "):
            return (ResponseType.ContinueReq, line[2:])
        elif line.startswith(b"* "):
            match = self.LITERAL_FOLLOWS.match(line)
            while match:
                try:
                    line += (
                        await self.reader.readexactly(int(match.group(1)))
                        + await self.reader.readline()
                    )
                except IncompleteReadError as err:
                    raise IncompleteResponse(line) from err
                match = self.LITERAL_FOLLOWS.match(line)
            return (ResponseType.Untagged, line[2:])
        else:
            while not self._parses_as_tagged_response(line):
                if self.reader.at_eof():
                    raise IncompleteResponse(line)
                line += await self.reader.readline()
            return (ResponseType.Tagged, line)

    @classmethod
    def _parses_as_tagged_response(cls, line: bytes) -> bool:
        try:
            response_tagged.parse_string(line.decode("ascii"), parse_all=True)
            return True
        except ParseException as err:
            print(err)
            return False
