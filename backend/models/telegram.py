"""The parts of a Telegram Bot API `Update` the vendor webhook reads; every other field is ignored."""

from pydantic import BaseModel, Field


class Chat(BaseModel):
    id: int


class Voice(BaseModel):
    file_id: str


class Message(BaseModel):
    message_id: int
    chat: Chat
    text: str | None = None
    voice: Voice | None = None
    reply_to_message: "Message | None" = None


class CallbackQuery(BaseModel):
    id: str
    data: str | None = None
    message: Message | None = None


class Update(BaseModel):
    update_id: int
    message: Message | None = None
    callback_query: CallbackQuery | None = None


class Button(BaseModel):
    text: str
    data: str = Field(max_length=64)  # Telegram's limit on callback_data
