"""MIRA Knowledge Graph Client (Neo4j with resilient In-Memory Fallback).

Implements the MIRA-Web graph schema:
- Nodes: Site, Page, Element, LiveField
- Relationships:
    (:Site)-[:HAS_PAGE]->(:Page)
    (:Page)-[:CONTAINS_ELEMENT]->(:Element)
    (:Page)-[:HAS_LIVEFIELD]->(:LiveField)
"""

from __future__ import annotations
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("mira.graph")

# In-memory graph fallback store when Neo4j is offline
_IN_MEMORY_STORE: Dict[str, Any] = {
    "sites": {},       # site_id -> dict
    "pages": {},       # page_id -> dict
    "elements": {},    # element_id -> dict
    "livefields": {},   # livefield_id -> dict
    "site_pages": {},  # site_id -> set(page_id)
    "page_elements": {}, # page_url -> list(element_id)
    "page_livefields": {}, # page_url -> list(livefield_id)
}


class Neo4jDriverWrapper:
    """Wrapper that manages Neo4j driver connection and fallback."""

    def __init__(self) -> None:
        self.uri = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
        self.username = os.getenv("NEO4J_USERNAME") or os.getenv("NEO4J_USER") or "neo4j"
        self.password = os.getenv("NEO4J_PASSWORD", "")
        self._driver = None
        self._is_live: Optional[bool] = None

    def get_driver(self):
        """Returns active neo4j driver or None if offline."""
        if self._is_live is False:
            return None

        if self._driver is not None:
            return self._driver

        try:
            from neo4j import GraphDatabase, basic_auth
            auth_token = basic_auth(self.username, self.password)
            driver = GraphDatabase.driver(self.uri, auth=auth_token, connection_timeout=3.0)
            driver.verify_connectivity()
            # Verify actual query execution
            with driver.session() as s:
                s.run("RETURN 1").single()
            self._driver = driver
            self._is_live = True
            logger.info("Connected to Neo4j at %s", self.uri)
            return self._driver
        except Exception as e:
            logger.warning("Neo4j unavailable or auth error (%s). Using in-memory graph fallback.", e)
            self._is_live = False
            self._driver = None
            return None

    @property
    def is_connected(self) -> bool:
        return self.get_driver() is not None

    def close(self):
        if self._driver is not None:
            try:
                self._driver.close()
            except Exception:
                pass
            self._driver = None
            self._is_live = None


_WRAPPER = Neo4jDriverWrapper()


def get_driver():
    """Returns active Neo4j driver instance or None if unreachable."""
    return _WRAPPER.get_driver()


def init_schema(driver=None) -> bool:
    """Initializes uniqueness constraints in Neo4j if available."""
    drv = driver or get_driver()
    if not drv:
        logger.debug("In-memory fallback schema initialized.")
        return True

    queries = [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Site) REQUIRE s.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Page) REQUIRE p.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (e:Element) REQUIRE e.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (l:LiveField) REQUIRE l.id IS UNIQUE",
    ]

    try:
        with drv.session() as session:
            for q in queries:
                session.run(q)
        return True
    except Exception as e:
        logger.warning("Failed to initialize Neo4j constraints: %s", e)
        return False


def upsert_site(site_id: str, url: str, driver=None) -> Dict[str, Any]:
    """Upsert a Site node."""
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    site_data = {"id": site_id, "url": url, "last_crawled": now_iso}

    drv = driver or get_driver()
    if drv:
        query = """
        MERGE (s:Site {id: $id})
        SET s.url = $url, s.last_crawled = $last_crawled
        RETURN s
        """
        try:
            with drv.session() as session:
                session.run(query, id=site_id, url=url, last_crawled=now_iso)
        except Exception as e:
            logger.warning("Neo4j error in upsert_site: %s", e)

    # Always mirror to in-memory store
    _IN_MEMORY_STORE["sites"][site_id] = site_data
    if site_id not in _IN_MEMORY_STORE["site_pages"]:
        _IN_MEMORY_STORE["site_pages"][site_id] = set()
    return site_data


def upsert_page(site_id: str, page_id: str, url: str, title: str = "", path: str = "", driver=None) -> Dict[str, Any]:
    """Upsert a Page node and connect (:Site)-[:HAS_PAGE]->(:Page)."""
    page_data = {
        "id": page_id,
        "site_id": site_id,
        "url": url,
        "title": title,
        "path": path,
    }

    drv = driver or get_driver()
    if drv:
        query = """
        MERGE (s:Site {id: $site_id})
        MERGE (p:Page {id: $page_id})
        SET p.url = $url, p.title = $title, p.path = $path, p.site_id = $site_id
        MERGE (s)-[:HAS_PAGE]->(p)
        RETURN p
        """
        try:
            with drv.session() as session:
                session.run(query, site_id=site_id, page_id=page_id, url=url, title=title, path=path)
        except Exception as e:
            logger.warning("Neo4j error in upsert_page: %s", e)

    # In-memory mirror
    _IN_MEMORY_STORE["pages"][page_id] = page_data
    if site_id in _IN_MEMORY_STORE["site_pages"]:
        _IN_MEMORY_STORE["site_pages"][site_id].add(page_id)
    else:
        _IN_MEMORY_STORE["site_pages"][site_id] = {page_id}
    return page_data


def upsert_element(site_id: str, page_url: str, element: Dict[str, Any], driver=None) -> Dict[str, Any]:
    """Upsert an Element node and connect (:Page)-[:CONTAINS_ELEMENT]->(:Element)."""
    el_id = element.get("id", f"el_{hash(page_url + str(element.get('role', '')) + str(element.get('name', '')))}")
    bbox_str = json.dumps(element.get("bbox", {}))
    role = element.get("role", "")
    name = element.get("name", "")

    el_data = {
        "id": el_id,
        "site_id": site_id,
        "page_url": page_url,
        "role": role,
        "name": name,
        "bbox": element.get("bbox", {}),
    }

    drv = driver or get_driver()
    if drv:
        query = """
        MATCH (p:Page {url: $page_url})
        MERGE (e:Element {id: $id})
        SET e.role = $role, e.name = $name, e.page_url = $page_url, e.bbox = $bbox, e.site_id = $site_id
        MERGE (p)-[:CONTAINS_ELEMENT]->(e)
        RETURN e
        """
        try:
            with drv.session() as session:
                session.run(query, id=el_id, page_url=page_url, role=role, name=name, bbox=bbox_str, site_id=site_id)
        except Exception as e:
            logger.warning("Neo4j error in upsert_element: %s", e)

    # In-memory mirror
    _IN_MEMORY_STORE["elements"][el_id] = el_data
    if page_url not in _IN_MEMORY_STORE["page_elements"]:
        _IN_MEMORY_STORE["page_elements"][page_url] = []
    if el_id not in _IN_MEMORY_STORE["page_elements"][page_url]:
        _IN_MEMORY_STORE["page_elements"][page_url].append(el_id)

    return el_data


def upsert_livefield(site_id: str, page_url: str, livefield: Dict[str, Any], driver=None) -> Dict[str, Any]:
    """Upsert a LiveField node and connect (:Page)-[:HAS_LIVEFIELD]->(:LiveField)."""
    lf_id = livefield.get("id", f"lf_{hash(page_url + str(livefield.get('region_bbox', '')))}")
    region_bbox_str = json.dumps(livefield.get("region_bbox", {}))
    label_text = livefield.get("label_text", "")
    last_value_hash = livefield.get("last_value_hash", "")
    last_changed_ts = float(livefield.get("last_changed_ts", time.time()))
    freshness_claim = bool(livefield.get("freshness_claim", False))

    lf_data = {
        "id": lf_id,
        "site_id": site_id,
        "page_url": page_url,
        "region_bbox": livefield.get("region_bbox", {}),
        "label_text": label_text,
        "last_value_hash": last_value_hash,
        "last_changed_ts": last_changed_ts,
        "freshness_claim": freshness_claim,
    }

    drv = driver or get_driver()
    if drv:
        query = """
        MATCH (p:Page {url: $page_url})
        MERGE (l:LiveField {id: $id})
        SET l.page_url = $page_url,
            l.region_bbox = $region_bbox,
            l.label_text = $label_text,
            l.last_value_hash = $last_value_hash,
            l.last_changed_ts = $last_changed_ts,
            l.freshness_claim = $freshness_claim,
            l.site_id = $site_id
        MERGE (p)-[:HAS_LIVEFIELD]->(l)
        RETURN l
        """
        try:
            with drv.session() as session:
                session.run(
                    query,
                    id=lf_id,
                    page_url=page_url,
                    region_bbox=region_bbox_str,
                    label_text=label_text,
                    last_value_hash=last_value_hash,
                    last_changed_ts=last_changed_ts,
                    freshness_claim=freshness_claim,
                    site_id=site_id,
                )
        except Exception as e:
            logger.warning("Neo4j error in upsert_livefield: %s", e)

    # In-memory mirror
    _IN_MEMORY_STORE["livefields"][lf_id] = lf_data
    if page_url not in _IN_MEMORY_STORE["page_livefields"]:
        _IN_MEMORY_STORE["page_livefields"][page_url] = []
    if lf_id not in _IN_MEMORY_STORE["page_livefields"][page_url]:
        _IN_MEMORY_STORE["page_livefields"][page_url].append(lf_id)

    return lf_data


def get_elements_for_page(page_url: str, driver=None) -> List[Dict[str, Any]]:
    """Retrieve all discovered elements for a page."""
    drv = driver or get_driver()
    if drv:
        query = """
        MATCH (p:Page {url: $page_url})-[:CONTAINS_ELEMENT]->(e:Element)
        RETURN e.id AS id, e.role AS role, e.name AS name, e.page_url AS page_url, e.bbox AS bbox
        """
        try:
            with drv.session() as session:
                result = session.run(query, page_url=page_url)
                items = []
                for rec in result:
                    bbox_val = rec["bbox"]
                    if isinstance(bbox_val, str):
                        try:
                            bbox_val = json.loads(bbox_val)
                        except Exception:
                            pass
                    items.append({
                        "id": rec["id"],
                        "role": rec["role"],
                        "name": rec["name"],
                        "page_url": rec["page_url"],
                        "bbox": bbox_val,
                    })
                return items
        except Exception as e:
            logger.warning("Error reading elements from Neo4j (%s), falling back to memory", e)

    # In-memory retrieval
    element_ids = _IN_MEMORY_STORE["page_elements"].get(page_url, [])
    return [_IN_MEMORY_STORE["elements"][eid] for eid in element_ids if eid in _IN_MEMORY_STORE["elements"]]


def get_livefields_for_page(page_url: str, driver=None) -> List[Dict[str, Any]]:
    """Retrieve all LiveFields for a page."""
    drv = driver or get_driver()
    if drv:
        query = """
        MATCH (p:Page {url: $page_url})-[:HAS_LIVEFIELD]->(l:LiveField)
        RETURN l.id AS id, l.page_url AS page_url, l.region_bbox AS region_bbox,
               l.label_text AS label_text, l.last_value_hash AS last_value_hash,
               l.last_changed_ts AS last_changed_ts, l.freshness_claim AS freshness_claim
        """
        try:
            with drv.session() as session:
                result = session.run(query, page_url=page_url)
                items = []
                for rec in result:
                    bbox_val = rec["region_bbox"]
                    if isinstance(bbox_val, str):
                        try:
                            bbox_val = json.loads(bbox_val)
                        except Exception:
                            pass
                    items.append({
                        "id": rec["id"],
                        "page_url": rec["page_url"],
                        "region_bbox": bbox_val,
                        "label_text": rec["label_text"],
                        "last_value_hash": rec["last_value_hash"],
                        "last_changed_ts": rec["last_changed_ts"],
                        "freshness_claim": rec["freshness_claim"],
                    })
                return items
        except Exception as e:
            logger.warning("Error reading livefields from Neo4j (%s), falling back to memory", e)

    # In-memory retrieval
    lf_ids = _IN_MEMORY_STORE["page_livefields"].get(page_url, [])
    return [_IN_MEMORY_STORE["livefields"][lid] for lid in lf_ids if lid in _IN_MEMORY_STORE["livefields"]]


def is_site_known(site_id: str, driver=None) -> bool:
    """Check if site has already been indexed."""
    drv = driver or get_driver()
    if drv:
        query = "MATCH (s:Site {id: $site_id}) RETURN count(s) > 0 AS known"
        try:
            with drv.session() as session:
                result = session.run(query, site_id=site_id)
                single = result.single()
                if single:
                    return bool(single["known"])
        except Exception as e:
            logger.warning("Error checking site from Neo4j (%s), falling back to memory", e)

    return site_id in _IN_MEMORY_STORE["sites"]


def get_pages_for_site(site_id: str, driver=None) -> List[Dict[str, Any]]:
    """Retrieve all pages indexed for a site."""
    drv = driver or get_driver()
    if drv:
        query = """
        MATCH (s:Site {id: $site_id})-[:HAS_PAGE]->(p:Page)
        RETURN p.id AS id, p.url AS url, p.title AS title, p.path AS path
        """
        try:
            with drv.session() as session:
                res = session.run(query, site_id=site_id)
                return [{"id": r["id"], "url": r["url"], "title": r["title"], "path": r["path"]} for r in res]
        except Exception:
            pass

    page_ids = _IN_MEMORY_STORE["site_pages"].get(site_id, set())
    return [_IN_MEMORY_STORE["pages"][pid] for pid in page_ids if pid in _IN_MEMORY_STORE["pages"]]


def clear_all(driver=None) -> None:
    """Clear graph store (used for clean testing)."""
    drv = driver or get_driver()
    if drv:
        try:
            with drv.session() as session:
                session.run("MATCH (n) DETACH DELETE n")
        except Exception:
            pass

    _IN_MEMORY_STORE["sites"].clear()
    _IN_MEMORY_STORE["pages"].clear()
    _IN_MEMORY_STORE["elements"].clear()
    _IN_MEMORY_STORE["livefields"].clear()
    _IN_MEMORY_STORE["site_pages"].clear()
    _IN_MEMORY_STORE["page_elements"].clear()
    _IN_MEMORY_STORE["page_livefields"].clear()
