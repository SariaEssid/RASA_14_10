"""
actions/answer_from_file/answer_from_markdown/experts_rag/markdown_store.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from __future__ import annotations
from typing import List
from actions.actions import normalize_text
from actions.constants.Constants import EM_SPEC, TIC_SPEC, GC_SPEC, MATH_SPEC, SE_PTP_SSCOMP, DISSER_SSCOMP, SP_SSCOMP, \
    CP_SSCOMP, RDI_SSCOMP, DOSS_SSCOMP, ElJ_SSCOMP, FLAG_ALERT
from actions.constants.EntitiesMapping import ALL_SPECIAITIES
from actions.logging.logging_helpers import log_info_text

import re

def parse_markdown_sections(markdown_text: str):
    sections = []
    current_title = "Root"
    current_content = []

    for line in markdown_text.splitlines():
        line = line.strip()
        # Headings like ## 1 - Composante 1
        m = re.match(r'^(#+)\s+(.*)$', line)
        if m:
            if current_content:
                sections.append({"title": current_title, "content": "\n".join(current_content)})
            current_title = m.group(2)
            current_content = []
        else:
            if line:
                current_content.append(line)

    if current_content:
        sections.append({"title": current_title, "content": "\n".join(current_content)})
    return sections


def table_to_narrative_e(markdown_table: str) -> str:
    lines = [l.strip() for l in markdown_table.strip().split('\n') if l.strip()]
    if len(lines) < 2: return markdown_table

    # Extract headers: split and remove empty strings from ends
    headers = [h.strip().replace('**', '') for h in lines[0].split('|') if h.strip()]

    # If the second line is a separator (contains ---), skip it; otherwise, it's data
    start_index = 1
    if len(lines) > 1 and '---' in lines[1]:
        start_index = 2

    rows = lines[start_index:]
    narrative_output = []

    for row in rows:
        # Split by | and remove the first/last empty elements caused by outer pipes
        cells = [c.strip().replace('**', '') for c in row.split('|')]
        if row.startswith('|'): cells.pop(0)
        if row.endswith('|'): cells.pop()

        line_parts = []
        # Zip headers and cells to ensure they stay aligned regardless of count
        for i, header in enumerate(headers):
            val = cells[i] if i < len(cells) else ""

            # Clean up empty/filler values
            if val in ["-", ".", "", " "]:
                line_parts.append(f"{header}: NON_SPECIFIE")
            else:
                line_parts.append(f"{header}: {val}")

        if line_parts:
            narrative_output.append("LIGNE_OFFICIELLE: " + " | ".join(line_parts))

    return "\n".join(narrative_output)

def table_to_narrative_d(markdown_table: str) -> str:
    lines = markdown_table.strip().split('\n')
    if len(lines) < 3: return markdown_table

    headers = [h.strip() for h in lines[0].split('|') if h.strip()]
    rows = lines[2:]
    narrative_output = []

    for row in rows:
        if not row.strip() or '|' not in row: continue
        # On ne filtre pas les cellules vides ici pour garder l'indexation par rapport aux headers
        cells = [c.strip().replace('**', '') for c in row.split('|')]
        if row.startswith('|'): cells.pop(0)
        if row.strip().endswith('|'): cells.pop()

        line_parts = []
        for i in range(len(headers)):
            if i < len(cells):
                val = cells[i].strip()
                if val in ["-", ".", "", " "]:
                    line_parts.append(f"{headers[i]}: NON_SPECIFIE")
                else:
                    line_parts.append(f"{headers[i]}: {val}")

        if line_parts:
            # IMPORTANT : On garde toute la ligne pour que "Production RDI" soit présent
            narrative_output.append("LIGNE_OFFICIELLE: " + " | ".join(line_parts))

    return "\n".join(narrative_output)

def retrieve_sections_with_table_dynamic_bb(sections, question, top_k=3):
    question_lower = question.lower()
    question_tokens = question_lower.split()
    scored = []

    # 1. Définition des spécialités pour filtrage strict
    specialites_maitre = [
        f"{TIC_SPEC}",
        f"{EM_SPEC}",
        f"{GC_SPEC}",
        f"{MATH_SPEC}",
        "génie énergétique developpement durable",
        "langues communication"
    ]

    # Identifier quelle spécialité l'utilisateur mentionne OKEY
    target_specialite = next((s for s in specialites_maitre if s in question_lower), None)

    keywords_weight = {
        "dossier": 5, "jury": 5, "entretien": 5,
        "tic": 4, "technologies": 4, "production": 4, "rdi": 6
    }

    for s in sections:
        title_lower = s['title'].lower()
        content_lower = s['content'].lower()
        text_full = f"{title_lower} {content_lower}".replace("|", " ").replace("<br>", " ")

        # --- LOGIQUE ANTI-HALLUCINATION ---
        # Si l'utilisateur demande une spécialité précise, on ignore les sections
        # qui ne mentionnent pas cette spécialité dans leur contenu ou titre.
        if target_specialite and target_specialite not in text_full:
            continue

        score = 0
        for token in question_tokens:
            if token in text_full:
                score += keywords_weight.get(token, 1)
            if token in title_lower:
                score += 3

        if score > 0:
            scored.append((score, s))

    scored.sort(reverse=True, key=lambda x: x[0])
    return [s for _, s in scored[:top_k]]

ROW_ANCHORS = {
    f"{RDI_SSCOMP}": ["2.2", "RDI"],
    f"{CP_SSCOMP}": ["2.1.1", "capsules"],
    f"{DOSS_SSCOMP}": ["3.1", "Dossier"],
    f"{SE_PTP_SSCOMP}": ["2.1.2"],
    f"{ElJ_SSCOMP}": ["3.2"],
    f"{DISSER_SSCOMP}": ["1.2", "1.2.1", "1.2.2"],
    f"{SP_SSCOMP}": ["2.1.3"]
}

def extract_cell_value(narrative_text: str, specialite: str, composante: str) -> str | None:
    # Use clean anchors to avoid dash/hyphen issues
    val = None
    anchors = ROW_ANCHORS.get(composante, [])

    log_info_text("ESSID-1 anchors : ", str(anchors))

    for line in narrative_text.splitlines():
        if "LIGNE_OFFICIELLE" not in line:
            log_info_text(f"{FLAG_ALERT}", "SKIPPED without LIGNE_OFFICIELLE")
            continue

        line_lower = line.lower()
        log_info_text("ESSID-2 line_lower : ", line_lower)

        # Check anchors (e.g., '3.1' or 'dossier')
        # Use str(a).lower() in line_lower for maximum compatibility
        if anchors and not any(str(a).lower() in line_lower for a in anchors):
            log_info_text(f"{FLAG_ALERT}", "SKIPPED anchors NOT IN " + line_lower)
            continue


        # Regex: find the specialty name, skip the colon, catch everything until the next |
        # This handles 'Électromécanique: Name1, Name2' perfectly.
        log_info_text("ESSID-3 line 1 : ", normalize_text(specialite))
        log_info_text("ESSID-3 line 2 : ", normalize_text(line))
        pattern = rf"{re.escape(normalize_text(specialite))}\s*:\s*([^|]+)"
        log_info_text("ESSID-3 pattern : ", str(pattern))
        m = re.search(pattern, normalize_text(line), re.IGNORECASE)
        log_info_text("ESSID-3 m : ", str(m))

        val = None
        if m:
            val = m.group(1).strip()
            log_info_text(f"{FLAG_ALERT}", "GET val " + val.upper())
            log_info_text("ESSID-4 val : ", str(val))
            if val not in ["NON_SPECIFIE", "-", "."]:
                return val

    return val.upper()


###################################################
def retrieve_sections_with_table_dynamic(sections, question, top_k=3):
    question_tokens = question.lower().split()
    scored = []

    for s in sections:
        text = f"{s['title']} {s['content']}".replace("|", " ").replace("<br>", " ").lower()
        score = sum(2 if t in s['title'].lower() else 1 for t in question_tokens if t in text)
        if score > 0:
            scored.append((score, s))

    scored.sort(reverse=True, key=lambda x: x[0])
    return [s for _, s in scored[:top_k]]

def table_to_narrative_b(markdown_table: str) -> str:
    lines = markdown_table.strip().split('\n')
    if len(lines) < 3:
        return markdown_table

    # 1. Extraction des headers en conservant les colonnes vides (on enlève juste les bords)
    raw_headers = [h.strip() for h in lines[0].split('|')]
    headers = [h for h in raw_headers if h]  # Liste propre des titres de colonnes

    rows = lines[2:]
    narrative_output = []

    for row in rows:
        if not row.strip() or '|' not in row:
            continue

        # 2. Découpage strict par '|' sans filtrer les cellules vides
        cells = [c.strip().replace('<br/>', ' ').replace('<br>', ' ').replace('**', '') for c in row.split('|')]

        # On retire les éléments vides créés par les pipes extérieurs |...|
        if row.strip().startswith('|'): cells.pop(0)
        if row.strip().endswith('|'): cells.pop()

        # 3. Mapping Header <-> Cellule par index strict
        line_parts = []
        # On utilise le nombre de headers pour itérer
        for i in range(len(headers)):
            if i < len(cells):
                val = cells[i].strip()
                # On ignore les tirets (-) et les cellules vides dans le texte final
                if val and val not in ["-", ".", ""]:
                    line_parts.append(f"{headers[i]}: {val}")

        if line_parts:
            narrative_output.append("- " + " / ".join(line_parts))

    return "\n".join(narrative_output)

def parse_specialities_from_question(question: str) -> list:

    detected = []
    log_info_text("***** QUESTION ", question)
    for speciality in ALL_SPECIAITIES:
        log_info_text("==========> UNIT ", speciality)
        if speciality in question:
            log_info_text("----------> OK + ", speciality)
            detected.append(speciality)

    return detected