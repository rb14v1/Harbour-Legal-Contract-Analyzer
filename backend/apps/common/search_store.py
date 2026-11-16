"""
Vector/hybrid search abstraction (Azure AI Search).

Real path: `azure-search-documents` `SearchClient` against a pre-provisioned
index, used when AZURE_SEARCH_ENDPOINT + AZURE_SEARCH_KEY are configured.

Stub path: an in-process in-memory list of {id, vector, payload} per index
name, with cosine-similarity top-k search implemented in plain Python (no
external deps). This only needs to behave correctly within a single
test/process run - there is no persistence requirement, mirroring an
in-memory vector store fallback.
"""
import math

from django.conf import settings

# index_name -> list[{"id": str, "vector": list[float], "payload": dict}]
_MEMORY_INDEXES: dict[str, list[dict]] = {}


def _is_real() -> bool:
    return bool(settings.AZURE_SEARCH_ENDPOINT and settings.AZURE_SEARCH_KEY)


def _get_search_client(index_name: str):
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents import SearchClient

    return SearchClient(
        endpoint=settings.AZURE_SEARCH_ENDPOINT,
        index_name=index_name,
        credential=AzureKeyCredential(settings.AZURE_SEARCH_KEY),
    )


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def upsert_chunks(index_name: str, items: list[dict]) -> int:
    """
    `items`: list of {"id": str, "vector": list[float], "payload": dict}.
    Returns the number of items upserted.
    """
    if _is_real():
        client = _get_search_client(index_name)
        documents = [
            {"id": item["id"], "content_vector": item["vector"], **item["payload"]}
            for item in items
        ]
        client.upload_documents(documents=documents)
        return len(documents)

    bucket = _MEMORY_INDEXES.setdefault(index_name, [])
    existing_ids = {entry["id"]: i for i, entry in enumerate(bucket)}
    for item in items:
        record = {"id": item["id"], "vector": item["vector"], "payload": item["payload"]}
        if item["id"] in existing_ids:
            bucket[existing_ids[item["id"]]] = record
        else:
            bucket.append(record)
    return len(items)


def search(index_name: str, query_vector: list[float], top_k: int = 5, filters: dict | None = None) -> list[dict]:
    """
    Returns up to `top_k` results as [{"id", "score", "payload"}, ...],
    ordered by descending similarity. `filters` is an optional dict of exact
    payload field matches (e.g. {"contract_id": 3}).
    """
    if _is_real():
        from azure.search.documents.models import VectorizedQuery

        client = _get_search_client(index_name)
        odata_filter = None
        if filters:
            odata_filter = " and ".join(f"{k} eq {v!r}" for k, v in filters.items())
        vector_query = VectorizedQuery(vector=query_vector, k_nearest_neighbors=top_k, fields="content_vector")
        results = client.search(
            search_text=None, vector_queries=[vector_query], filter=odata_filter, top=top_k
        )
        output = []
        for result in results:
            payload = {k: v for k, v in result.items() if not k.startswith("@") and k != "content_vector"}
            output.append({"id": result["id"], "score": result.get("@search.score", 0.0), "payload": payload})
        return output

    bucket = _MEMORY_INDEXES.get(index_name, [])
    candidates = bucket
    if filters:
        candidates = [
            entry for entry in bucket
            if all(entry["payload"].get(k) == v for k, v in filters.items())
        ]
    scored = [
        {"id": entry["id"], "score": _cosine_similarity(query_vector, entry["vector"]), "payload": entry["payload"]}
        for entry in candidates
    ]
    scored.sort(key=lambda r: r["score"], reverse=True)
    return scored[:top_k]


def clear_index(index_name: str) -> None:
    """Testing helper: empty an in-memory index. No-op against the real backend."""
    if not _is_real():
        _MEMORY_INDEXES.pop(index_name, None)


def is_stub_mode() -> bool:
    return not _is_real()
