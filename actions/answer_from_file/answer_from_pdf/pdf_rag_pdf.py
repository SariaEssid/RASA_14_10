"""
actions/answer_from_file/answer_from_pdf/pdf_rag_pdf.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from pypdf import PdfReader
from actions.logging.logging_helpers import log_info_text
from actions.settings.settings import settings
from actions.utils.embedding_loader import get_embedder

import os
import faiss

# ---------------------------------------------------------
#  🔥 GLOBAL CACHE for PDFs
# ---------------------------------------------------------
# This cache stores already-read PDFs along with their chunks and FAISS index.
# Keys: absolute PDF path
# Values: {"chunks": [...], "faiss": index}

pdf_cache = {}
embed_model = get_embedder()

def chunk_text(text, size=settings.CHUNK_SIZE, overlap=settings.CHUNK_OVERLAP):
    """
    Divise le texte en morceaux en priorisant les séparations structurelles
    (doubles sauts de ligne, puis lignes simples) avant d'appliquer la limite de taille.
    Ceci rend le chunking plus "dynamique" face à la structure du document (tableaux, listes).
    """

    chunks = get_chunks(text, size, overlap)

    # S'assurer que les chunks ne dépassent pas la taille maximale, et éliminer les doublons
    final_chunks = []
    for chunk in chunks:
        # S'assurer de respecter la taille limite après l'assemblage
        if len(chunk) > size:
            # Si un chunk est trop grand (ce qui ne devrait pas arriver souvent avec cette logique),
            # le découper à la taille limite pour éviter les erreurs de modèle.
            final_chunks.append(chunk[:size])
        else:
            final_chunks.append(chunk)

    # Utilisation d'un set pour éliminer les doublons causés par l'overlap simple.
    return sorted(list(set(final_chunks)), key=final_chunks.index)


# ---------------------------------------------------------
# 🔥 Load PDF dynamically, with caching
# ---------------------------------------------------------
def load_pdf_dynamic(pdf_path: str):
    """
    Load PDF → chunk → embed → FAISS.
    Cached so next calls are instant.
    """
    global pdf_cache

    pdf_path = os.path.abspath(pdf_path)

    # Return cached data if available
    if pdf_path in pdf_cache:
        log_info_text("RAG", f"TAKE PDF FROM CACHE: {os.path.basename(pdf_path)}")
        return pdf_cache[pdf_path]

    # 1) Read PDF
    text = read_pdf_from_file(pdf_path)

    # 2) Chunk text
    chunks = chunk_text(text)

    # 3) Build FAISS index
    index = build_index(chunks)

    # 4) Cache for future use
    pdf_cache[pdf_path] = {
        "chunks": chunks,
        "faiss": index,
    }
    log_info_text("RAG", f"TAKE PDF FROM PATH: {os.path.basename(pdf_path)}")
    return pdf_cache[pdf_path]

def build_index(chunks):

    embeddings = embed_model.encode(chunks).astype("float32")
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    return index

# ---------------------------------------------------------
# 🔥 Retrieve context (top-k relevant chunks)
# ---------------------------------------------------------
def retrieve_context_pdf(query, pdf_path: str, k: int = 4):
    """
    Retrieve top-k chunks for a given query from a given PDF.
    """
    data = load_pdf_dynamic(pdf_path)

    chunks = data["chunks"]
    index = data["faiss"]

    query_embed = embed_model.encode([query]).astype("float32")
    distances, I = index.search(query_embed, k)

    # Return concatenated top-k chunks
    return "\n\n".join(chunks[i] for i in I[0])

def read_pdf_from_file(path: str) -> str:
    """Read PDF and return its plain text, sorted by page position."""
    with open(path, "rb") as f:
        reader = PdfReader(f)
        text = ""
        # Sort pages by top, then left
        pages = sorted(reader.pages, key=lambda p: (p.mediabox.top, p.mediabox.left))
        for page in pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def get_chunks(text, size, overlap):
    # 1. Diviser le texte en blocs plus larges basés sur des séparateurs forts (paragraphes, tableaux)
    # Dans ce type de PDF, "\n\n" sépare souvent les sections de contenu importantes.
    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]

    chunks = []

    for block in blocks:
        current_chunk = ""

        # 2. Dans chaque bloc, tenter de diviser par lignes pour capturer des enregistrements complets
        lines = [l.strip() for l in block.split("\n") if l.strip()]

        for line in lines:
            # Si l'ajout de la ligne actuelle dépasse la taille, finaliser le chunk précédent
            if len(current_chunk) + len(line) + 1 > size and current_chunk:
                chunks.append(current_chunk)

                # Le nouveau chunk commence avec la ligne actuelle, plus un chevauchement si possible
                # Le chevauchement est implémenté en réinjectant une partie de l'ancien chunk

                # Trouver la fin du chevauchement de l'ancien chunk
                overlap_text = current_chunk[-overlap:]

                # Trouver le dernier séparateur pour commencer l'overlap proprement
                last_separator = max(overlap_text.rfind("."), overlap_text.rfind("\n"))
                if last_separator > 0:
                    overlap_text = overlap_text[last_separator + 1:].strip()

                current_chunk = overlap_text + " " + line + " "

            else:
                # Sinon, ajouter simplement la ligne au chunk actuel
                current_chunk += line + " "

        # Ajouter le dernier chunk du bloc si non vide
        if current_chunk:
            chunks.append(current_chunk)

    return chunks