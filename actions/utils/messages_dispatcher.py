"""
actions/utils/messages_dispatcher.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

"""
Unified message dispatcher to eliminate code duplication
Replaces multiple message sending functions with a single, consistent interface
"""

from typing import Text, List, Optional, Dict
from rasa_sdk.executor import CollectingDispatcher
from actions.constants.Constants import FEEDBACK_BUTTONS

import logging

log = logging.getLogger("rasa-actions")

class MessageDispatcher:
    """Unified message dispatcher with consistent formatting and security"""

    @staticmethod
    def send_secure(
            dispatcher: CollectingDispatcher,
            message: Text,
            with_buttons: bool = False,
            buttons: Optional[List[Dict]] = None,
            message_type: str = "info",
            with_images: bool = False,
            images: List[Text] = None,
            post_fix_msg: Optional[Text] = None
    ) -> None:

        if not message or not isinstance(message, str):
            log.warning(f"Attempted to send empty or invalid message: {message}")
            return

        # Clean and secure the message
        clean_msg = MessageDispatcher._sanitize_message(message)

        # Choose sending strategy
        if with_buttons and not with_images:
            log.info("🎯   BTN")
            MessageDispatcher._send_with_buttons(dispatcher, clean_msg, buttons)
        elif with_buttons and with_images:
            log.info("🎯   BTN + IMG")
            MessageDispatcher._send_with_buttons_and_images(dispatcher, clean_msg, buttons, images, post_fix_msg)
        else:
            log.info("🎯   JUST TEXT")
            MessageDispatcher._send_simple(dispatcher, clean_msg)

        # Log the message dispatch
        MessageDispatcher._log_dispatch(clean_msg, message_type, with_buttons)

    @staticmethod
    def _sanitize_message(message: Text) -> Text:
        """Sanitize and normalize message content"""
        # Replace escaped newlines with actual newlines
        clean_msg = message.replace("\\n", "\n")

        # Remove potential harmful characters (basic XSS protection)
        clean_msg = clean_msg.replace("<script>", "").replace("</script>", "")

        # Trim excessive whitespace
        clean_msg = "\n".join(line.strip() for line in clean_msg.split("\n"))

        return clean_msg

    @staticmethod
    def _send_with_buttons(
            dispatcher: CollectingDispatcher,
            message: Text,
            buttons: Optional[List[Dict]] = None
    ) -> None:
        """Send message with buttons using optimal formatting"""
        lines = MessageDispatcher._get_split_reply(message)

        if len(lines) <= 1:
            # Single line message with buttons
            dispatcher.utter_message(text=message, buttons=buttons or FEEDBACK_BUTTONS)
        else:
            # Multi-line message: all but last line without buttons, last line with buttons
            msg_part_1 = '\n'.join(lines[:-1])
            msg_part_2 = lines[-1]

            for line in msg_part_1.splitlines():
                if line.strip():  # Skip empty lines
                    dispatcher.utter_message(text=line)

            dispatcher.utter_message(text=msg_part_2, buttons=buttons or FEEDBACK_BUTTONS)


    @staticmethod
    def _send_with_buttons_and_images(
            dispatcher: CollectingDispatcher,
            message: Text,
            buttons: Optional[List[Dict]] = None,
            images: Optional[List[Text]] = None,
            post_fix_msg: Optional[Text] = None
    ) -> None:
        """Send message with buttons using optimal formatting"""
        lines = MessageDispatcher._get_split_reply(message)

        if len(lines) <= 1:
            # Single line message with buttons
            dispatcher.utter_message(text=message, image=f"data:image/jpeg;base64,{images}", buttons=buttons or FEEDBACK_BUTTONS)
        else:
            # Multi-line message: all but last line without buttons, last line with buttons
            msg_part_1 = '\n'.join(lines[:-1])
            msg_part_2 = lines[-1]

            for line in msg_part_1.splitlines():
                if line.strip():  # Skip empty lines
                    dispatcher.utter_message(text=line)

            dispatcher.utter_message(text=msg_part_2)

            for img in images:
                dispatcher.utter_message(image=f"data:image/jpeg;base64,{img}")
            dispatcher.utter_message(text=post_fix_msg, buttons=buttons or FEEDBACK_BUTTONS)

    @staticmethod
    def _send_simple(dispatcher: CollectingDispatcher, message: Text) -> None:
        """Send simple multi-line message"""
        lines = MessageDispatcher._get_split_reply(message)
        for line in lines:
            if line.strip():  # Skip empty lines
                dispatcher.utter_message(text=line)

    @staticmethod
    def _log_dispatch(message: Text, message_type: str, with_buttons: bool) -> None:
        """Log message dispatch for monitoring"""
        button_info = "with buttons" if with_buttons else "without buttons"
        log.debug(f"📤 Message dispatched ({message_type}, {button_info}): {message}...")

    @staticmethod
    def _get_split_reply(reply):
        return reply.split('\n')

    @staticmethod
    def _djust_lines(answer):
        return answer.replace("\\n", "\n")
