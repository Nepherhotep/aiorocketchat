import pytest
import hashlib
from unittest.mock import Mock, AsyncMock, ANY
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
from aiorocketchat.response import WebsocketResponse, BaseResponse, Channel

pytestmark = pytest.mark.asyncio


async def test_connect_get_message():
    expected = {
        "msg": "connect",
        "version": "1",
        "support": ["1"],
    }
    assert Connect.get_message() == expected


async def test_connect_parse_response(protocol_mock):
    await Connect.call(protocol_mock)
    protocol_mock.call_method.assert_called_once()


async def test_resume_get_message():
    msg_id = "123"
    token = "sample_token"
    expected = {
        "msg": "method",
        "method": "login",
        "id": msg_id,
        "params": [{"resume": token}],
    }
    assert Resume.get_message(msg_id, token) == expected


async def test_resume_parse_response(protocol_mock):
    result = Resume.parse_response(WebsocketResponse({"result": {"id": "123"}}))
    assert result == BaseResponse(id="123")


async def test_login_get_message():
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


async def test_login_parse_response(protocol_mock):
    result = Login.parse_response(WebsocketResponse({"result": {"id": "123"}}))
    assert result == BaseResponse(id="123")


async def test_get_channels_get_message():
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


async def test_send_message():
    msg_id = "123"
    channel = "channel1"
    message = "Hello, World!"
    expected = {
        "id": "123",
        "method": "sendMessage",
        "msg": "method",
        "params": [{"_id": ANY, "msg": "Hello, World!", "rid": "channel1"}],
    }
    assert SendMessage.get_message(msg_id, channel, message) == expected


async def test_send_message_parse_response(protocol_mock):
    result = SendMessage.parse_response(WebsocketResponse({"result": {"id": "123"}}))
    assert result == BaseResponse(id="123")


# Test for SendReaction
async def test_send_reaction_get_message():
    msg_id = "123"
    emoji = ":smile:"
    message_id = "456"
    expected = {
        "id": "123",
        "method": "setReaction",
        "msg": "method",
        "params": ["456", ":smile:"],
    }
    assert SendReaction.get_message(msg_id, emoji, message_id) == expected


async def test_send_reaction_parse_response(protocol_mock):
    result = SendReaction.parse_response(WebsocketResponse({"result": {"id": "123"}}))
    assert result == BaseResponse(id="123")


async def test_send_typing_event_get_message():
    msg_id = "123"
    channel_id = "channel1"
    username = "user1"
    is_typing = True
    expected = {
        "msg": "method",
        "method": "stream-notify-room",
        "id": msg_id,
        "params": [f"{channel_id}/typing", username, is_typing],
    }
    assert (
        SendTypingEvent.get_message(msg_id, channel_id, username, is_typing) == expected
    )


async def test_send_typing_event_parse_response():
    response_content = {"result": {"id": "123"}}
    result = SendTypingEvent.parse_response(WebsocketResponse(response_content))
    assert result == BaseResponse(id="123")


async def test_subscribe_to_channel_messages_get_message():
    msg_id = "123"
    channel_id = "channel1"
    expected = {
        "msg": "sub",
        "id": msg_id,
        "name": "stream-room-messages",
        "params": [channel_id, {"useCollection": False, "args": []}],
    }
    assert SubscribeToChannelMessages.get_message(msg_id, channel_id) == expected


async def test_subscribe_to_channel_messages_parse_response():
    response_content = {
        "fields": {
            "args": [
                {
                    "_id": "msg123",
                    "rid": "channel1",
                    "tmid": None,
                    "u": {"_id": "user1"},
                    "msg": "Hello",
                    "t": None,
                }
            ]
        }
    }
    callback_mock = Mock()
    wrapped_callback = SubscribeToChannelMessages._wrap(callback_mock)
    wrapped_callback(response_content)
    callback_mock.assert_called_once_with(
        "channel1", "user1", "msg123", None, "Hello", None
    )


async def test_subscribe_to_channel_changes_get_message():
    msg_id = "123"
    user_id = "user1"
    expected = {
        "msg": "sub",
        "id": msg_id,
        "name": "stream-notify-user",
        "params": [f"{user_id}/rooms-changed", False],
    }
    assert SubscribeToChannelChanges.get_message(msg_id, user_id) == expected


async def test_subscribe_to_channel_changes_parse_response_added():
    response_content = {
        "fields": {"args": ["added", {"_id": "channel1", "t": "channel"}]}
    }
    callback_mock = Mock()
    wrapped_callback = SubscribeToChannelChanges._wrap(callback_mock)
    wrapped_callback(response_content)
    callback_mock.assert_called_once_with("channel1", "channel")


async def test_subscribe_to_channel_changes_parse_response_removed():
    response_content = {
        "fields": {"args": ["removed", {"_id": "channel1", "t": "channel"}]}
    }
    callback_mock = Mock()
    wrapped_callback = SubscribeToChannelChanges._wrap(callback_mock)
    wrapped_callback(response_content)
    callback_mock.assert_not_called()


async def test_unsubscribe_get_message():
    subscription_id = "sub123"
    expected = {
        "msg": "unsub",
        "id": subscription_id,
    }
    assert Unsubscribe.get_message(subscription_id) == expected


async def test_unsubscribe_get_response():
    response = Unsubscribe.parse_response(WebsocketResponse({"result": {"id": "123"}}))
    assert response == BaseResponse(id="123")
