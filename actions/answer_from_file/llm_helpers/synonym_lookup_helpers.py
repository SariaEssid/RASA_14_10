"""
actions/answer_from_file/common_helpers.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from __future__ import annotations

import os

import yaml

from actions.logging.logging_helpers import log_info_text


def get_synonyms_lookup(action_label, entities):
    entity_slot_mapping = load_entity_slot_mapping("domain.yml", entities)
    synonyms_lookup = load_synonyms_grouped_by_entity(find_conf_file_path(action_label, "data", "nlu.yml"), entities, entity_slot_mapping)
    return synonyms_lookup

def load_synonyms_grouped_by_entity(nlu_file_path, requested_entities, entity_slot_mapping):
    """
    entity_slot_mapping example:
    {
        "speciality": ["math", "tic", "elct_mkn"],
        "session": ["session_25-26", "session_24-25"],
        "grade": ["lcom", "maitre_assistant"]
    }
    """

    grouped_synonyms = {entity: {} for entity in requested_entities}

    with open(nlu_file_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    for item in data.get("nlu", []):

        if "synonym" not in item:
            continue

        slot_name = item["synonym"]

        # 👇 Detect entity of this slot
        entity_name = None
        for entity, slots in entity_slot_mapping.items():
            if slot_name in slots:
                entity_name = entity
                break

        if entity_name not in requested_entities:
            continue

        examples_block = item.get("examples", "")

        synonyms = [
            line.strip("- ").strip()
            for line in examples_block.split("\n")
            if line.strip()
        ]

        grouped_synonyms[entity_name][slot_name] = synonyms

    return grouped_synonyms

def load_entity_slot_mapping(domain_path: str, required_slots: list):
    with open(domain_path, "r", encoding="utf-8") as f:
        domain = yaml.safe_load(f)

    slots = domain.get("slots", {})

    entity_slot_mapping = {}

    for slot_name, slot_data in slots.items():
        if slot_name in required_slots:
            if slot_data.get("type") == "categorical":
                entity_slot_mapping[slot_name] = slot_data.get("values", [])

    # log_info_text(action_label, "ESSID - ENTITIES" + str(entity_slot_mapping))
    return entity_slot_mapping

def find_conf_file_path(action_label, folder_label, file_name):
    # 1. On part de l'emplacement du fichier actuel (common_helpers.py)
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # 2. On remonte de deux niveaux pour arriver à la racine 'chatbot_RASA'
    # actions/answer_from_file -> actions -> chatbot_RASA
    project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))

    # 3. On construit le chemin vers le dossier data
    if folder_label is None:
        file_path = os.path.join(project_root, file_name)
    else:
        file_path = os.path.join(project_root, folder_label, file_name)

    if not os.path.exists(file_path):
        # Optionnel : chercher directement à la racine au cas où
        nlu_path_root = os.path.join(project_root, file_name)
        if os.path.exists(nlu_path_root):
            return nlu_path_root

        raise FileNotFoundError(f"{file_name} introuvable. Chemin testé : {file_path}")

    log_info_text(action_label, "ESSID path" + file_path)
    return file_path