from django.test import TestCase

from apps.common import document_intelligence


SAMPLE_TEXT = (
    "CONTRACT: Example Agreement\n\n"
    "Termination. Either party may terminate this agreement with notice.\n\n"
    "Payment. Fees are due within thirty days.\n\n"
    "Confidentiality. Both parties shall keep information confidential.\n\n"
    "Governing Law. This is governed by the laws of Delaware.\n"
)


class DocumentIntelligenceStubTests(TestCase):
    def test_is_stub_mode_by_default(self):
        self.assertTrue(document_intelligence.is_stub_mode())

    def test_extract_contract_returns_full_text_and_clauses(self):
        result = document_intelligence.extract_contract(SAMPLE_TEXT.encode("utf-8"))
        self.assertEqual(result["full_text"], SAMPLE_TEXT)
        self.assertGreater(len(result["paragraphs"]), 0)
        self.assertGreater(len(result["clauses"]), 0)
        for clause in result["clauses"]:
            self.assertIn(clause["clause_type"], document_intelligence.CLAUSE_TYPES)
            self.assertIsInstance(clause["is_risky"], bool)
            self.assertGreaterEqual(clause["page_number"], 1)

    def test_extraction_is_deterministic(self):
        first = document_intelligence.extract_contract(SAMPLE_TEXT.encode("utf-8"))
        second = document_intelligence.extract_contract(SAMPLE_TEXT.encode("utf-8"))
        self.assertEqual(first["clauses"], second["clauses"])

    def test_handles_non_utf8_bytes_without_raising(self):
        raw = "Café confidentiality clause".encode("latin-1")
        result = document_intelligence.extract_contract(raw)
        self.assertIsInstance(result["full_text"], str)
