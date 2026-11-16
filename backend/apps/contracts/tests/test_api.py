import io

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.contracts.models import Contract

User = get_user_model()


class ContractApiTestsBase(APITestCase):
    def setUp(self):
        self.reviewer = User.objects.create_user(
            email="reviewer-api@example.com", password="pw12345!", role=User.Role.LEGAL_REVIEWER,
        )
        self.admin = User.objects.create_user(
            email="admin-api@example.com", password="pw12345!", role=User.Role.ADMIN,
            is_staff=True, is_superuser=True,
        )

    def auth_as(self, user):
        self.client.force_authenticate(user=user)


class ContractCrudPermissionTests(ContractApiTestsBase):
    def setUp(self):
        super().setUp()
        self.contract = Contract.objects.create(
            title="Permission Test", counterparty="Acme", uploaded_by=self.reviewer,
        )

    def test_unauthenticated_cannot_list(self):
        response = self.client.get(reverse("contract-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_reviewer_can_list_and_create(self):
        self.auth_as(self.reviewer)
        response = self.client.get(reverse("contract-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.post(reverse("contract-list"), {
            "title": "New Contract", "counterparty": "Beta Co", "contract_type": "nda",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["uploaded_by"], self.reviewer.id)

    def test_reviewer_cannot_delete(self):
        self.auth_as(self.reviewer)
        response = self.client.delete(reverse("contract-detail", args=[self.contract.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Contract.objects.filter(id=self.contract.id).exists())

    def test_admin_can_delete(self):
        self.auth_as(self.admin)
        response = self.client.delete(reverse("contract-detail", args=[self.contract.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Contract.objects.filter(id=self.contract.id).exists())


class ContractUploadAndProcessTests(ContractApiTestsBase):
    def test_upload_creates_contract_with_uploaded_status(self):
        self.auth_as(self.reviewer)
        upload_file = io.BytesIO(b"Termination. Either party may terminate.\n\nPayment. Due in 30 days.")
        upload_file.name = "contract.txt"
        response = self.client.post(reverse("contract-upload"), {
            "file": upload_file,
            "title": "Uploaded Contract",
            "counterparty": "Gamma Inc",
            "contract_type": "msa",
        }, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], Contract.Status.UPLOADED)
        self.assertTrue(response.data["blob_path"])

    def test_process_action_extracts_clauses_and_chunks(self):
        self.auth_as(self.reviewer)
        upload_file = io.BytesIO(
            b"Termination. Either party may terminate this agreement with notice.\n\n"
            b"Payment. Fees are due within thirty days of invoice.\n\n"
            b"Confidentiality. Both parties shall protect confidential information.\n\n"
            b"Governing Law. This agreement is governed by Delaware law."
        )
        upload_file.name = "contract.txt"
        upload_response = self.client.post(reverse("contract-upload"), {
            "file": upload_file, "title": "Process Me", "counterparty": "Delta LLC",
        }, format="multipart")
        contract_id = upload_response.data["id"]

        process_response = self.client.post(reverse("contract-process", args=[contract_id]))
        self.assertEqual(process_response.status_code, status.HTTP_200_OK)
        self.assertEqual(process_response.data["status"], Contract.Status.PROCESSED)

        clauses_response = self.client.get(reverse("contract-clauses", args=[contract_id]))
        self.assertEqual(clauses_response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(clauses_response.data), 0)


class ContractQueryApiTests(ContractApiTestsBase):
    def setUp(self):
        super().setUp()
        self.auth_as(self.reviewer)
        upload_file = io.BytesIO(
            b"Termination. Either party may terminate this agreement with notice.\n\n"
            b"Payment. Fees are due within thirty days of invoice."
        )
        upload_file.name = "contract.txt"
        upload_response = self.client.post(reverse("contract-upload"), {
            "file": upload_file, "title": "Query Target", "counterparty": "Epsilon",
        }, format="multipart")
        self.contract_id = upload_response.data["id"]
        self.client.post(reverse("contract-process", args=[self.contract_id]))

    def test_ask_question_scoped_to_contract(self):
        response = self.client.post(reverse("contract-query-list"), {
            "question_text": "What is the termination notice?",
            "contract_id": self.contract_id,
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["answer_text"])
        self.assertIsInstance(response.data["retrieved_chunk_ids"], list)

    def test_query_history_scoped_per_user(self):
        self.client.post(reverse("contract-query-list"), {"question_text": "Reviewer question"})

        self.auth_as(self.admin)
        self.client.post(reverse("contract-query-list"), {"question_text": "Admin question"})

        # Admin sees both.
        response = self.client.get(reverse("contract-query-list"))
        questions = [item["question_text"] for item in response.data["results"]]
        self.assertIn("Reviewer question", questions)
        self.assertIn("Admin question", questions)

        # Reviewer sees only their own.
        self.auth_as(self.reviewer)
        response = self.client.get(reverse("contract-query-list"))
        questions = [item["question_text"] for item in response.data["results"]]
        self.assertIn("Reviewer question", questions)
        self.assertNotIn("Admin question", questions)
