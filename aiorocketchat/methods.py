import hashlib
import time
from abc import ABC, abstractmethod

from aiorocketchat.protocol import Protocol, Response


class RealtimeRequest(ABC):
    sequence_counter = 0

    @classmethod
    def inc_sequence(cls):
        cls.sequence_counter += 1
        return cls.sequence_counter

    @classmethod
    @abstractmethod
    def parse_response(cls, response: Response):
        ...

    @classmethod
    @abstractmethod
    def get_message(cls, *args, **kwargs):
        ...


class Connect(RealtimeRequest):
    """Initialize the connection."""

    @classmethod
    def get_message(cls, *args, **kwargs):
        return {
            "msg": "connect",
            "version": "1",
            "support": ["1"],
        }

    @classmethod
    async def call(cls, protocol: Protocol) -> Response:
        return await protocol.call_method(cls.get_message())


class Resume(RealtimeRequest):
    """Log in to the service with a token."""

    @classmethod
    def get_message(cls, msg_id, token):
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

    @classmethod
    def parse_response(cls, response: Response):
        return response.get_field("result", "id")

    @classmethod
    async def call(cls, protocol: Protocol, token):
        msg_id = cls.inc_sequence()
        msg = cls.get_message(msg_id, token)
        response = await protocol.call_method(msg, msg_id)
        return cls.parse_response(response)


class Login(RealtimeRequest):
    """Log in to the service."""

    @classmethod
    def get_message(cls, msg_id, username, password):
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

    @classmethod
    def parse_response(cls, response: Response):
        return response.get_field("result", "id")

    @classmethod
    async def call(cls, protocol: Protocol, username, password):
        msg_id = cls.inc_sequence()
        msg = cls.get_message(msg_id, username, password)
        response = await protocol.call_method(msg, msg_id)
        return cls.parse_response(response)


class GetChannels(RealtimeRequest):
    """Get a list of channels user is currently member of."""

    @classmethod
    def get_message(cls, msg_id):
        return {
            "msg": "method",
            "method": "rooms/get",
            "id": msg_id,
            "params": [],
        }

    @classmethod
    def parse_response(cls, response: Response):
        # Return channel IDs and channel types.
        return [(r["_id"], r["t"]) for r in response.content["result"]]

    @classmethod
    async def call(cls, protocol: Protocol):
        msg_id = cls.inc_sequence()
        msg = cls.get_message(msg_id)
        response = await protocol.call_method(msg, msg_id)
        return cls.parse_response(response)


class SendMessage(RealtimeRequest):
    """Send a text message to a channel."""

    @classmethod
    def get_message(cls, msg_id, channel_id, msg_text, thread_id=None):
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

    @classmethod
    async def call(cls, protocol: Protocol, msg_text, channel_id, thread_id=None):
        msg_id = cls.inc_sequence()
        msg = cls.get_message(msg_id, channel_id, msg_text, thread_id)
        await protocol.call_method(msg, msg_id)


class SendReaction(RealtimeRequest):
    """Send a reaction to a specific message."""

    @classmethod
    def get_message(cls, msg_id, orig_msg_id, emoji):
        return {
            "msg": "method",
            "method": "setReaction",
            "id": msg_id,
            "params": [
                emoji,
                orig_msg_id,
            ],
        }

    @classmethod
    async def call(cls, protocol: Protocol, orig_msg_id, emoji):
        msg_id = cls.inc_sequence()
        msg = cls.get_message(msg_id, orig_msg_id, emoji)
        await protocol.call_method(msg)


class SendTypingEvent(RealtimeRequest):
    """Send the `typing` event to a channel."""

    @classmethod
    def get_message(cls, msg_id, channel_id, username, is_typing):
        return {
            "msg": "method",
            "method": "stream-notify-room",
            "id": msg_id,
            "params": [f"{channel_id}/typing", username, is_typing],
        }

    @classmethod
    async def call(cls, protocol: Protocol, channel_id, username, is_typing):
        msg_id = cls.inc_sequence()
        msg = cls.get_message(msg_id, channel_id, username, is_typing)
        await protocol.call_method(msg, msg_id)


class SubscribeToChannelMessages(RealtimeRequest):
    """Subscribe to all messages in the given channel."""

    @classmethod
    def get_message(cls, msg_id, channel_id):
        return {
            "msg": "sub",
            "id": msg_id,
            "name": "stream-room-messages",
            "params": [channel_id, {"useCollection": False, "args": []}],
        }

    @classmethod
    def _wrap(cls, callback):
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

    @classmethod
    async def call(cls, protocol: Protocol, channel_id, callback):
        # TODO: document the expected interface of the callback.
        msg_id = cls.inc_sequence()
        msg = cls.get_message(msg_id, channel_id)
        await protocol.create_subscription(msg, msg_id, cls._wrap(callback))
        return msg_id  # Return the ID to allow for later unsubscription.


class SubscribeToChannelChanges(RealtimeRequest):
    """Subscribe to all changes in channels."""

    @classmethod
    def get_message(cls, msg_id, user_id):
        return {
            "msg": "sub",
            "id": msg_id,
            "name": "stream-notify-user",
            "params": [f"{user_id}/rooms-changed", False],
        }

    @classmethod
    def _wrap(cls, callback):
        def fn(msg):
            payload = msg["fields"]["args"]
            if payload[0] == "removed":
                return  # Nothing else to do - channel has just been deleted.
            channel_id = payload[1]["_id"]
            channel_type = payload[1]["t"]
            return callback(channel_id, channel_type)

        return fn

    @classmethod
    async def call(cls, protocol: Protocol, user_id, callback):
        # TODO: document the expected interface of the callback.
        msg_id = cls.inc_sequence()
        msg = cls.get_message(msg_id, user_id)
        await protocol.create_subscription(msg, msg_id, cls._wrap(callback))
        return msg_id  # Return the ID to allow for later unsubscription.


class Unsubscribe(RealtimeRequest):
    """Cancel a subscription"""

    @classmethod
    def get_message(cls, subscription_id):
        return {
            "msg": "unsub",
            "id": subscription_id,
        }

    @classmethod
    async def call(cls, protocol: Protocol, subscription_id):
        msg = cls.get_message(subscription_id)
        await protocol.call_method(msg)
