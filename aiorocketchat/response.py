from collections import namedtuple
from typing import Any


class WebsocketResponse:
    def __init__(self, content: dict):
        self.content = content

    def get_field(self, *fields: str) -> Any:
        content = self.content
        for field in fields:
            content = content.get(field, {})
        return content or None


# a common response, where the object with id is returned
BaseResponse = namedtuple("BaseResponse", ["id"])
Channel = namedtuple("Channel", ["id", "type"])
