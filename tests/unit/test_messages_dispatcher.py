# noinspection PyPackageRequirements
"""
@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

import pytest
from unittest.mock import MagicMock, patch
from rasa_sdk.executor import CollectingDispatcher

from actions.utils.messages_dispatcher import MessageDispatcher

# 👉 FIX: Points to the exact file containing MessageDispatcher & FEEDBACK_BUTTONS imports
PATCH_TARGET = "actions.utils.messages_dispatcher"


# ==============================================================================
# FIXTURES & INITIAL STATE SETUP
# ==============================================================================

@pytest.fixture
def mock_dispatcher() -> MagicMock:
    return MagicMock(spec=CollectingDispatcher)


@pytest.fixture(autouse=True)
def mock_feedback_buttons():
    """Mock FEEDBACK_BUTTONS to isolate fallback button verification configurations."""
    fallback_buttons = [{"title": "Default", "payload": "/affirm"}]
    with patch(f"{PATCH_TARGET}.FEEDBACK_BUTTONS", fallback_buttons):
        yield fallback_buttons


# ==============================================================================
# 1. INPUT VALIDATION & GUARD TESTS
# ==============================================================================

@pytest.mark.parametrize("invalid_msg", [None, "", 123, [], {}])
def test_send_secure_invalid_message_guards(mock_dispatcher, invalid_msg):
    with patch(f"{PATCH_TARGET}.log") as mock_log:
        MessageDispatcher.send_secure(mock_dispatcher, invalid_msg)
        mock_log.warning.assert_called_once()
        mock_dispatcher.utter_message.assert_not_called()


# ==============================================================================
# 2. SANITIZATION & STRIP UTIL TESTS
# ==============================================================================

def test_sanitize_message_xss_and_newlines():
    harmful_input = "Line 1\\n<script>alert('xss')</script>Line 2   \n   Line 3"
    expected_output = "Line 1\nalert('xss')Line 2\nLine 3"

    clean_msg = MessageDispatcher._sanitize_message(harmful_input)
    assert clean_msg == expected_output


def test_adjust_lines_utility():
    assert MessageDispatcher._djust_lines("Part1\\nPart2") == "Part1\nPart2"


# ==============================================================================
# 3. TEXT-ONLY STRATEGY DIRECT DISPATCH TESTS ("JUST TEXT")
# ==============================================================================

def test_send_simple_text_single_line(mock_dispatcher):
    MessageDispatcher.send_secure(mock_dispatcher, "Hello World", with_buttons=False, with_images=False)
    mock_dispatcher.utter_message.assert_called_once_with(text="Hello World")


def test_send_simple_text_multi_line_skips_empty(mock_dispatcher):
    multi_line_msg = "Line 1\n\nLine 2"
    MessageDispatcher.send_secure(mock_dispatcher, multi_line_msg, with_buttons=False, with_images=False)

    assert mock_dispatcher.utter_message.call_count == 2
    mock_dispatcher.utter_message.assert_any_call(text="Line 1")
    mock_dispatcher.utter_message.assert_any_call(text="Line 2")


# ==============================================================================
# 4. BUTTONS-ONLY STRATEGY TESTS ("BTN")
# ==============================================================================

def test_send_with_buttons_single_line_explicit(mock_dispatcher):
    custom_buttons = [{"title": "Option A", "payload": "/choice_a"}]
    MessageDispatcher.send_secure(
        mock_dispatcher, "Single Part", with_buttons=True, buttons=custom_buttons, with_images=False
    )
    mock_dispatcher.utter_message.assert_called_once_with(text="Single Part", buttons=custom_buttons)


def test_send_with_buttons_single_line_fallback(mock_dispatcher, mock_feedback_buttons):
    MessageDispatcher.send_secure(mock_dispatcher, "Single Part", with_buttons=True, buttons=None, with_images=False)
    mock_dispatcher.utter_message.assert_called_once_with(text="Single Part", buttons=mock_feedback_buttons)


def test_send_with_buttons_multi_line(mock_dispatcher, mock_feedback_buttons):
    multi_line_msg = "Intro Line\nMiddle Line\nFinal Call to Action"
    MessageDispatcher.send_secure(mock_dispatcher, multi_line_msg, with_buttons=True, buttons=None, with_images=False)

    assert mock_dispatcher.utter_message.call_count == 3
    mock_dispatcher.utter_message.assert_any_call(text="Intro Line")
    mock_dispatcher.utter_message.assert_any_call(text="Middle Line")
    mock_dispatcher.utter_message.assert_any_call(text="Final Call to Action", buttons=mock_feedback_buttons)


# ==============================================================================
# 5. BUTTONS + IMAGES STRATEGY TESTS ("BTN + IMG")
# ==============================================================================

def test_send_with_buttons_and_images_single_line(mock_dispatcher, mock_feedback_buttons):
    img_list = ["encoded_string_xyz"]
    MessageDispatcher.send_secure(
        mock_dispatcher, "Single Part Img", with_buttons=True, buttons=None,
        with_images=True, images=img_list, post_fix_msg="Post text"
    )
    mock_dispatcher.utter_message.assert_called_once_with(
        text="Single Part Img",
        image=f"data:image/jpeg;base64,{img_list}",
        buttons=mock_feedback_buttons
    )


def test_send_with_buttons_and_images_multi_line(mock_dispatcher, mock_feedback_buttons):
    multi_line_msg = "Description Part 1\nDescription Part 2"
    img_list = ["img_1_b64", "img_2_b64"]

    MessageDispatcher.send_secure(
        mock_dispatcher, multi_line_msg, with_buttons=True, buttons=None,
        with_images=True, images=img_list, post_fix_msg="End notes"
    )

    assert mock_dispatcher.utter_message.call_count == 5
    mock_dispatcher.utter_message.assert_any_call(text="Description Part 1")
    mock_dispatcher.utter_message.assert_any_call(text="Description Part 2")
    mock_dispatcher.utter_message.assert_any_call(image="data:image/jpeg;base64,img_1_b64")
    mock_dispatcher.utter_message.assert_any_call(image="data:image/jpeg;base64,img_2_b64")
    mock_dispatcher.utter_message.assert_any_call(text="End notes", buttons=mock_feedback_buttons)