from aiogram.types import Message, InlineKeyboardMarkup
from aiogram.exceptions import TelegramBadRequest
import logging

async def safe_edit_message(message: Message, text: str, reply_markup: InlineKeyboardMarkup = None, parse_mode: str = "HTML", **kwargs):
    """
    Edits a message's text or caption depending on whether it has a photo.
    Handles 'message is not modified' error.
    """
    try:
        if message.photo:
            await message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode, **kwargs)
        else:
            await message.edit_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode, **kwargs)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            return
        if "message to edit not found" in str(e).lower():
            return
        raise
