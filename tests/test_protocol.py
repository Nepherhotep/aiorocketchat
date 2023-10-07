import pytest

from aiorocketchat.response import WebsocketResponse


def test_response_initialization():
    content = {"name": "John", "age": 30}
    response = WebsocketResponse(content)
    assert response.content == content


@pytest.mark.parametrize(
    "content,fields,expected",
    [
        ({"name": "John"}, ["name"], "John"),
        ({"user": {"profile": {"name": "John"}}}, ["user", "profile", "name"], "John"),
        ({"name": "John"}, ["address"], None),
        ({"user": {"profile": {"name": "John"}}}, ["user", "address", "city"], None),
        ({"result": {"id": "123"}}, ["result", "id"], "123"),
    ],
)
def test_get_nested_fields(content, fields, expected):
    response = WebsocketResponse(content)
    assert response.get_field(*fields) == expected
