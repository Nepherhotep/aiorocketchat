class RocketChatBaseException(Exception):
    """Base class for exceptions in this module."""


class RocketLoginError(RocketChatBaseException):
    """Exception raised when login fails."""


class RocketConnectError(RocketChatBaseException):
    """Exception raised when connecting to Rocket.Chat fails."""


class RocketResumeError(RocketChatBaseException):
    """Exception raised when resuming a session fails."""


class RocketGetChannelsError(RocketChatBaseException):
    """Exception raised when getting channels fails."""


class RocketSendMessageError(RocketChatBaseException):
    """Exception raised when sending a message fails."""


class RocketSendReactionError(RocketChatBaseException):
    """Exception raised when sending a reaction fails."""


class RocketSendTypingEventError(RocketChatBaseException):
    """Exception raised when sending a typing event fails."""


class RocketSubscribeToChannelMessagesError(RocketChatBaseException):
    """Exception raised when subscribing to channel messages fails."""


class RocketSubscribeToChannelChangesError(RocketChatBaseException):
    """Exception raised when subscribing to channel changes fails."""


class RocketUnsubscribeError(RocketChatBaseException):
    """Exception raised when unsubscribing from a channel fails."""
