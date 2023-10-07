from typing import Any


class Protocol:
    def call_method(self, *args, **kwargs):
        pass


class Response:
    def __init__(self, content: dict):
        self.content = content

    def get_field(self, *fields: str) -> Any:
        content = self.content
        for field in fields:
            content = content.get(field, {})
        return content or None
