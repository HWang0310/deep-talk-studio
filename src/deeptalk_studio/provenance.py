"""Provider tool provenance extraction and report-source reconciliation."""

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple

from .sources import normalize_report_sources, normalize_url


@dataclass(frozen=True)
class SearchCall:
    call_id: str
    action_type: str
    queries: Tuple[str, ...]
    source_urls: Tuple[str, ...]


@dataclass(frozen=True)
class UrlCitation:
    url: str
    title: str
    output_item_id: str
    start_index: int
    end_index: int


@dataclass(frozen=True)
class ProviderProvenance:
    search_calls: Tuple[SearchCall, ...]
    citations: Tuple[UrlCitation, ...]


def _source_urls(values: Any) -> Tuple[str, ...]:
    urls: List[str] = []
    if not isinstance(values, list):
        return ()
    for value in values:
        if isinstance(value, str):
            urls.append(value)
        elif isinstance(value, dict) and isinstance(value.get("url"), str):
            urls.append(value["url"])
    return tuple(urls)


def _queries(action: Dict[str, Any]) -> Tuple[str, ...]:
    values = action.get("queries")
    if isinstance(values, list):
        return tuple(value for value in values if isinstance(value, str))
    value = action.get("query")
    return (value,) if isinstance(value, str) else ()


def extract_provenance(response: Dict[str, Any]) -> ProviderProvenance:
    search_calls: List[SearchCall] = []
    citations: List[UrlCitation] = []
    output = response.get("output", [])
    if not isinstance(output, list):
        return ProviderProvenance((), ())

    for item in output:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "web_search_call":
            action = item.get("action") if isinstance(item.get("action"), dict) else {}
            search_calls.append(
                SearchCall(
                    call_id=str(item.get("id", "")),
                    action_type=str(action.get("type", "unknown")),
                    queries=_queries(action),
                    source_urls=_source_urls(action.get("sources")),
                )
            )
        if item.get("type") != "message":
            continue
        for content in item.get("content", []) if isinstance(item.get("content"), list) else []:
            if not isinstance(content, dict):
                continue
            annotations = content.get("annotations", [])
            if not isinstance(annotations, list):
                continue
            for annotation in annotations:
                if not isinstance(annotation, dict) or annotation.get("type") != "url_citation":
                    continue
                nested = annotation.get("url_citation")
                details = nested if isinstance(nested, dict) else annotation
                url = details.get("url")
                if not isinstance(url, str):
                    continue
                citations.append(
                    UrlCitation(
                        url=url,
                        title=str(details.get("title", "")),
                        output_item_id=str(item.get("id", "")),
                        start_index=int(details.get("start_index", 0) or 0),
                        end_index=int(details.get("end_index", 0) or 0),
                    )
                )
    return ProviderProvenance(tuple(search_calls), tuple(citations))


def _append_ref(mapping: Dict[str, List[str]], url: str, reference: str) -> None:
    try:
        key = normalize_url(url)
    except (TypeError, ValueError):
        return
    mapping.setdefault(key, []).append(reference)


def _reference_maps(
    provenance: ProviderProvenance,
) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
    action_refs: Dict[str, List[str]] = {}
    citation_refs: Dict[str, List[str]] = {}
    for call in provenance.search_calls:
        for url in call.source_urls:
            _append_ref(action_refs, url, f"web_search_call:{call.call_id}")
    for citation in provenance.citations:
        _append_ref(
            citation_refs,
            citation.url,
            f"url_citation:{citation.output_item_id}:{citation.start_index}-{citation.end_index}",
        )
    return action_refs, citation_refs


def reconcile_source_records(
    sources: Iterable[Dict[str, Any]], provenance: ProviderProvenance
) -> List[Dict[str, Any]]:
    """Apply real API provenance to source records without changing their groups."""

    action_refs, citation_refs = _reference_maps(provenance)
    result: List[Dict[str, Any]] = []
    for original in sources:
        source = deepcopy(original)
        key = normalize_url(source["url"])
        source["normalized_url"] = key
        refs = list(dict.fromkeys(action_refs.get(key, []) + citation_refs.get(key, [])))
        source["inspection_method"] = "openai_web_search_tool" if refs else "not_inspected"
        source["provenance_status"] = "matched" if refs else "unmatched"
        source["provenance_refs"] = refs
        source["provenance_method"] = "url_citation" if citation_refs.get(key) else "web_search_action_source"
        result.append(source)
    return result


def reconcile_provenance(
    data: Dict[str, Any], provenance: ProviderProvenance
) -> Dict[str, Any]:
    """Match declared API sources to URLs actually returned by web search tools."""

    result = normalize_report_sources(deepcopy(data))
    reconciled_sources = reconcile_source_records(result["sources"], provenance)
    result["sources"] = reconciled_sources

    status_by_source: Dict[str, str] = {}
    for source in result["sources"]:
        status_by_source[source["id"]] = source["provenance_status"]

    supporting_sources: Dict[str, List[str]] = {}
    for link in result.get("evidence_links", []):
        if link.get("relation") == "supports":
            supporting_sources.setdefault(link["claim_id"], []).append(link["source_id"])
    for claim in result.get("claims", []):
        if claim.get("classification") != "confirmed_fact":
            continue
        source_ids = supporting_sources.get(claim["id"], [])
        if not any(status_by_source.get(source_id) == "matched" for source_id in source_ids):
            claim["classification"] = "unverified"
            claim["confidence"] = "low"
            claim["verification_status"] = "unverified"
            note = "API provenance 未匹配到该 confirmed_fact 的支持来源，已自动降级。"
            claim["notes"] = f"{claim['notes']} {note}".strip()
    return result
