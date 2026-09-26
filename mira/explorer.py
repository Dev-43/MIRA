"""Generic Web Explorer for MIRA.

Performs BFS crawl of target URL up to depth 3 or 15 pages.
Extracts:
1. Interactive elements via robust DOM + ARIA element querying (button, link, textbox, heading, tab, etc.)
2. LiveFields via temporal screenshot pixel-block diffing (32x32 grid over sample interval)
   with freshness claim detection via generic keyword matching.
Zero site-specific or domain-specific hardcoded strings.
"""

from __future__ import annotations
import hashlib
import io
import json
import logging
import os
import re
import time
from collections import deque
from typing import Any, Dict, List, Set, Tuple
from urllib.parse import urljoin, urlparse

from PIL import Image
from playwright.sync_api import Page, sync_playwright

from mira import graph

logger = logging.getLogger("mira.explorer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

FRESHNESS_KEYWORDS = {
    "live", "real-time", "realtime", "online", "fps", "hz",
    "connected", "streaming", "active", "updated", "sync",
    "latency", "ms", "refresh", "telemetry", "status", "stream",
    "armed", "disarmed", "voltage", "altitude", "battery", "speed"
}

INTERACTIVE_SELECTOR = (
    "button, a[href], input, select, textarea, "
    "[role='button'], [role='tab'], [role='checkbox'], [role='combobox'], "
    "[role='menuitem'], [role='switch'], [role='link'], "
    "h1, h2, h3, [class*='badge'], [class*='status']"
)


def _make_id(prefix: str, *parts: Any) -> str:
    raw = "_".join(str(p) for p in parts)
    digest = hashlib.md5(raw.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}_{digest}"


def _get_site_id(target_url: str) -> str:
    parsed = urlparse(target_url)
    host = parsed.netloc.replace(":", "_").replace(".", "_")
    return f"site_{host}"


def _extract_interactive_elements(page: Page, page_url: str) -> List[Dict[str, Any]]:
    """Extract interactive elements and headings from page with bounding boxes."""
    elements: List[Dict[str, Any]] = []

    try:
        locators = page.locator(INTERACTIVE_SELECTOR).all()
        for loc in locators:
            try:
                if not loc.is_visible(timeout=200):
                    continue

                box = loc.bounding_box()
                if not box or box["width"] <= 0 or box["height"] <= 0:
                    continue

                bbox = {
                    "x": float(box["x"]),
                    "y": float(box["y"]),
                    "width": float(box["width"]),
                    "height": float(box["height"]),
                }

                # Derive role
                role = loc.get_attribute("role") or ""
                tag = loc.evaluate("el => el.tagName.toLowerCase()")
                if not role:
                    if tag == "a":
                        role = "link"
                    elif tag in ("h1", "h2", "h3", "h4"):
                        role = "heading"
                    elif tag == "input":
                        input_type = loc.get_attribute("type") or "text"
                        role = "checkbox" if input_type == "checkbox" else "textbox"
                    elif tag in ("textarea", "select"):
                        role = "textbox"
                    elif "badge" in (loc.get_attribute("class") or "").lower() or "status" in (loc.get_attribute("class") or "").lower():
                        role = "status"
                    else:
                        role = "button" if tag == "button" else tag

                # Derive accessible name
                name = (
                    loc.get_attribute("aria-label")
                    or loc.inner_text()
                    or loc.get_attribute("placeholder")
                    or loc.get_attribute("title")
                    or ""
                ).strip()

                if not name:
                    continue

                # Clean whitespace
                name = re.sub(r"\s+", " ", name)[:100]

                el_id = _make_id("el", page_url, role, name, int(bbox["x"]), int(bbox["y"]))
                elements.append({
                    "id": el_id,
                    "role": role,
                    "name": name,
                    "page_url": page_url,
                    "bbox": bbox,
                })
            except Exception:
                continue
    except Exception as e:
        logger.warning("Error querying interactive elements on %s: %s", page_url, e)

    return elements


def _detect_livefields(
    page: Page,
    page_url: str,
    site_id: str,
    sample_interval: float = 2.0,
    block_size: int = 32,
    threshold: int = 15,
) -> List[Dict[str, Any]]:
    """Detect dynamic regions (LiveFields) by comparing two screenshots across interval."""
    livefields: List[Dict[str, Any]] = []

    try:
        try:
            shot1_bytes = page.locator("body").screenshot(timeout=3000)
        except Exception:
            shot1_bytes = page.screenshot(type="png", timeout=3000, animations="disabled")
        page.wait_for_timeout(int(sample_interval * 1000))
        try:
            shot2_bytes = page.locator("body").screenshot(timeout=3000)
        except Exception:
            shot2_bytes = page.screenshot(type="png", timeout=3000, animations="disabled")

        img1 = Image.open(io.BytesIO(shot1_bytes)).convert("RGB")
        img2 = Image.open(io.BytesIO(shot2_bytes)).convert("RGB")

        if img1.size != img2.size:
            return livefields

        width, height = img1.size
        changed_blocks: List[Tuple[int, int]] = []

        # Sample grid
        for y in range(0, height, block_size):
            for x in range(0, width, block_size):
                box = (x, y, min(x + block_size, width), min(y + block_size, height))
                crop1 = img1.crop(box)
                crop2 = img2.crop(box)

                b1 = crop1.tobytes()
                b2 = crop2.tobytes()

                if b1 == b2:
                    continue

                # Compute average pixel difference
                diff_sum = 0
                sample_step = 3
                for i in range(0, len(b1), sample_step):
                    diff_sum += abs(b1[i] - b2[i])

                avg_diff = diff_sum / (len(b1) / sample_step) if b1 else 0
                if avg_diff > threshold:
                    changed_blocks.append((x, y))

        if not changed_blocks:
            return livefields

        # Cluster adjacent changed blocks into regions
        clusters: List[List[Tuple[int, int]]] = []
        visited = set()

        for b in changed_blocks:
            if b in visited:
                continue
            cluster = [b]
            visited.add(b)
            queue = [b]
            while queue:
                cx, cy = queue.pop()
                for neighbor in changed_blocks:
                    if neighbor not in visited:
                        nx, ny = neighbor
                        if abs(nx - cx) <= block_size * 2 and abs(ny - cy) <= block_size * 2:
                            visited.add(neighbor)
                            cluster.append(neighbor)
                            queue.append(neighbor)
            clusters.append(cluster)

        # Merge clusters into bounding boxes
        now_ts = time.time()
        for idx, cluster in enumerate(clusters):
            min_x = min(pt[0] for pt in cluster)
            min_y = min(pt[1] for pt in cluster)
            max_x = max(pt[0] + block_size for pt in cluster)
            max_y = max(pt[1] + block_size for pt in cluster)

            w = max_x - min_x
            h = max_y - min_y

            # Filter tiny jitter
            if w < 16 or h < 16:
                continue

            region_bbox = {"x": float(min_x), "y": float(min_y), "width": float(w), "height": float(h)}

            # Crop hash
            crop = img2.crop((min_x, min_y, max_x, max_y))
            crop_hash = hashlib.md5(crop.tobytes()).hexdigest()

            # Attempt to extract nearby text for freshness keyword inspection
            nearby_text = ""
            try:
                js_extract = """
                (box) => {
                    const el = document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2);
                    return el ? (el.innerText || el.textContent || '') : '';
                }
                """
                extracted = page.evaluate(js_extract, region_bbox)
                if extracted:
                    nearby_text = str(extracted).strip()[:200]
            except Exception:
                pass

            clean_text_lower = nearby_text.lower()
            words = set(re.findall(r"\b\w+[\w-]*\b", clean_text_lower))
            freshness_claim = bool(words & FRESHNESS_KEYWORDS)

            lf_id = _make_id("lf", page_url, idx, min_x, min_y, w, h)
            livefields.append({
                "id": lf_id,
                "page_url": page_url,
                "region_bbox": region_bbox,
                "label_text": nearby_text or f"Dynamic Region at ({min_x},{min_y})",
                "last_value_hash": crop_hash,
                "last_changed_ts": now_ts,
                "freshness_claim": freshness_claim,
            })

    except Exception as e:
        logger.warning("Error during LiveField detection on %s: %s", page_url, e)

    return livefields


def explore(
    target_url: str,
    max_depth: int = 3,
    max_pages: int = 15,
    sample_interval: float = 2.0,
    headless: bool = True,
    warm: bool = False,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Crawl target URL up to depth 3 or 15 pages.

    Returns:
        (elements, livefields) matching the MIRA interface contracts.
    """
    site_id = _get_site_id(target_url)

    # Check for warm run cache hit
    if warm and graph.is_site_known(site_id):
        cached_pages = graph.get_pages_for_site(site_id)
        cached_elements = []
        for cp in cached_pages:
            cached_elements.extend(graph.get_elements_for_page(cp["url"]))
        if cached_elements:
            logger.info("Warm run cache hit: Re-using %d pre-indexed elements across %d pages.",
                        len(cached_elements), len(cached_pages))
            # Resample LiveFields only
            all_livefields: List[Dict[str, Any]] = []
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=headless)
                context = browser.new_context(viewport={"width": 1440, "height": 900})
                page = context.new_page()
                for cp in cached_pages[:max_pages]:
                    try:
                        page.goto(cp["url"], wait_until="domcontentloaded", timeout=10000)
                        page.wait_for_timeout(1500)
                        lfs = _detect_livefields(page, cp["url"], site_id, sample_interval=sample_interval)
                        for lf in lfs:
                            graph.upsert_livefield(site_id=site_id, page_url=cp["url"], livefield=lf)
                            all_livefields.append(lf)
                    except Exception:
                        pass
                browser.close()
            return cached_elements, all_livefields

    graph.upsert_site(site_id, target_url)

    target_parsed = urlparse(target_url)
    target_domain = target_parsed.netloc

    all_elements: List[Dict[str, Any]] = []
    all_livefields: List[Dict[str, Any]] = []

    visited_urls: Set[str] = set()
    queue: deque[Tuple[str, int]] = deque([(target_url, 0)])

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        while queue and len(visited_urls) < max_pages:
            current_url, depth = queue.popleft()

            parsed_curr = urlparse(current_url)
            clean_url = parsed_curr._replace(fragment="").geturl()

            if clean_url in visited_urls:
                continue

            visited_urls.add(clean_url)
            logger.info("Crawling [Depth %d | Page %d/%d]: %s", depth, len(visited_urls), max_pages, clean_url)

            try:
                page.goto(clean_url, wait_until="domcontentloaded", timeout=15000)
            except Exception as e:
                logger.warning("Failed to navigate to %s: %s", clean_url, e)
                continue

            # Wait briefly for dynamic client-side renders (Cesium / WebSockets)
            page.wait_for_timeout(2500)

            title = page.title() or ""
            path = parsed_curr.path or "/"
            page_id = _make_id("p", site_id, clean_url)
            graph.upsert_page(site_id=site_id, page_id=page_id, url=clean_url, title=title, path=path)

            # 1. Discover Interactive Elements
            elements = _extract_interactive_elements(page, clean_url)
            for el in elements:
                graph.upsert_element(site_id=site_id, page_url=clean_url, element=el)
                all_elements.append(el)
            logger.info("Found %d interactive elements on %s", len(elements), clean_url)

            # 2. Discover LiveFields via Temporal Pixel Diffing
            livefields = _detect_livefields(
                page=page,
                page_url=clean_url,
                site_id=site_id,
                sample_interval=sample_interval,
            )
            for lf in livefields:
                graph.upsert_livefield(site_id=site_id, page_url=clean_url, livefield=lf)
                all_livefields.append(lf)
            logger.info("Found %d LiveFields on %s", len(livefields), clean_url)

            # 3. Discover same-origin links for BFS if depth < max_depth
            if depth < max_depth:
                try:
                    hrefs = page.eval_on_selector_all(
                        "a[href]",
                        "anchors => anchors.map(a => a.getAttribute('href'))"
                    )
                    for href in hrefs:
                        if not href or href.startswith("javascript:") or href.startswith("mailto:"):
                            continue
                        full_link = urljoin(clean_url, href)
                        parsed_link = urlparse(full_link)
                        if parsed_link.netloc == target_domain:
                            link_no_frag = parsed_link._replace(fragment="").geturl()
                            if link_no_frag not in visited_urls:
                                queue.append((link_no_frag, depth + 1))
                except Exception as e:
                    logger.debug("Link discovery failed on %s: %s", clean_url, e)

        browser.close()

    logger.info("Exploration complete. Total pages: %d, Total elements: %d, Total LiveFields: %d",
                len(visited_urls), len(all_elements), len(all_livefields))
    return all_elements, all_livefields


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="MIRA Generic Web Explorer")
    parser.add_argument("--target", default="http://localhost:4010", help="Target URL to explore")
    parser.add_argument("--depth", type=int, default=3, help="Max BFS depth")
    parser.add_argument("--pages", type=int, default=15, help="Max pages")
    parser.add_argument("--sample", type=float, default=2.0, help="LiveField sample interval seconds")
    parser.add_argument("--headed", action="store_true", help="Run headed browser")
    args = parser.parse_args()

    elems, lfs = explore(
        target_url=args.target,
        max_depth=args.depth,
        max_pages=args.pages,
        sample_interval=args.sample,
        headless=not args.headed,
    )
    print(f"\nDiscovered {len(elems)} elements and {len(lfs)} LiveFields.")
