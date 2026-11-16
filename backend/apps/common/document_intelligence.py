"""
Document extraction abstraction.

Real path: Azure AI Document Intelligence via `azure-ai-documentintelligence`,
used when AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT + _KEY are configured. In
production this would call the "prebuilt-document" model (general key-value
+ layout extraction), which is also well suited to contract-style documents.

Stub path: treats the uploaded bytes as plain text (decoding leniently),
splits it into paragraphs, and produces deterministic, SHA256-seeded fake
clause extraction/classification so results are reproducible across runs
and across environments with zero network calls.
"""
import hashlib

from django.conf import settings

CLAUSE_TYPES = [
    "termination",
    "indemnification",
    "payment",
    "confidentiality",
    "governing_law",
    "limitation_of_liability",
]

PARAGRAPHS_PER_PAGE = 4
# Only every Nth paragraph is promoted to a classified "clause" - the rest is
# ordinary body text, mirroring how a real layout model would surface a
# handful of salient clauses out of a much longer document.
CLAUSE_EVERY_N_PARAGRAPHS = 2


def _digest(text: str) -> bytes:
    return hashlib.sha256(text.encode("utf-8")).digest()


def _decode(document_bytes: bytes) -> str:
    for encoding in ("utf-8", "latin-1"):
        try:
            return document_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    return document_bytes.decode("utf-8", errors="replace")


def _is_real() -> bool:
    return bool(settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and settings.AZURE_DOCUMENT_INTELLIGENCE_KEY)


def _extract_real(document_bytes: bytes) -> dict:
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
    from azure.core.credentials import AzureKeyCredential

    client = DocumentIntelligenceClient(
        endpoint=settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT,
        credential=AzureKeyCredential(settings.AZURE_DOCUMENT_INTELLIGENCE_KEY),
    )
    poller = client.begin_analyze_document(
        "prebuilt-document", AnalyzeDocumentRequest(bytes_source=document_bytes)
    )
    result = poller.result()
    full_text = result.content or ""
    paragraphs = [p.content for p in (result.paragraphs or []) if p.content and p.content.strip()]
    return _classify_paragraphs(full_text, paragraphs)


def _classify_paragraphs(full_text: str, paragraphs: list[str]) -> dict:
    clauses = []
    for index, paragraph in enumerate(paragraphs):
        if index % CLAUSE_EVERY_N_PARAGRAPHS != 0:
            continue
        digest = _digest(paragraph if paragraph.strip() else f"paragraph-{index}")
        clause_type = CLAUSE_TYPES[digest[0] % len(CLAUSE_TYPES)]
        is_risky = (digest[1] % 5) == 0
        page_number = (index // PARAGRAPHS_PER_PAGE) + 1
        clauses.append(
            {
                "clause_type": clause_type,
                "extracted_text": paragraph.strip(),
                "page_number": page_number,
                "is_risky": is_risky,
            }
        )
    return {"full_text": full_text, "paragraphs": paragraphs, "clauses": clauses}


def extract_contract(document_bytes: bytes, filename: str = "") -> dict:
    """
    Extract full text + classified clauses from a contract document.

    Returns {"full_text": str, "paragraphs": list[str], "clauses": [
        {"clause_type", "extracted_text", "page_number", "is_risky"}, ...
    ]}.
    """
    if _is_real():
        return _extract_real(document_bytes)

    text = _decode(document_bytes)
    raw_paragraphs = [p.strip() for p in text.replace("\r\n", "\n").split("\n\n")]
    paragraphs = [p for p in raw_paragraphs if p]
    if not paragraphs:
        paragraphs = [text.strip()] if text.strip() else []
    return _classify_paragraphs(text, paragraphs)


def is_stub_mode() -> bool:
    return not _is_real()
