from django.conf import settings
from django.db import models


class Contract(models.Model):
    class ContractType(models.TextChoices):
        NDA = "nda", "NDA"
        MSA = "msa", "Master Services Agreement"
        EMPLOYMENT = "employment", "Employment"
        LEASE = "lease", "Lease"
        LICENSING = "licensing", "Licensing"
        VENDOR = "vendor", "Vendor Agreement"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"
        PROCESSING = "processing", "Processing"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"

    title = models.CharField(max_length=255)
    counterparty = models.CharField(max_length=255)
    contract_type = models.CharField(max_length=32, choices=ContractType.choices, default=ContractType.OTHER)
    effective_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="uploaded_contracts"
    )
    blob_path = models.CharField(max_length=512, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.UPLOADED)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.counterparty})"


class ContractClause(models.Model):
    class ClauseType(models.TextChoices):
        TERMINATION = "termination", "Termination"
        INDEMNIFICATION = "indemnification", "Indemnification"
        PAYMENT = "payment", "Payment"
        CONFIDENTIALITY = "confidentiality", "Confidentiality"
        GOVERNING_LAW = "governing_law", "Governing Law"
        LIMITATION_OF_LIABILITY = "limitation_of_liability", "Limitation of Liability"

    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name="clauses")
    clause_type = models.CharField(max_length=32, choices=ClauseType.choices)
    extracted_text = models.TextField()
    page_number = models.PositiveIntegerField(default=1)
    is_risky = models.BooleanField(default=False)

    class Meta:
        ordering = ["page_number", "id"]

    def __str__(self):
        return f"{self.get_clause_type_display()} (p{self.page_number})"


class ContractChunk(models.Model):
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name="chunks")
    chunk_text = models.TextField()
    chunk_index = models.PositiveIntegerField()
    search_doc_id = models.CharField(max_length=128, unique=True)

    class Meta:
        ordering = ["chunk_index"]
        constraints = [
            models.UniqueConstraint(fields=["contract", "chunk_index"], name="unique_contract_chunk_index")
        ]

    def __str__(self):
        return f"Chunk {self.chunk_index} of contract {self.contract_id}"


class ContractQuery(models.Model):
    asked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="queries")
    contract = models.ForeignKey(
        Contract, on_delete=models.CASCADE, related_name="queries", null=True, blank=True,
        help_text="null means search across all contracts",
    )
    question_text = models.TextField()
    answer_text = models.TextField(blank=True)
    retrieved_chunk_ids = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "contract queries"

    def __str__(self):
        return self.question_text[:60]
