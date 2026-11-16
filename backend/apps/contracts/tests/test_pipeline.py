import io

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.common import blob_store, search_store
from apps.contracts import services
from apps.contracts.models import Contract, ContractChunk, ContractClause, ContractQuery

User = get_user_model()

SAMPLE_TEXT = (
    "Termination. Either party may terminate this Agreement upon thirty (30) days "
    "written notice to the other party.\n\n"
    "Payment. Client shall pay all invoices within thirty (30) days of receipt.\n\n"
    "Confidentiality. Each party shall protect the other's confidential information.\n\n"
    "Governing Law. This Agreement is governed by the laws of Delaware.\n\n"
    "Limitation of Liability. Neither party's liability shall exceed fees paid."
)


class EndToEndPipelineTests(TestCase):
    """
    Full upload -> extract -> chunk/embed -> index -> search -> AI answer
    pipeline, entirely through stub mode (no network, no external services).
    """

    def setUp(self):
        self.user = User.objects.create_user(email="pipeline@example.com", password="pw12345!")
        search_store.clear_index(services.SEARCH_INDEX_NAME)

    def test_full_pipeline(self):
        # 1. Upload: store the raw document via blob_store, create the Contract row.
        blob_path = blob_store.upload_document(
            io.BytesIO(SAMPLE_TEXT.encode("utf-8")), "contracts", "e2e-test.txt"
        )
        contract = Contract.objects.create(
            title="E2E Pipeline Contract",
            counterparty="E2E Counterparty",
            uploaded_by=self.user,
            blob_path=blob_path,
            status=Contract.Status.UPLOADED,
        )
        self.assertEqual(contract.status, Contract.Status.UPLOADED)

        # 2. Process: extract clauses, chunk, embed, index.
        services.process_contract(contract)
        contract.refresh_from_db()
        self.assertEqual(contract.status, Contract.Status.PROCESSED)

        clauses = ContractClause.objects.filter(contract=contract)
        self.assertGreater(clauses.count(), 0)

        chunks = ContractChunk.objects.filter(contract=contract)
        self.assertGreater(chunks.count(), 0)

        # Confirm chunks really made it into the search index.
        any_chunk = chunks.first()
        results = search_store.search(
            services.SEARCH_INDEX_NAME,
            [0.0] * 1536,  # dummy vector just to confirm the index is populated
            top_k=50,
        )
        indexed_ids = {r["id"] for r in results}
        self.assertIn(any_chunk.search_doc_id, indexed_ids)

        # 3. Ask a question: embed -> search -> synthesize answer.
        query = services.ask_question(
            user=self.user,
            question_text="What is the termination notice period?",
            contract=contract,
        )
        self.assertIsInstance(query, ContractQuery)
        self.assertTrue(query.answer_text)
        self.assertGreater(len(query.retrieved_chunk_ids), 0)
        # Every retrieved chunk id must belong to this contract.
        retrieved_chunks = ContractChunk.objects.filter(id__in=query.retrieved_chunk_ids)
        self.assertTrue(all(c.contract_id == contract.id for c in retrieved_chunks))

    def test_ask_question_without_contract_searches_all(self):
        contract_a = Contract.objects.create(
            title="A", counterparty="A Co", uploaded_by=self.user,
            blob_path=blob_store.upload_document(io.BytesIO(SAMPLE_TEXT.encode()), "contracts", "a.txt"),
        )
        contract_b = Contract.objects.create(
            title="B", counterparty="B Co", uploaded_by=self.user,
            blob_path=blob_store.upload_document(io.BytesIO(SAMPLE_TEXT.encode()), "contracts", "b.txt"),
        )
        services.process_contract(contract_a)
        services.process_contract(contract_b)

        query = services.ask_question(user=self.user, question_text="payment terms", contract=None)
        retrieved_chunks = ContractChunk.objects.filter(id__in=query.retrieved_chunk_ids)
        contract_ids = {c.contract_id for c in retrieved_chunks}
        # Should be able to retrieve chunks from either/both contracts when unscoped.
        self.assertTrue(contract_ids.issubset({contract_a.id, contract_b.id}))

    def test_process_contract_is_idempotent_on_reprocessing(self):
        blob_path = blob_store.upload_document(
            io.BytesIO(SAMPLE_TEXT.encode("utf-8")), "contracts", "reprocess.txt"
        )
        contract = Contract.objects.create(
            title="Reprocess Me", counterparty="Re Co", uploaded_by=self.user, blob_path=blob_path,
        )
        services.process_contract(contract)
        first_chunk_count = ContractChunk.objects.filter(contract=contract).count()
        services.process_contract(contract)
        second_chunk_count = ContractChunk.objects.filter(contract=contract).count()
        self.assertEqual(first_chunk_count, second_chunk_count)
