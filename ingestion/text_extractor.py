"""
Text Extractor — chuyển raw Notion blocks → plain text có cấu trúc.

Output giữ nguyên hierarchy của document:
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
    """Lấy plain_text từ Notion rich_text array, nối lại thành string."""
    return "".join(item.get("plain_text", "") for item in rich_text_list)


def blocks_to_text(blocks: list[dict]) -> str:
    """
    Chuyển list Notion blocks → string text có cấu trúc.
    Bỏ qua: image, video, file, bookmark, divider, unsupported.
    """
    lines: list[str] = []
    table_rows: list[list[str]] = []   # buffer tạm cho table
    in_table = False

    for block in blocks:
        btype = block.get("type", "")
        data = block.get(btype, {})

        # ── Flush table buffer khi ra khỏi table ─────────────────────────────
        if in_table and btype != "table_row":
            lines.append(_render_table(table_rows))
            table_rows = []
            in_table = False

        # ── Xử lý từng block type ─────────────────────────────────────────────
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
                lines.append(f"1. {text}")

        elif btype == "callout":
            text = extract_rich_text(data.get("rich_text", []))
            if text.strip():
                lines.append(f"[!] {text}")

        elif btype == "quote":
            text = extract_rich_text(data.get("rich_text", []))
            if text.strip():
                lines.append(f"> {text}")

        elif btype == "toggle":
            # Title của toggle
            text = extract_rich_text(data.get("rich_text", []))
            if text.strip():
                lines.append(f"▶ {text}")
            # Children của toggle đã được flatten bởi crawler

        elif btype == "code":
            text = extract_rich_text(data.get("rich_text", []))
            lang = data.get("language", "")
            if text.strip():
                lines.append(f"```{lang}\n{text}\n```")

        elif btype == "table":
            # Table sẽ được xử lý qua table_row blocks tiếp theo
            in_table = True

        elif btype == "table_row":
            cells = data.get("cells", [])
            row = [extract_rich_text(cell) for cell in cells]
            table_rows.append(row)
            in_table = True

        elif btype == "child_page":
            # Không lấy text — child_page đã được crawl riêng
            pass

        elif btype in ("divider", "image", "video", "file", "pdf",
                       "bookmark", "embed", "link_preview",
                       "column_list", "column", "breadcrumb",
                       "table_of_contents", "equation", "synced_block"):
            # Bỏ qua các block không chứa text cần thiết
            pass

        else:
            # Fallback: thử extract rich_text nếu có
            rich_text = data.get("rich_text", [])
            if rich_text:
                text = extract_rich_text(rich_text)
                if text.strip():
                    lines.append(text)

    # Flush table nếu page kết thúc bằng table
    if in_table and table_rows:
        lines.append(_render_table(table_rows))

    return "\n".join(lines)


def _render_table(rows: list[list[str]]) -> str:
    """Chuyển list of rows → Markdown table format."""
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
    Extract toàn bộ text từ 1 PageData object.
    Thêm page title làm H1 ở đầu.
    """
    header = f"# {page.title}\nBreadcrumb: {page.breadcrumb}\n"
    body = blocks_to_text(page.blocks)
    return f"{header}\n{body}".strip()
