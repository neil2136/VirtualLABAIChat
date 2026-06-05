class ConversationError(Exception):
    pass


class ConversationNotFoundError(ConversationError):
    pass


class ConversationExpiredError(ConversationError):
    pass


class ConversationAccessDeniedError(ConversationError):
    pass