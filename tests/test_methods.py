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
from aiorocketchat.response import TransportResponse, BaseResponse, Channel

pytestmark = pytest.mark.asyncio


async def test_connect_get_message(mock_transport):
    expected = {
        "msg": "connect",
        "version": "1",
        "support": ["1"],
    }
    assert Connect(mock_transport).get_message() == expected


async def test_connect_parse_response(mock_transport):
    await Connect(mock_transport).call()
    mock_transport.call_method.assert_called_once()


async def test_resume_get_message(mock_transport):
    msg_id = "123"
    token = "sample_token"
    expected = {
        "msg": "method",
        "method": "login",
        "id": msg_id,
        "params": [{"resume": token}],
    }
    assert Resume(mock_transport).get_message(msg_id, token) == expected


async def test_resume_parse_response(mock_transport):
    result = Resume(mock_transport).parse_response(
        TransportResponse({"result": {"id": "123"}})
    )
    assert result == BaseResponse(id="123")


async def test_login_get_message(mock_transport):
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
    assert Login(mock_transport).get_message(msg_id, username, password) == expected


async def test_login_parse_response(mock_transport):
    result = Login(mock_transport).parse_response(
        TransportResponse({"result": {"id": "123"}})
    )
    assert result == BaseResponse(id="123")


async def test_get_channels_get_message(mock_transport):
    msg_id = "123"
    expected = {
        "msg": "method",
        "method": "rooms/get",
        "id": msg_id,
        "params": [],
    }
    assert GetChannels(mock_transport).get_message(msg_id) == expected


async def test_get_channels_call(mock_transport):
    result = GetChannels(mock_transport).parse_response(
        TransportResponse(
            {"result": [{"_id": "123", "t": "channel"}, {"_id": "222", "t": "channel"}]}
        )
    )
    assert result == [
        Channel(id="123", type="channel"),
        Channel(id="222", type="channel"),
    ]


async def test_send_message(mock_transport):
    msg_id = "123"
    channel = "channel1"
    message = "Hello, World!"
    expected = {
        "id": "123",
        "method": "sendMessage",
        "msg": "method",
        "params": [{"_id": ANY, "msg": "Hello, World!", "rid": "channel1"}],
    }
    assert SendMessage(mock_transport).get_message(msg_id, channel, message) == expected


async def test_send_message_parse_response(mock_transport):
    result = SendMessage(mock_transport).parse_response(
        TransportResponse({"result": {"id": "123"}})
    )
    assert result == BaseResponse(id="123")


# Test for SendReaction
async def test_send_reaction_get_message(mock_transport):
    msg_id = "123"
    emoji = ":smile:"
    message_id = "456"
    expected = {
        "id": "123",
        "method": "setReaction",
        "msg": "method",
        "params": ["456", ":smile:"],
    }
    assert (
        SendReaction(mock_transport).get_message(msg_id, emoji, message_id) == expected
    )


async def test_send_reaction_parse_response(mock_transport):
    result = SendReaction(mock_transport).parse_response(
        TransportResponse({"result": {"id": "123"}})
    )
    assert result == BaseResponse(id="123")


async def test_send_typing_event_get_message(mock_transport):
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
        SendTypingEvent(mock_transport).get_message(
            msg_id, channel_id, username, is_typing
        )
        == expected
    )


async def test_send_typing_event_parse_response(mock_transport):
    response_content = {"result": {"id": "123"}}
    result = SendTypingEvent(mock_transport).parse_response(
        TransportResponse(response_content)
    )
    assert result == BaseResponse(id="123")


async def test_subscribe_to_channel_messages_get_message(mock_transport):
    msg_id = "123"
    channel_id = "channel1"
    expected = {
        "msg": "sub",
        "id": msg_id,
        "name": "stream-room-messages",
        "params": [channel_id, {"useCollection": False, "args": []}],
    }
    assert (
        SubscribeToChannelMessages(mock_transport).get_message(msg_id, channel_id)
        == expected
    )


async def test_subscribe_to_channel_messages_parse_response(mock_transport):
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
    wrapped_callback = SubscribeToChannelMessages(mock_transport)._wrap(callback_mock)
    wrapped_callback(response_content)
    callback_mock.assert_called_once_with(
        "channel1", "user1", "msg123", None, "Hello", None
    )


async def test_subscribe_to_channel_changes_get_message(mock_transport):
    msg_id = "123"
    user_id = "user1"
    expected = {
        "msg": "sub",
        "id": msg_id,
        "name": "stream-notify-user",
        "params": [f"{user_id}/rooms-changed", False],
    }
    assert (
        SubscribeToChannelChanges(mock_transport).get_message(msg_id, user_id)
        == expected
    )


async def test_subscribe_to_channel_changes_parse_response_added(mock_transport):
    response_content = {
        "fields": {"args": ["added", {"_id": "channel1", "t": "channel"}]}
    }
    callback_mock = Mock()
    wrapped_callback = SubscribeToChannelChanges(mock_transport)._wrap(callback_mock)
    wrapped_callback(response_content)
    callback_mock.assert_called_once_with("channel1", "channel")


async def test_subscribe_to_channel_changes_parse_response_removed(mock_transport):
    response_content = {
        "fields": {"args": ["removed", {"_id": "channel1", "t": "channel"}]}
    }
    callback_mock = Mock()
    wrapped_callback = SubscribeToChannelChanges(mock_transport)._wrap(callback_mock)
    wrapped_callback(response_content)
    callback_mock.assert_not_called()


async def test_unsubscribe_get_message(mock_transport):
    subscription_id = "sub123"
    expected = {
        "msg": "unsub",
        "id": subscription_id,
    }
    assert Unsubscribe(mock_transport).get_message(subscription_id) == expected


async def test_unsubscribe_get_response(mock_transport):
    response = Unsubscribe(mock_transport).parse_response(
        TransportResponse({"result": {"id": "123"}})
    )
    assert response == BaseResponse(id="123")
