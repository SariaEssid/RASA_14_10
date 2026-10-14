"""
tests/unit/test_pdf_rag_pdf.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from unittest.mock import MagicMock, patch
import numpy as np
import pytest

from actions.answer_from_file.answer_from_pdf.pdf_rag_pdf import (
    chunk_text,
    build_index,
    load_pdf_dynamic,
    retrieve_context_pdf,
    read_pdf_from_file,
    pdf_cache
)


# =========================================================
# FIXTURES & MOCK ENGINE INITIALIZATION
# =========================================================

@pytest.fixture(autouse=True)
def clear_pdf_cache():
    """Ensures the global dynamic PDF memory dictionary is empty before each test run."""
    pdf_cache.clear()
    yield
    pdf_cache.clear()


@pytest.fixture
def mock_embedder():
    """Mocks the dynamic embedding generator to return structured dimensions rapidly."""
    with patch("actions.answer_from_file.answer_from_pdf.pdf_rag_pdf.embed_model") as mock_model:
        def side_effect_encode(sentences):
            if isinstance(sentences, str):
                sentences = [sentences]
            return np.random.rand(len(sentences), 8).astype("float32")

        mock_model.encode.side_effect = side_effect_encode
        yield mock_model


# =========================================================
# 1. CHUNK TEXT PARSING TESTS
# =========================================================

def test_chunk_text_basic_splitting():
    """Verify standard paragraph break division and character size boundaries."""
    sample_text = "Paragraph 1 line content.\n\nParagraph 2 line content."
    chunks = chunk_text(sample_text, size=100, overlap=10)

    assert len(chunks) == 2
    assert "Paragraph 1" in chunks[0]
    assert "Paragraph 2" in chunks[1]


def test_chunk_text_with_line_overflow_and_overlap():
    """Test line-by-line assembly when single block lines overflow the size limit.

    This explicitly satisfies the line-overflow logic blocks by processing multiple
    lines inside a single text segment.
    """
    # Line 1 populates current_chunk. Line 2 forces the overflow condition block to execute.
    sample_text = "ShortLineOne\nSuperLongSecondLineThatTriggersAnOverflowCondition"

    chunks = chunk_text(sample_text, size=20, overlap=5)

    assert len(chunks) >= 2
    assert len(chunks) == len(set(chunks))


def test_chunk_text_exceeding_hard_max_limit():
    """Verify that chunks exceeding the absolute hard boundary are clamped safely on line 58."""
    # Single long line without breaks: loops directly to the final size constraint check.
    sample_text = "SuperLongSingleStringBlockWithoutAnyLineBreaks"
    chunks = chunk_text(sample_text, size=10, overlap=2)

    assert len(chunks) == 1
    assert chunks[0] == "SuperLongS"
    assert len(chunks[0]) == 10


# =========================================================
# 2. FAISS INDEX BUILDER TESTS
# =========================================================

def test_build_index_structure(mock_embedder):
    """Verify FAISS structural index creation dimensions matches embedding configurations."""
    chunks = ["Sample chunk layout alpha", "Sample chunk layout beta"]
    index = build_index(chunks)

    assert index.ntotal == 2
    assert index.d == 8


# =========================================================
# 3. DYNAMIC CACHE LOGIC & RAG RETRIEVAL TESTS
# =========================================================

@patch("actions.answer_from_file.answer_from_pdf.pdf_rag_pdf.read_pdf_from_file")
def test_load_pdf_dynamic_caching_lifecycle(mock_read_pdf, mock_embedder):
    """Verify document processing bypasses file parsing upon hitting global cache matches."""
    mock_read_pdf.return_value = "Page content line alpha.\n\nPage content line beta."
    dummy_path = "faked_document_location.pdf"

    first_payload = load_pdf_dynamic(dummy_path)
    assert mock_read_pdf.call_count == 1
    assert len(first_payload["chunks"]) == 2

    second_payload = load_pdf_dynamic(dummy_path)
    assert mock_read_pdf.call_count == 1
    assert second_payload == first_payload


@patch("actions.answer_from_file.answer_from_pdf.pdf_rag_pdf.load_pdf_dynamic")
def test_retrieve_context_pdf_search_execution(mock_load_dynamic, mock_embedder):
    """Verify top-k context retrieval maps search items successfully into string format."""
    chunks_list = ["Apple pie recipe", "Baking structural guides", "Carrot muffin textures", "Donut glazing lines"]
    index = build_index(chunks_list)

    mock_load_dynamic.return_value = {
        "chunks": chunks_list,
        "faiss": index
    }

    context_result = retrieve_context_pdf(query="baking guide", pdf_path="test.pdf", k=2)

    assert isinstance(context_result, str)
    assert "\n\n" in context_result


# =========================================================
# 4. PYPDF FILE READ OPERATIONS
# =========================================================

def test_read_pdf_from_file_parsing(tmp_path):
    """Test standard extraction mechanics using patch mocks for PdfReader class objects."""
    target_file = tmp_path / "mock_document.pdf"
    target_file.write_bytes(b"%PDF-1.4 mock content shell")

    mock_page_1 = MagicMock()
    mock_page_1.mediabox.top = 100
    mock_page_1.mediabox.left = 50
    mock_page_1.extract_text.return_value = "First extracted page content block."

    mock_page_2 = MagicMock()
    mock_page_2.mediabox.top = 200
    mock_page_2.mediabox.left = 50
    mock_page_2.extract_text.return_value = "Second extracted page content block."

    with patch("actions.answer_from_file.answer_from_pdf.pdf_rag_pdf.PdfReader") as MockPdfReader:
        mock_instance = MockPdfReader.return_value
        mock_instance.pages = [mock_page_2, mock_page_1]

        extracted_plain_text = read_pdf_from_file(str(target_file))

        assert extracted_plain_text.startswith("First extracted")
        assert "Second extracted" in extracted_plain_text