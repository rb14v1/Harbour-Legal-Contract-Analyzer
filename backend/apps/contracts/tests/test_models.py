from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from apps.contracts.models import Contract, ContractChunk, ContractClause, ContractQuery

User = get_user_model()


class ContractModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="model@example.com", password="pw12345!")

    def test_create_contract_defaults(self):
        contract = Contract.objects.create(
            title="Test Agreement", counterparty="Acme Corp", uploaded_by=self.user,
        )
        self.assertEqual(contract.status, Contract.Status.UPLOADED)
        self.assertEqual(contract.contract_type, Contract.ContractType.OTHER)

    def test_clause_and_chunk_relations(self):
        contract = Contract.objects.create(title="T", counterparty="C", uploaded_by=self.user)
        clause = ContractClause.objects.create(
            contract=contract, clause_type="termination", extracted_text="text", page_number=1,
        )
        chunk = ContractChunk.objects.create(
            contract=contract, chunk_text="chunk", chunk_index=0, search_doc_id="doc-1",
        )
        self.assertEqual(contract.clauses.count(), 1)
        self.assertEqual(contract.chunks.count(), 1)
        self.assertEqual(clause.contract, contract)
        self.assertEqual(chunk.contract, contract)

    def test_chunk_index_unique_per_contract(self):
        contract = Contract.objects.create(title="T", counterparty="C", uploaded_by=self.user)
        ContractChunk.objects.create(contract=contract, chunk_text="a", chunk_index=0, search_doc_id="d1")
        with self.assertRaises(IntegrityError):
            ContractChunk.objects.create(contract=contract, chunk_text="b", chunk_index=0, search_doc_id="d2")

    def test_query_nullable_contract_means_search_all(self):
        query = ContractQuery.objects.create(
            asked_by=self.user, contract=None, question_text="q", answer_text="a",
        )
        self.assertIsNone(query.contract)
