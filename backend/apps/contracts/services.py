"""
The two end-to-end pipelines for this app:

1. process_contract(): upload -> extract -> chunk -> embed -> index
2. ask_question(): embed question -> vector search -> AI-synthesized answer

Both are intentionally synchronous (no Celery) per spec, and both run
entirely through the deterministic stub implementations in apps/common/
when the matching Azure/OpenAI env vars are not configured.
"""
from django.conf import settings
from django.db import transaction

from apps.common import ai, blob_store, document_intelligence, search_store

from .models import Contract, ContractChunk, ContractClause, ContractQuery

SEARCH_INDEX_NAME = "contract_chunks"
CHUNK_MAX_CHARS = 600


def chunk_text(text: str, max_chars: int = CHUNK_MAX_CHARS) -> list[str]:
    """Paragraph-first chunking, sub-splitting any paragraph longer than max_chars."""
    paragraphs = [p.strip() for p in text.replace("\r\n", "\n").split("\n\n") if p.strip()]
    if not paragraphs and text.strip():
        paragraphs = [text.strip()]

    chunks = []
    for paragraph in paragraphs:
        if len(paragraph) <= max_chars:
            chunks.append(paragraph)
            continue
        for start in range(0, len(paragraph), max_chars):
            chunks.append(paragraph[start:start + max_chars])
    return chunks


@transaction.atomic
def process_contract(contract: Contract) -> Contract:
    """Run the full upload -> extract -> chunk/embed -> index pipeline for one contract."""
    contract.status = Contract.Status.PROCESSING
    contract.save(update_fields=["status"])

    try:
        raw_bytes = blob_store.download_document(contract.blob_path)
        extraction = document_intelligence.extract_contract(raw_bytes, filename=contract.blob_path)

        contract.clauses.all().delete()
        clause_objs = [
            ContractClause(
                contract=contract,
                clause_type=clause["clause_type"],
                extracted_text=clause["extracted_text"],
                page_number=clause["page_number"],
                is_risky=clause["is_risky"],
            )
            for clause in extraction["clauses"]
        ]
        ContractClause.objects.bulk_create(clause_objs)

        contract.chunks.all().delete()
        text_chunks = chunk_text(extraction["full_text"])

        search_items = []
        chunk_objs = []
        for index, chunk in enumerate(text_chunks):
            search_doc_id = f"contract-{contract.id}-chunk-{index}"
            chunk_objs.append(
                ContractChunk(
                    contract=contract,
                    chunk_text=chunk,
                    chunk_index=index,
                    search_doc_id=search_doc_id,
                )
            )
        ContractChunk.objects.bulk_create(chunk_objs)

        for chunk_obj in contract.chunks.all():
            vector = ai.generate_embedding(chunk_obj.chunk_text)
            search_items.append({
                "id": chunk_obj.search_doc_id,
                "vector": vector,
                "payload": {
                    "contract_id": contract.id,
                    "chunk_id": chunk_obj.id,
                    "chunk_index": chunk_obj.chunk_index,
                    "text": chunk_obj.chunk_text[:500],
                },
            })

        if search_items:
            search_store.upsert_chunks(SEARCH_INDEX_NAME, search_items)

        contract.status = Contract.Status.PROCESSED
        contract.save(update_fields=["status"])
    except Exception:
        contract.status = Contract.Status.FAILED
        contract.save(update_fields=["status"])
        raise

    return contract


def _build_answer_prompt(question: str, results: list[dict]) -> list[dict]:
    context_lines = []
    for result in results:
        payload = result["payload"]
        context_lines.append(
            f"- (chunk_id={payload.get('chunk_id')}, contract_id={payload.get('contract_id')}, "
            f"score={result['score']:.3f}): {payload.get('text', '')}"
        )
    context_block = "\n".join(context_lines) if context_lines else "(no matching chunks found)"

    system_prompt = (
        "You are a legal contract analysis assistant. Answer the user's question using "
        "only the retrieved contract excerpts provided. Cite the chunk_id(s) you used."
    )
    user_prompt = f"Question: {question}\n\nRetrieved contract excerpts:\n{context_block}"
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def ask_question(user, question_text: str, contract: Contract | None = None, top_k: int = 5) -> ContractQuery:
    """Embed the question, retrieve top-k chunks (optionally scoped to one contract), and
    synthesize an answer via the chat model. Persists and returns a ContractQuery row."""
    query_vector = ai.generate_embedding(question_text)
    filters = {"contract_id": contract.id} if contract else None
    results = search_store.search(SEARCH_INDEX_NAME, query_vector, top_k=top_k, filters=filters)

    messages = _build_answer_prompt(question_text, results)
    answer_text = ai.chat_completion(messages)

    retrieved_chunk_ids = [r["payload"].get("chunk_id") for r in results if r["payload"].get("chunk_id")]

    return ContractQuery.objects.create(
        asked_by=user,
        contract=contract,
        question_text=question_text,
        answer_text=answer_text,
        retrieved_chunk_ids=retrieved_chunk_ids,
    )
