"""
Notion Recursive Crawler — Option A: Start from a fixed Root Page ID.

Flow:
  1. Start from NOTION_ROOT_PAGE_ID
  2. Fetch all blocks for that page (handles pagination)
  3. When encountering a child_page block → recursively crawl it
  4. Build a breadcrumb path from root down to each leaf page
  5. Return a flat list of PageData objects (all pages, fully populated)
"""
import time
from dataclasses import dataclass, field
from typing import Optional

from notion_client import Client
from notion_client.errors import APIResponseError

from ingestion.config import NOTION_API_KEY


@dataclass
class PageData:
    """Extracted data for a single Notion page."""
    page_id: str
    title: str
    parent_id: Optional[str]
    breadcrumb: str            # e.g. "Root > Section > Sub-section"
    breadcrumb_list: list[str] # e.g. ["Root", "Section", "Sub-section"]
    url: str
    last_edited: str
    blocks: list[dict]         # Raw Notion blocks (text not yet extracted)
    is_changed: bool = True    # True if last_edited differs from DB


class NotionCrawler:
    """Recursively crawls from a root page and returns a flat list of PageData."""

    def __init__(self):
        self.client = Client(auth=NOTION_API_KEY)
        self._pages: list[PageData] = []

    # ── Public API ────────────────────────────────────────────────────────────

    def crawl(self, root_page_id: str, limit: int = 0, db_state: dict[str, str] = None) -> list[PageData]:
        """Start crawling from root_page_id, return flat list of all pages."""
        self._pages = []
        self._limit = limit
        self._db_state = db_state or {}
        print(f"[Crawler] Starting from root page: {root_page_id}")
        self._crawl_page(
            page_id=root_page_id,
            parent_id=None,
            breadcrumb_list=[],
        )
        print(f"[Crawler] Done — total {len(self._pages)} pages collected")
        return self._pages

    # ── Internal ──────────────────────────────────────────────────────────────

    def _crawl_page(
        self,
        page_id: str,
        parent_id: Optional[str],
        breadcrumb_list: list[str],
    ) -> None:
        """Crawl one page: fetch metadata, fetch blocks, recurse into child pages."""
        if getattr(self, "_limit", 0) and len(self._pages) >= self._limit:
            return
        # 1. Fetch page metadata
        page_meta = self._get_page_meta(page_id)
        if page_meta is None:
            return

        title = page_meta["title"]
        new_breadcrumb = breadcrumb_list + [title]
        breadcrumb_str = " > ".join(new_breadcrumb)

        print(f"[Crawler]   {'  ' * len(breadcrumb_list)}↳ {title}")

        # Check if page has changed compared to DB state
        last_edited = page_meta["last_edited"]
        is_changed = (self._db_state.get(page_id) != last_edited)
        if not is_changed:
            print(f"[Crawler]   {'  ' * len(breadcrumb_list)}  (Unchanged, skipping blocks payload)")

        # 2. Fetch all blocks to find child_pages (and content if changed)
        blocks = self._fetch_all_blocks(page_id)

        # 3. Store this page
        self._pages.append(PageData(
            page_id=page_id,
            title=title,
            parent_id=parent_id,
            breadcrumb=breadcrumb_str,
            breadcrumb_list=new_breadcrumb,
            url=page_meta["url"],
            last_edited=last_edited,
            blocks=blocks if is_changed else [],  # Drop blocks if unchanged to save memory
            is_changed=is_changed,
        ))

        # 4. Find child_page blocks and recurse into them
        for block in blocks:
            if block.get("type") == "child_page":
                child_id = block["id"]
                self._crawl_page(
                    page_id=child_id,
                    parent_id=page_id,
                    breadcrumb_list=new_breadcrumb,
                )

    def _get_page_meta(self, page_id: str) -> Optional[dict]:
        """Retrieve title, url, and last_edited_time for a given page."""
        try:
            page = self._api_call(self.client.pages.retrieve, page_id=page_id)
        except Exception as e:
            print(f"[Crawler] ⚠️  Could not retrieve page {page_id}: {e}")
            return None

        # Extract title from page properties
        title = "Untitled"
        props = page.get("properties", {})
        for prop in props.values():
            if prop.get("type") == "title":
                rich_text = prop.get("title", [])
                if rich_text:
                    title = "".join(t.get("plain_text", "") for t in rich_text)
                break

        return {
            "title": title or "Untitled",
            "url": page.get("url", ""),
            "last_edited": page.get("last_edited_time", ""),
        }

    def _fetch_all_blocks(self, block_id: str) -> list[dict]:
        """
        Fetch ALL blocks for a page/block, handling Notion's pagination.
        Notion returns at most 100 blocks per request, so we loop via cursor.
        """
        all_blocks: list[dict] = []
        cursor: Optional[str] = None

        while True:
            kwargs = {"block_id": block_id, "page_size": 100}
            if cursor:
                kwargs["start_cursor"] = cursor

            try:
                response = self._api_call(
                    self.client.blocks.children.list, **kwargs
                )
            except Exception as e:
                print(f"[Crawler] ⚠️  Error fetching blocks for {block_id}: {e}")
                break

            results = response.get("results", [])
            all_blocks.extend(results)

            if response.get("has_more"):
                cursor = response.get("next_cursor")
            else:
                break

        # Recursively expand layout containers (column_list, column) and
        # content containers (toggle, callout, etc.) to find child_pages
        # that may be nested inside layout blocks.
        # Note: child_page blocks themselves are NOT expanded here — they are
        # handled separately in _crawl_page to maintain proper breadcrumb hierarchy.
        expanded: list[dict] = []
        for block in all_blocks:
            expanded.append(block)
            btype = block.get("type", "")
            if block.get("has_children") and btype in (
                "toggle", "callout", "bulleted_list_item",
                "numbered_list_item", "quote",
                # Layout containers — child_pages may be nested inside these
                "column_list", "column",
                "synced_block",
            ):
                children = self._fetch_all_blocks(block["id"])
                for child in children:
                    child["_parent_type"] = btype
                expanded.extend(children)

        return expanded

    def _api_call(self, func, **kwargs):
        """Wrapper with retry and exponential backoff for Notion API rate limits."""
        for attempt in range(5):
            try:
                return func(**kwargs)
            except APIResponseError as e:
                if e.status == 429:  # Too Many Requests
                    wait = 2 ** attempt
                    print(f"[Crawler] Rate limited, waiting {wait}s...")
                    time.sleep(wait)
                else:
                    raise
        raise RuntimeError("Notion API: exceeded maximum retry attempts")
