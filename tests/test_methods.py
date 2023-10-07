import pytest
import hashlib
from unittest.mock import Mock, AsyncMock
from aiorocketchat.methods import (
    Connect,
    Resume,
    Login,
    GetChannels,
    SendMessage,
    SendReaction,
    SendTypingEvent,
    SubscribeToChannelMessages,
    SubscribeToChannelChanges,
    Unsubscribe,
)
from aiorocketchat.response import WebsocketResponse, ObjectResponse, Channel

pytestmark = pytest.mark.asyncio


def test_connect_get_message():
    expected = {
        "msg": "connect",
        "version": "1",
        "support": ["1"],
    }
    assert Connect.get_message() == expected


async def test_connect_call(protocol_mock):
    await Connect.call(protocol_mock)
    protocol_mock.call_method.assert_called_once()


def test_resume_get_message():
    msg_id = "123"
    token = "sample_token"
    expected = {
        "msg": "method",
        "method": "login",
        "id": msg_id,
        "params": [{"resume": token}],
    }
    assert Resume.get_message(msg_id, token) == expected


async def test_resume_call(protocol_mock):
    result = Resume.parse_response(WebsocketResponse({"result": {"id": "123"}}))
    assert result == ObjectResponse(id="123")


def test_login_get_message():
    msg_id = "123"
    username = "user"
    password = "pass"
    pwd_digest = hashlib.sha256(password.encode()).hexdigest()
    expected = {
        "msg": "method",
        "method": "login",
        "id": msg_id,
        "params": [
            {
                "user": {"username": username},
                "password": {"digest": pwd_digest, "algorithm": "sha-256"},
            }
        ],
    }
    assert Login.get_message(msg_id, username, password) == expected


async def test_login_call(protocol_mock):
    result = Login.parse_response(WebsocketResponse({"result": {"id": "123"}}))
    assert result == "123"


def test_get_channels_get_message():
    msg_id = "123"
    expected = {
        "msg": "method",
        "method": "rooms/get",
        "id": msg_id,
        "params": [],
    }
    assert GetChannels.get_message(msg_id) == expected


async def test_get_channels_call(protocol_mock):
    result = GetChannels.parse_response(
        WebsocketResponse({"result": [{"_id": "123", "t": "channel"}]})
    )
    assert result == [Channel(id="123", type="channel")]
