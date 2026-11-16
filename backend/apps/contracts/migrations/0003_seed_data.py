"""
Idempotent seed data migration.

Uses RunPython + get_or_create with historical models only (apps.get_model),
and django.contrib.auth.hashers.make_password() for user passwords (never
set_password() on a historical model). The only non-ORM calls are to the
pure, model-free utility functions in apps/common/ (blob_store,
document_intelligence, ai, search_store), which is safe because they never
touch the ORM or "real" model classes.
"""
import io

from django.contrib.auth.hashers import make_password
from django.db import migrations

DEMO_PASSWORD = "DemoPass123!"

CHUNK_MAX_CHARS = 600


def _chunk_text(text, max_chars=CHUNK_MAX_CHARS):
    paragraphs = [p.strip() for p in text.replace("\r\n", "\n").split("\n\n") if p.strip()]
    if not paragraphs and text.strip():
        paragraphs = [text.strip()]
    chunks = []
    for paragraph in paragraphs:
        if len(paragraph) <= max_chars:
            chunks.append(paragraph)
        else:
            for start in range(0, len(paragraph), max_chars):
                chunks.append(paragraph[start:start + max_chars])
    return chunks


def _contract_text(title, counterparty, body_paragraphs):
    header = f"CONTRACT: {title}\nCOUNTERPARTY: {counterparty}\n"
    return header + "\n\n".join(body_paragraphs)


CONTRACT_SPECS = [
    {
        "title": "Master Services Agreement - Northwind Consulting",
        "counterparty": "Northwind Consulting Ltd.",
        "contract_type": "msa",
        "effective_date": "2024-01-15",
        "expiry_date": "2027-01-14",
        "status": "processed",
        "body": [
            "This Master Services Agreement governs all statements of work entered into "
            "between the parties for consulting and professional services.",
            "Termination. Either party may terminate this Agreement for convenience upon "
            "sixty (60) days written notice to the other party.",
            "Payment. Client shall pay all undisputed invoices within thirty (30) days of "
            "receipt. Late payments accrue interest at 1.5% per month.",
            "Indemnification. Each party shall indemnify the other against third-party "
            "claims arising from gross negligence or willful misconduct.",
            "Confidentiality. Each party shall protect the other's confidential information "
            "using at least the same degree of care it uses for its own confidential data.",
            "Governing Law. This Agreement is governed by the laws of the State of Delaware.",
            "Limitation of Liability. Neither party's aggregate liability shall exceed the "
            "total fees paid in the twelve (12) months preceding the claim.",
        ],
    },
    {
        "title": "Mutual Non-Disclosure Agreement - Pinecrest Analytics",
        "counterparty": "Pinecrest Analytics Inc.",
        "contract_type": "nda",
        "effective_date": "2024-03-01",
        "expiry_date": "2026-03-01",
        "status": "processed",
        "body": [
            "This Mutual Non-Disclosure Agreement is entered into to facilitate discussion "
            "of a potential business relationship between the parties.",
            "Confidentiality. Each receiving party agrees to hold the disclosing party's "
            "confidential information in strict confidence for a period of three (3) years.",
            "Termination. This Agreement may be terminated by either party with thirty (30) "
            "days written notice; confidentiality obligations survive termination.",
            "Governing Law. This Agreement shall be governed by the laws of the State of "
            "New York, without regard to conflict of law principles.",
            "No License. Nothing in this Agreement grants either party any license or "
            "ownership rights to the other party's intellectual property.",
        ],
    },
    {
        "title": "Employment Agreement - Senior Counsel Role",
        "counterparty": "Jordan Blake",
        "contract_type": "employment",
        "effective_date": "2023-09-01",
        "expiry_date": None,
        "status": "processed",
        "body": [
            "This Employment Agreement sets forth the terms of employment between the "
            "Company and the Employee for the position of Senior Counsel.",
            "Termination. The Company may terminate this Agreement for cause immediately, "
            "or without cause upon thirty (30) days written notice and severance pay.",
            "Payment. The Employee shall receive an annual base salary payable in "
            "accordance with the Company's standard payroll practices.",
            "Confidentiality. The Employee agrees not to disclose Company trade secrets "
            "during or after the term of employment.",
            "Indemnification. The Company shall indemnify the Employee for actions taken "
            "in good faith within the scope of employment.",
            "Governing Law. This Agreement is governed by the laws of the State of "
            "California.",
        ],
    },
    {
        "title": "Commercial Lease Agreement - Riverside Office Park",
        "counterparty": "Riverside Properties LLC",
        "contract_type": "lease",
        "effective_date": "2022-06-01",
        "expiry_date": "2027-05-31",
        "status": "processed",
        "body": [
            "This Commercial Lease Agreement covers approximately 12,000 square feet of "
            "office space located at Riverside Office Park, Suite 400.",
            "Payment. Tenant shall pay monthly base rent plus a pro-rata share of common "
            "area maintenance charges, due on the first day of each month.",
            "Termination. Landlord may terminate this Lease upon Tenant's uncured default "
            "after fifteen (15) days written notice.",
            "Limitation of Liability. Landlord's liability for any claim arising from this "
            "Lease shall not exceed the total rent paid in the prior six (6) months.",
            "Governing Law. This Lease is governed by the laws of the State of Texas.",
            "Indemnification. Tenant shall indemnify Landlord against claims arising from "
            "Tenant's use or occupancy of the premises.",
        ],
    },
    {
        "title": "Software Licensing Agreement - Helix Analytics Platform",
        "counterparty": "Helix Analytics Corp.",
        "contract_type": "licensing",
        "effective_date": "2024-02-01",
        "expiry_date": "2025-01-31",
        "status": "processed",
        "body": [
            "This Software Licensing Agreement grants Licensee a non-exclusive, "
            "non-transferable license to use the Helix Analytics Platform.",
            "Payment. Licensee shall pay an annual license fee in advance, non-refundable "
            "except as expressly stated in this Agreement.",
            "Termination. Licensor may terminate this Agreement immediately if Licensee "
            "breaches the license scope restrictions in Section 2.",
            "Confidentiality. Licensee shall not disclose the Platform's source code, "
            "APIs, or technical documentation to any third party.",
            "Limitation of Liability. Licensor's total liability under this Agreement "
            "shall not exceed the fees paid by Licensee in the preceding year.",
            "Governing Law. This Agreement is governed by the laws of the State of "
            "Washington.",
        ],
    },
    {
        "title": "Vendor Supply Agreement - Atlas Office Supplies",
        "counterparty": "Atlas Office Supplies Co.",
        "contract_type": "vendor",
        "effective_date": "2023-11-01",
        "expiry_date": "2025-10-31",
        "status": "processed",
        "body": [
            "This Vendor Supply Agreement governs the purchase of office supplies and "
            "consumables by the Company from Vendor on an ongoing basis.",
            "Payment. Company shall pay Vendor invoices within forty-five (45) days of "
            "delivery, subject to a 2% early-payment discount within ten (10) days.",
            "Termination. Either party may terminate this Agreement for convenience with "
            "ninety (90) days written notice.",
            "Indemnification. Vendor shall indemnify Company against claims of product "
            "defect or non-conformance with applicable safety standards.",
            "Governing Law. This Agreement is governed by the laws of the State of "
            "Illinois.",
        ],
    },
    {
        "title": "Data Processing Addendum - Summit Cloud Services",
        "counterparty": "Summit Cloud Services Inc.",
        "contract_type": "vendor",
        "effective_date": "2024-06-01",
        "expiry_date": "2026-05-31",
        "status": "uploaded",
        "body": [
            "This Data Processing Addendum has just been uploaded and is awaiting "
            "processing; no clauses have been extracted yet.",
        ],
    },
    {
        "title": "Equipment Financing Agreement - Cascade Capital",
        "counterparty": "Cascade Capital Partners",
        "contract_type": "other",
        "effective_date": "2023-04-01",
        "expiry_date": "2028-03-31",
        "status": "failed",
        "body": [
            "This Equipment Financing Agreement failed automated processing due to a "
            "corrupted source scan and requires manual re-upload.",
        ],
    },
]

SAMPLE_QUESTIONS = [
    ("What is the termination notice period in this contract?", 0),
    ("How are confidentiality obligations defined?", 1),
    ("Summarize payment terms across our vendor contracts.", None),
]


def seed_data(apps, schema_editor):
    from apps.common import ai, blob_store, search_store

    User = apps.get_model("users", "User")
    Contract = apps.get_model("contracts", "Contract")
    ContractClause = apps.get_model("contracts", "ContractClause")
    ContractChunk = apps.get_model("contracts", "ContractChunk")
    ContractQuery = apps.get_model("contracts", "ContractQuery")

    reviewer, _ = User.objects.get_or_create(
        email="reviewer@legalcontracts.demo",
        defaults={
            "full_name": "Riley Chen",
            "role": "legal_reviewer",
            "password": make_password(DEMO_PASSWORD),
            "is_staff": False,
            "is_superuser": False,
            "is_active": True,
        },
    )
    admin_user, _ = User.objects.get_or_create(
        email="admin@legalcontracts.demo",
        defaults={
            "full_name": "Avery Morgan",
            "role": "admin",
            "password": make_password(DEMO_PASSWORD),
            "is_staff": True,
            "is_superuser": True,
            "is_active": True,
        },
    )

    created_contracts = {}

    for index, spec in enumerate(CONTRACT_SPECS):
        contract, created = Contract.objects.get_or_create(
            title=spec["title"],
            counterparty=spec["counterparty"],
            defaults={
                "contract_type": spec["contract_type"],
                "effective_date": spec["effective_date"],
                "expiry_date": spec["expiry_date"],
                "uploaded_by": reviewer if index % 2 == 0 else admin_user,
                "status": "uploaded",
                "blob_path": "",
            },
        )
        created_contracts[index] = contract
        if not created:
            continue

        full_text = _contract_text(spec["title"], spec["counterparty"], spec["body"])
        blob_path = blob_store.upload_document(
            io.BytesIO(full_text.encode("utf-8")), "contracts", f"seed-contract-{index}.txt"
        )
        contract.blob_path = blob_path
        contract.status = spec["status"]
        contract.save(update_fields=["blob_path", "status"])

        if spec["status"] != "processed":
            continue

        from apps.common import document_intelligence

        extraction = document_intelligence.extract_contract(full_text.encode("utf-8"))

        for clause in extraction["clauses"]:
            ContractClause.objects.get_or_create(
                contract=contract,
                clause_type=clause["clause_type"],
                page_number=clause["page_number"],
                extracted_text=clause["extracted_text"],
                defaults={"is_risky": clause["is_risky"]},
            )

        text_chunks = _chunk_text(extraction["full_text"])
        search_items = []
        for chunk_index, chunk in enumerate(text_chunks):
            search_doc_id = f"contract-{contract.id}-chunk-{chunk_index}"
            chunk_obj, _ = ContractChunk.objects.get_or_create(
                contract=contract,
                chunk_index=chunk_index,
                defaults={"chunk_text": chunk, "search_doc_id": search_doc_id},
            )
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
            search_store.upsert_chunks("contract_chunks", search_items)

    # Sample query history, built directly (not via apps.contracts.services,
    # which binds to the *current* model classes and must never be imported
    # from a data migration).
    for question_text, contract_index in SAMPLE_QUESTIONS:
        contract = created_contracts.get(contract_index) if contract_index is not None else None
        query_vector = ai.generate_embedding(question_text)
        filters = {"contract_id": contract.id} if contract else None
        results = search_store.search("contract_chunks", query_vector, top_k=3, filters=filters)
        retrieved_chunk_ids = [r["payload"].get("chunk_id") for r in results if r["payload"].get("chunk_id")]
        context = "; ".join(r["payload"].get("text", "")[:120] for r in results)
        answer_text = ai.chat_completion([
            {"role": "system", "content": "You are a legal contract analysis assistant."},
            {"role": "user", "content": f"Question: {question_text}\n\nContext: {context}"},
        ])
        ContractQuery.objects.get_or_create(
            asked_by=reviewer,
            contract=contract,
            question_text=question_text,
            defaults={"answer_text": answer_text, "retrieved_chunk_ids": retrieved_chunk_ids},
        )


def unseed_data(apps, schema_editor):
    # Intentionally a no-op: seed data is additive demo content, not something
    # we need to tear down on reverse migration.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("contracts", "0002_initial"),
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_data, unseed_data),
    ]
