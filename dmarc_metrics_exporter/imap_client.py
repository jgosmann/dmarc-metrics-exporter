from asyncio import StreamReader
from enum import Enum
from typing import Tuple


class ParseError(Exception):
    pass


class ResponseType(Enum):
    ContinueReq = "+"
    Untagged = "*"
    Tagged = "tagged"


# pylint: disable=too-few-public-methods
class ImapReader:
    def __init__(self, reader: StreamReader):
        self.reader = reader

    async def read_response(self) -> Tuple[ResponseType, bytes]:
        line = await self.reader.readline()
        if line.startswith(b"+ "):
            return (ResponseType.ContinueReq, line[2:])
        raise ParseError(line)
