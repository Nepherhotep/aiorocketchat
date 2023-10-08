import hashlib
import time
from abc import ABC, abstractmethod
from typing import Any

from aiorocketchat.exceptions import (
    RocketChatBaseException,
    RocketConnectError,
    RocketResumeError,
    RocketLoginError,
    RocketSendMessageError,
    RocketGetChannelsError,
    RocketSendReactionError,
    RocketSendTypingEventError,
    RocketSubscribeToChannelMessagesError,
    RocketSubscribeToChannelChangesError,
    RocketUnsubscribeError,
)
from aiorocketchat.transport import Transport
from aiorocketchat.response import TransportResponse, BaseResponse, Channel


class BaseRealtimeRequestAbstract(ABC):
    sequence_counter = 0

    @classmethod
    def inc_sequence(cls):
        cls.sequence_counter += 1
        return str(cls.sequence_counter)

    @abstractmethod
    def parse_response(self, response: TransportResponse):
        ...

    @abstractmethod
    def get_message(self, *args, **kwargs):
        ...


class BaseRealtimeRequest(BaseRealtimeRequestAbstract, ABC):
    exception_class = RocketChatBaseException

    def __init__(self, transport: Transport):
        self.transport = transport

    def parse_response(self, response: TransportResponse) -> Any:
        return BaseResponse(id=response.get_field("result", "id"))

    async def call(self, *args) -> BaseResponse:
        msg_id = self.inc_sequence()
        msg = self.get_message(msg_id, *args)
        response = await self.transport.call_method(msg, msg_id)
        self.raise_exceptions(response)
        return self.parse_response(response)

    def raise_exceptions(self, response: TransportResponse):
        error = response.get_field("error")
        if error:
            raise Exception(error)


class Connect(BaseRealtimeRequest):
    exception_class = RocketConnectError

    def get_message(self, *args, **kwargs):
        return {
            "msg": "connect",
            "version": "1",
            "support": ["1"],
        }

    async def call(self) -> TransportResponse:
        await self.transport.call_method(self.get_message())


class Resume(BaseRealtimeRequest):
    """Log in to the service with a token."""

    exception_class = RocketResumeError

    def get_message(self, msg_id, token):
        return {
            "msg": "method",
            "method": "login",
            "id": msg_id,
            "params": [
                {
                    "resume": token,
                }
            ],
        }


class Login(BaseRealtimeRequest):
    """Log in to the service."""

    exception_class = RocketLoginError

    def get_message(self, msg_id, username, password):
        pwd_digest = hashlib.sha256(password.encode()).hexdigest()
        return {
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


class GetChannels(BaseRealtimeRequest):
    """Get a list of channels user is currently member of."""

    exception_class = RocketGetChannelsError

    def get_message(self, msg_id):
        return {
            "msg": "method",
            "method": "rooms/get",
            "id": msg_id,
            "params": [],
        }

    def parse_response(self, response: TransportResponse):
        # Return channel IDs and channel types.
        return [Channel(id=r["_id"], type=r["t"]) for r in response.content["result"]]

    async def call(self):
        msg_id = self.inc_sequence()
        msg = self.get_message(msg_id)
        response = await self.transport.call_method(msg, msg_id)
        return self.parse_response(response)


class SendMessage(BaseRealtimeRequest):
    """Send a text message to a channel."""

    exception_class = RocketSendMessageError

    def get_message(self, msg_id, channel_id, msg_text, thread_id=None):
        id_seed = f"{msg_id}:{time.time()}"
        msg = {
            "msg": "method",
            "method": "sendMessage",
            "id": msg_id,
            "params": [
                {
                    "_id": hashlib.md5(id_seed.encode()).hexdigest()[:12],
                    "rid": channel_id,
                    "msg": msg_text,
                }
            ],
        }
        if thread_id is not None:
            msg["params"][0]["tmid"] = thread_id
        return msg

    async def call(self, msg_text, channel_id, thread_id=None):
        msg_id = self.inc_sequence()
        msg = self.get_message(msg_id, channel_id, msg_text, thread_id)
        await self.transport.call_method(msg, msg_id)


class SendReaction(BaseRealtimeRequest):
    """Send a reaction to a specific message."""

    exception_class = RocketSendReactionError

    def get_message(self, msg_id, orig_msg_id, emoji):
        return {
            "msg": "method",
            "method": "setReaction",
            "id": msg_id,
            "params": [
                emoji,
                orig_msg_id,
            ],
        }

    async def call(self, orig_msg_id, emoji):
        msg_id = self.inc_sequence()
        msg = self.get_message(msg_id, orig_msg_id, emoji)
        await self.transport.call_method(msg)


class SendTypingEvent(BaseRealtimeRequest):
    """Send the `typing` event to a channel."""

    exception_class = RocketSendTypingEventError

    def get_message(self, msg_id, channel_id, username, is_typing):
        return {
            "msg": "method",
            "method": "stream-notify-room",
            "id": msg_id,
            "params": [f"{channel_id}/typing", username, is_typing],
        }

    async def call(self, channel_id, username, is_typing):
        msg_id = self.inc_sequence()
        msg = self.get_message(msg_id, channel_id, username, is_typing)
        await self.transport.call_method(msg, msg_id)


class SubscribeToChannelMessages(BaseRealtimeRequest):
    """Subscribe to all messages in the given channel."""

    exception_class = RocketSubscribeToChannelMessagesError

    def get_message(self, msg_id, channel_id):
        return {
            "msg": "sub",
            "id": msg_id,
            "name": "stream-room-messages",
            "params": [channel_id, {"useCollection": False, "args": []}],
        }

    def _wrap(self, callback):
        def fn(msg):
            event = msg["fields"]["args"][0]  # TODO: This looks suspicious.
            msg_id = event["_id"]
            channel_id = event["rid"]
            thread_id = event.get("tmid")
            sender_id = event["u"]["_id"]
            msg = event["msg"]
            qualifier = event.get("t")
            return callback(channel_id, sender_id, msg_id, thread_id, msg, qualifier)

        return fn

    async def call(self, channel_id, callback):
        # TODO: document the expected interface of the callback.
        msg_id = self.inc_sequence()
        msg = self.get_message(msg_id, channel_id)
        await self.transport.create_subscription(msg, msg_id, self._wrap(callback))
        return BaseResponse(
            id=msg_id
        )  # Return the ID to allow for later unsubscription.


class SubscribeToChannelChanges(BaseRealtimeRequest):
    """Subscribe to all changes in channels."""

    exception_class = RocketSubscribeToChannelChangesError

    def get_message(self, msg_id, user_id):
        return {
            "msg": "sub",
            "id": msg_id,
            "name": "stream-notify-user",
            "params": [f"{user_id}/rooms-changed", False],
        }

    def _wrap(self, callback):
        def fn(msg):
            payload = msg["fields"]["args"]
            if payload[0] == "removed":
                return  # Nothing else to do - channel has just been deleted.
            channel_id = payload[1]["_id"]
            channel_type = payload[1]["t"]
            return callback(channel_id, channel_type)

        return fn

    async def call(self, user_id, callback):
        # TODO: document the expected interface of the callback.
        msg_id = self.inc_sequence()
        msg = self.get_message(msg_id, user_id)
        await self.transport.create_subscription(msg, msg_id, self._wrap(callback))
        return BaseResponse(
            id=msg_id
        )  # Return the ID to allow for later unsubscription.


class Unsubscribe(BaseRealtimeRequest):
    """Cancel a subscription"""

    exception_class = RocketUnsubscribeError

    def get_message(self, subscription_id):
        return {
            "msg": "unsub",
            "id": subscription_id,
        }

    async def call(self, subscription_id):
        msg = self.get_message(subscription_id)
        return await self.transport.call_method(msg)
