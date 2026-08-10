"""URL normalization and conservative source independence grouping."""

import re
import unicodedata
from copy import deepcopy
from typing import Any, Dict, Iterable, List
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


TRACKING_PARAMETERS = {
    "fbclid",
    "gclid",
    "dclid",
    "mc_cid",
    "mc_eid",
    "igshid",
    "ref",
    "source",
}


def normalize_url(value: str) -> str:
    parts = urlsplit(value.strip())
    scheme = parts.scheme.lower()
    hostname = (parts.hostname or "").lower()
    port = parts.port
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        hostname = f"{hostname}:{port}"
    path = re.sub(r"/{2,}", "/", parts.path or "/")
    if path != "/":
        path = path.rstrip("/")
    query_items = []
    for key, item_value in parse_qsl(parts.query, keep_blank_values=True):
        lowered = key.lower()
        if lowered.startswith("utm_") or lowered in TRACKING_PARAMETERS:
            continue
        query_items.append((key, item_value))
    query = urlencode(sorted(query_items))
    return urlunsplit((scheme, hostname, path, query, ""))


def _normalized_title(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "".join(character for character in normalized if character.isalnum())


def normalize_and_group_sources(sources: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return copied sources with deterministic URL and independence metadata."""

    result: List[Dict[str, Any]] = []
    source_by_id: Dict[str, Dict[str, Any]] = {}
    first_by_url: Dict[str, Dict[str, Any]] = {}
    first_by_publisher: Dict[str, Dict[str, Any]] = {}
    first_by_title: Dict[str, Dict[str, Any]] = {}
    next_group = 1

    for original in sources:
        source = deepcopy(original)
        source["normalized_url"] = normalize_url(source["url"])
        publisher_key = unicodedata.normalize("NFKC", source["publisher"]).casefold().strip()
        title_key = _normalized_title(source["title"])
        explicit_parent = source_by_id.get(source.get("syndication_of", ""))
        duplicate_parent = first_by_url.get(source["normalized_url"])
        title_parent = first_by_title.get(title_key)
        publisher_parent = first_by_publisher.get(publisher_key)

        if explicit_parent:
            source["independence_group"] = explicit_parent["independence_group"]
            source["independence_status"] = "syndicated"
        elif duplicate_parent:
            source["independence_group"] = duplicate_parent["independence_group"]
            source["independence_status"] = "duplicate"
            source["syndication_of"] = duplicate_parent["id"]
        elif title_parent and title_parent["publisher"].casefold() != source["publisher"].casefold():
            source["independence_group"] = title_parent["independence_group"]
            source["independence_status"] = "syndicated"
            source["syndication_of"] = title_parent["id"]
        elif publisher_parent:
            source["independence_group"] = publisher_parent["independence_group"]
            source["independence_status"] = "related"
            source["syndication_of"] = ""
        else:
            source["independence_group"] = f"IG{next_group}"
            next_group += 1
            if source.get("independence_status") != "unknown":
                source["independence_status"] = "independent"
            source["syndication_of"] = ""

        result.append(source)
        source_by_id[source["id"]] = source
        first_by_url.setdefault(source["normalized_url"], source)
        first_by_publisher.setdefault(publisher_key, source)
        first_by_title.setdefault(title_key, source)

    return result


def normalize_report_sources(data: Dict[str, Any]) -> Dict[str, Any]:
    result = deepcopy(data)
    result["sources"] = normalize_and_group_sources(result["sources"])
    groups = {source["id"]: source["independence_group"] for source in result["sources"]}
    for link in result.get("evidence_links", []):
        if link.get("source_id") in groups:
            link["independence_group"] = groups[link["source_id"]]
    return result
