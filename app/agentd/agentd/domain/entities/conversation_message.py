from dataclasses import dataclass
from datetime import datetime
from typing import Literal

MessageRole = Literal["system", "user", "assistant", "tool"]


@dataclass(frozen=True, slots=True)
class ConversationMessage:
    role: MessageRole
    content: str
    created_at: datetime