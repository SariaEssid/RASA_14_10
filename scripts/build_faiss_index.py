import sys
import os
import logging
import json
import faiss
import numpy as np

# ✅ Make project root importable
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from actions.utils.embedding_loader import get_embedder

log = logging.getLogger("rasa-actions")

data_dir = os.path.join(PROJECT_ROOT, "data")
faiss_index_dir = os.path.join(PROJECT_ROOT, "faiss_index")

def build_faq_index():
    faq_path = os.path.join(data_dir, "faqs.json")
    with open(faq_path, "r", encoding="utf-8") as f:
        faq_data = json.load(f)

    questions = [q["question"] for q in faq_data]
    answers = [q["answer"] for q in faq_data]

    os.makedirs(faiss_index_dir, exist_ok=True)

    answers_path = os.path.join(faiss_index_dir, "answers.json")
    with open(answers_path, "w", encoding="utf-8") as f:
        json.dump(answers, f, ensure_ascii=False, indent=2)

    embedder = get_embedder()  # ✅ loads ONCE
    embeddings = embedder.encode(
        questions,
        normalize_embeddings=True,
        show_progress_bar=True
    )

    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(np.asarray(embeddings))

    index_path = os.path.join(faiss_index_dir, "faiss.index")
    faiss.write_index(index, index_path)

    log.info("✅ FAISS index built successfully")
    print(f"📁 Index: {index_path}")
    print(f"📁 Answers: {answers_path}")
    print(f"📊 Indexed questions: {len(questions)}")

if __name__ == "__main__":
    build_faq_index()