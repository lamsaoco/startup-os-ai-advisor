"""
Text Extractor — converts raw Notion blocks → structured plain text.

Output preserves document hierarchy:
  # Heading 1
  ## Heading 2
  ### Heading 3
  • Bullet item
  1. Numbered item
  [!] Callout text
  > Quote text
  | Col1 | Col2 |  (markdown table)
"""
from ingestion.notion_crawler import PageData


def extract_rich_text(rich_text_list: list[dict]) -> str:
    """Extract plain_text from Notion rich_text array and join into a string."""
    return "".join(item.get("plain_text", "") for item in rich_text_list)


def blocks_to_text(blocks: list[dict]) -> str:
    """
    Convert a list of Notion blocks → structured plain text string.
    Ignores: image, video, file, bookmark, divider, unsupported blocks.
    """
    lines: list[str] = []
    table_rows: list[list[str]] = []   # temporary buffer for table
    in_table = False
    numbered_list_counter = 0  # counter for numbered list items within a sequence

    for block in blocks:
        btype = block.get("type", "")
        data = block.get(btype, {})

        # ── Flush table buffer when exiting a table ─────────────────────────────
        if in_table and btype != "table_row":
            lines.append(_render_table(table_rows))
            table_rows = []
            in_table = False

        # Reset numbered list counter when a non-numbered-list block is encountered
        if btype != "numbered_list_item":
            numbered_list_counter = 0

        # ── Process each block type ─────────────────────────────────────────────
        if btype == "heading_1":
            text = extract_rich_text(data.get("rich_text", []))
            if text.strip():
                lines.append(f"\n# {text}")

        elif btype == "heading_2":
            text = extract_rich_text(data.get("rich_text", []))
            if text.strip():
                lines.append(f"\n## {text}")

        elif btype == "heading_3":
            text = extract_rich_text(data.get("rich_text", []))
            if text.strip():
                lines.append(f"\n### {text}")

        elif btype == "paragraph":
            text = extract_rich_text(data.get("rich_text", []))
            if text.strip():
                lines.append(text)

        elif btype == "bulleted_list_item":
            text = extract_rich_text(data.get("rich_text", []))
            if text.strip():
                lines.append(f"• {text}")

        elif btype == "numbered_list_item":
            text = extract_rich_text(data.get("rich_text", []))
            if text.strip():
                numbered_list_counter += 1
                lines.append(f"{numbered_list_counter}. {text}")

        elif btype == "callout":
            text = extract_rich_text(data.get("rich_text", []))
            if text.strip():
                lines.append(f"[!] {text}")

        elif btype == "quote":
            text = extract_rich_text(data.get("rich_text", []))
            if text.strip():
                lines.append(f"> {text}")

        elif btype == "toggle":
            # Title of the toggle
            text = extract_rich_text(data.get("rich_text", []))
            if text.strip():
                lines.append(f"▶ {text}")
            # Children of the toggle have already been flattened by the crawler

        elif btype == "code":
            text = extract_rich_text(data.get("rich_text", []))
            lang = data.get("language", "")
            if text.strip():
                lines.append(f"```{lang}\n{text}\n```")

        elif btype == "table":
            # Table will be processed via subsequent table_row blocks
            in_table = True

        elif btype == "table_row":
            cells = data.get("cells", [])
            row = [extract_rich_text(cell) for cell in cells]
            table_rows.append(row)
            in_table = True

        elif btype == "child_page":
            # Do not extract text — child_page has been crawled separately
            pass

        elif btype in ("divider", "image", "video", "file", "pdf",
                       "bookmark", "embed", "link_preview",
                       "column_list", "column", "breadcrumb",
                       "table_of_contents", "equation", "synced_block"):
            # Ignore blocks that do not contain necessary text
            pass

        else:
            # Fallback: try to extract rich_text if available
            rich_text = data.get("rich_text", [])
            if rich_text:
                text = extract_rich_text(rich_text)
                if text.strip():
                    lines.append(text)

    # Flush table if page ends with a table
    if in_table and table_rows:
        lines.append(_render_table(table_rows))

    return "\n".join(lines)


def _render_table(rows: list[list[str]]) -> str:
    """Convert a list of rows → Markdown table format."""
    if not rows:
        return ""
    lines = []
    # Header row
    lines.append("| " + " | ".join(rows[0]) + " |")
    # Separator
    lines.append("| " + " | ".join(["---"] * len(rows[0])) + " |")
    # Data rows
    for row in rows[1:]:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def extract_page_text(page: PageData) -> str:
    """
    Extract all text from a PageData object.
    Prepend the page title as an H1 heading.
    """
    header = f"# {page.title}\nBreadcrumb: {page.breadcrumb}\n"
    body = blocks_to_text(page.blocks)
    return f"{header}\n{body}".strip()
