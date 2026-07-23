"""
Heading-Aware Chunker — splits page text into semantically coherent chunks.

Strategy:
  1. Split full page text by heading markers (# / ## / ###)
  2. Each heading + its content below = one chunk candidate
  3. If a candidate exceeds CHUNK_MAX_TOKENS → split further by paragraphs
  4. If a candidate is below CHUNK_MIN_TOKENS → merge with the next chunk
  5. Every chunk retains: page metadata, breadcrumb, and heading_path
"""
import re
import uuid
from dataclasses import dataclass, field
from typing import Optional

import tiktoken

from ingestion.config import CHUNK_MAX_TOKENS, CHUNK_MIN_TOKENS
from ingestion.notion_crawler import PageData
from ingestion.text_extractor import extract_page_text

# Use cl100k_base tokenizer (compatible with most modern models)
_TOKENIZER = tiktoken.get_encoding("cl100k_base")


@dataclass
class Chunk:
    """A single text chunk ready for embedding and storage."""
    chunk_id: str
    document_id: str           # Notion page ID
    content: str               # Actual text content of this chunk
    heading_path: str          # e.g. "2. Six-Step Process > 2.1 Self-Assessment"
    breadcrumb: str            # e.g. "HR Framework > Performance Review"
    page_title: str
    chunk_index: int           # Position of this chunk within the page (0-based)
    token_count: int


def count_tokens(text: str) -> int:
    """Count the number of tokens in a text string."""
    return len(_TOKENIZER.encode(text))


def chunk_page(page: PageData) -> list[Chunk]:
    """
    Main entry point: convert a PageData object into a list of Chunk objects.
    """
    full_text = extract_page_text(page)
    raw_sections = _split_by_headings(full_text)
    chunks: list[Chunk] = []

    for section_heading, section_text in raw_sections:
        # Build the heading path for this section
        heading_path = _build_heading_path(section_heading)
        combined = f"{section_heading}\n{section_text}".strip() if section_heading else section_text.strip()

        token_count = count_tokens(combined)

        if token_count > CHUNK_MAX_TOKENS:
            # Section too large → split further by paragraph
            sub_chunks = _split_by_paragraphs(
                heading=section_heading,
                text=section_text,
            )
        else:
            sub_chunks = [combined]

        for sub in sub_chunks:
            sub = sub.strip()
            if not sub:
                continue
            tc = count_tokens(sub)
            if tc < CHUNK_MIN_TOKENS and chunks:
                # Too small → merge into the previous chunk
                prev = chunks[-1]
                merged_content = prev.content + "\n\n" + sub
                chunks[-1] = Chunk(
                    chunk_id=prev.chunk_id,
                    document_id=prev.document_id,
                    content=merged_content,
                    heading_path=prev.heading_path,
                    breadcrumb=prev.breadcrumb,
                    page_title=prev.page_title,
                    chunk_index=prev.chunk_index,
                    token_count=count_tokens(merged_content),
                )
            else:
                chunks.append(Chunk(
                    chunk_id=str(uuid.uuid4()),
                    document_id=page.page_id,
                    content=sub,
                    heading_path=heading_path,
                    breadcrumb=page.breadcrumb,
                    page_title=page.title,
                    chunk_index=len(chunks),
                    token_count=tc,
                ))

    return chunks


# ── Helpers ───────────────────────────────────────────────────────────────────

def _split_by_headings(text: str) -> list[tuple[str, str]]:
    """
    Split text into (heading, content) pairs at every Markdown heading line.
    The first segment (before any heading) uses an empty string as the heading.
    """
    # Match lines starting with # heading markers
    heading_pattern = re.compile(r"^(#{1,3} .+)$", re.MULTILINE)
    positions = [(m.start(), m.group()) for m in heading_pattern.finditer(text)]

    if not positions:
        # No headings found → treat entire text as one section
        return [("", text)]

    sections: list[tuple[str, str]] = []

    # Content before the first heading (if any)
    if positions[0][0] > 0:
        pre_text = text[: positions[0][0]].strip()
        if pre_text:
            sections.append(("", pre_text))

    # Each heading + content until the next heading
    for i, (pos, heading) in enumerate(positions):
        start = pos + len(heading)
        end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        content = text[start:end].strip()
        sections.append((heading, content))

    return sections


def _split_by_paragraphs(heading: str, text: str) -> list[str]:
    """
    Split an oversized section into smaller chunks by paragraph boundaries.
    Each sub-chunk is prefixed with the parent heading for context.
    """
    paragraphs = re.split(r"\n{2,}", text)
    sub_chunks: list[str] = []
    current_parts: list[str] = [heading] if heading else []
    current_tokens = count_tokens(heading) if heading else 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        para_tokens = count_tokens(para)

        if current_tokens + para_tokens > CHUNK_MAX_TOKENS and current_parts:
            # Flush current buffer as a chunk
            sub_chunks.append("\n\n".join(current_parts))
            # Start new chunk, re-use heading as context prefix
            current_parts = [heading] if heading else []
            current_tokens = count_tokens(heading) if heading else 0

        current_parts.append(para)
        current_tokens += para_tokens

    # Flush remaining buffer
    if current_parts:
        sub_chunks.append("\n\n".join(current_parts))

    return sub_chunks


def _build_heading_path(heading_line: str) -> str:
    """Strip Markdown markers from a heading line to get a clean path segment."""
    return re.sub(r"^#{1,3}\s+", "", heading_line).strip()
