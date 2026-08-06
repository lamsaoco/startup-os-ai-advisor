"""
Heading-Aware Chunker — splits page text into semantically coherent chunks.

Strategy:
  1. Split full page text by heading markers (# / ## / ###)
  2. Each heading + its content below = one chunk candidate
  3. If a candidate exceeds CHUNK_MAX_TOKENS → split further by paragraphs
     with a sliding-window overlap of CHUNK_OVERLAP_TOKENS between sub-chunks
  4. If a candidate is below CHUNK_MIN_TOKENS → merge with the next chunk
  5. Every chunk retains: page metadata, breadcrumb, and heading_path
  6. Each chunk has two text representations:
       - content   : raw text as-is (stored in DB, shown to users)
       - embed_text: contextual prefix + content (used for embedding only)
         Format: "[Document: <title> | Path: <breadcrumb> > <heading_path>]\n<content>"
"""
import re
import uuid
from dataclasses import dataclass, field
from typing import Optional

import tiktoken

from ingestion.config import CHUNK_MAX_TOKENS, CHUNK_MIN_TOKENS, CHUNK_OVERLAP_TOKENS
from ingestion.notion_crawler import PageData
from ingestion.text_extractor import extract_page_text

# Use cl100k_base tokenizer (compatible with most modern models)
_TOKENIZER = tiktoken.get_encoding("cl100k_base")


@dataclass
class Chunk:
    """A single text chunk ready for embedding and storage."""
    chunk_id: str
    document_id: str           # Notion page ID
    content: str               # Raw text content — stored in DB, shown to users
    embed_text: str            # Contextual text used for embedding (breadcrumb + content)
    heading_path: str          # e.g. "2. Six-Step Process > 2.1 Self-Assessment"
    breadcrumb: str            # e.g. "HR Framework > Performance Review"
    page_title: str
    chunk_index: int           # Position of this chunk within the page (0-based)
    token_count: int           # Token count of raw content


def count_tokens(text: str) -> int:
    """Count the number of tokens in a text string."""
    return len(_TOKENIZER.encode(text))


def _build_embed_text(page_title: str, breadcrumb: str, heading_path: str, content: str) -> str:
    """
    Build the contextual text used for embedding.
    Combines breadcrumb, heading path, and raw content so the embedding
    model understands the document hierarchy without exposing it in the answer.

    Format:
        [Document: <title> | Path: <breadcrumb> > <heading_path>]
        <content>
    """
    path_parts = [p for p in [breadcrumb, heading_path] if p]
    path_str = " > ".join(path_parts) if path_parts else page_title
    header = f"[Document: {page_title} | Path: {path_str}]"
    return f"{header}\n{content}"


def chunk_page(page: PageData) -> list[Chunk]:
    """
    Main entry point: convert a PageData object into a list of Chunk objects.
    """
    full_text = extract_page_text(page)
    raw_sections = _split_by_headings(full_text)
    chunks: list[Chunk] = []

    for section_heading, section_text in raw_sections:
        # Build the clean heading path for this section
        heading_path = _build_heading_path(section_heading)
        combined = f"{section_heading}\n{section_text}".strip() if section_heading else section_text.strip()

        token_count = count_tokens(combined)

        if token_count > CHUNK_MAX_TOKENS:
            # Section too large → split further by paragraph with overlap
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
                merged_embed = _build_embed_text(
                    page.title, page.breadcrumb, prev.heading_path, merged_content
                )
                chunks[-1] = Chunk(
                    chunk_id=prev.chunk_id,
                    document_id=prev.document_id,
                    content=merged_content,
                    embed_text=merged_embed,
                    heading_path=prev.heading_path,
                    breadcrumb=prev.breadcrumb,
                    page_title=prev.page_title,
                    chunk_index=prev.chunk_index,
                    token_count=count_tokens(merged_content),
                )
            else:
                embed_text = _build_embed_text(page.title, page.breadcrumb, heading_path, sub)
                chunks.append(Chunk(
                    chunk_id=str(uuid.uuid4()),
                    document_id=page.page_id,
                    content=sub,
                    embed_text=embed_text,
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
    Split an oversized section into smaller chunks by paragraph boundaries,
    with a sliding-window overlap of CHUNK_OVERLAP_TOKENS tokens between
    consecutive sub-chunks to prevent context loss at boundaries.

    Each sub-chunk is prefixed with the parent heading for context.
    """
    paragraphs = re.split(r"\n{2,}", text)
    sub_chunks: list[str] = []

    # Tokenize all paragraphs once upfront
    para_token_lists: list[list[int]] = [
        _TOKENIZER.encode(p.strip()) for p in paragraphs if p.strip()
    ]
    clean_paras: list[str] = [p.strip() for p in paragraphs if p.strip()]

    heading_tokens = _TOKENIZER.encode(heading) if heading else []
    heading_token_count = len(heading_tokens)

    current_token_ids: list[int] = list(heading_tokens)  # start with heading
    current_parts: list[str] = [heading] if heading else []

    for para, para_tokens in zip(clean_paras, para_token_lists):
        para_token_count = len(para_tokens)

        if (len(current_token_ids) + para_token_count > CHUNK_MAX_TOKENS) and current_parts:
            # Flush current buffer as a completed sub-chunk
            sub_chunks.append("\n\n".join(current_parts))

            # Build overlap: take the last CHUNK_OVERLAP_TOKENS tokens from the
            # flushed buffer (excluding the heading prefix) and decode back to text
            overlap_tokens = current_token_ids[heading_token_count:][-CHUNK_OVERLAP_TOKENS:]
            overlap_text = _TOKENIZER.decode(overlap_tokens).strip() if overlap_tokens else ""

            # Start new sub-chunk: heading prefix + overlap text
            current_parts = [heading] if heading else []
            current_token_ids = list(heading_tokens)

            if overlap_text:
                current_parts.append(overlap_text)
                current_token_ids += overlap_tokens

        current_parts.append(para)
        current_token_ids += para_tokens

    # Flush remaining buffer
    if current_parts:
        sub_chunks.append("\n\n".join(current_parts))

    return sub_chunks


def _build_heading_path(heading_line: str) -> str:
    """Strip Markdown markers from a heading line to get a clean path segment."""
    return re.sub(r"^#{1,3}\s+", "", heading_line).strip()
