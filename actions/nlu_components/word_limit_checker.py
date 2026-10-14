"""
actions/nlu_components/word_limit_checker.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from typing import Any, Dict, List, Text
from rasa.engine.graph import GraphComponent, ExecutionContext
from rasa.engine.recipes.default_recipe import DefaultV1Recipe
from rasa.shared.nlu.training_data.message import Message
from rasa.shared.nlu.training_data.training_data import TrainingData

import logging
log = logging.getLogger("rasa-actions")

@DefaultV1Recipe.register(
    DefaultV1Recipe.ComponentType.MESSAGE_TOKENIZER,  # ensures it fits early in the pipeline
    is_trainable=False
)
class WordLimitChecker(GraphComponent):
    """Custom component that limits user input to 200 words."""

    @classmethod
    def create(
        cls,
        config: Dict[Text, Any],
        name: Text,
        resource: Any,
        context: ExecutionContext,
    ) -> "WordLimitChecker":
        """Create the component with proper signature (Rasa 3.6.1)."""
        return cls()

    # ☠
    def process_training_data(self, training_data: TrainingData) -> TrainingData:
        """No special training-time behavior needed."""
        log.info("process_training_data")
        return training_data

    def process(self, messages: List[Message]) -> List[Message]:
        log.info("process")
        """Check message word count and override intent if too long."""
        for message in messages:
            text = message.get("text", "")
            if text:
                word_count = len(text.split())
                if word_count > 200:
                    # force intent to too_long_input
                    message.set("intent", {"name": "too_long_input", "confidence": 1.0})
        return messages
