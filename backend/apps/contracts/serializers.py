from rest_framework import serializers

from .models import Contract, ContractChunk, ContractClause, ContractQuery


class ContractClauseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractClause
        fields = ["id", "contract", "clause_type", "extracted_text", "page_number", "is_risky"]
        read_only_fields = fields


class ContractChunkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractChunk
        fields = ["id", "contract", "chunk_text", "chunk_index", "search_doc_id"]
        read_only_fields = fields


class ContractSerializer(serializers.ModelSerializer):
    uploaded_by_email = serializers.EmailField(source="uploaded_by.email", read_only=True)
    clause_count = serializers.IntegerField(source="clauses.count", read_only=True)
    chunk_count = serializers.IntegerField(source="chunks.count", read_only=True)

    class Meta:
        model = Contract
        fields = [
            "id", "title", "counterparty", "contract_type", "effective_date", "expiry_date",
            "uploaded_by", "uploaded_by_email", "blob_path", "status", "created_at",
            "clause_count", "chunk_count",
        ]
        read_only_fields = ["id", "uploaded_by", "blob_path", "status", "created_at"]


class ContractUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    title = serializers.CharField(max_length=255)
    counterparty = serializers.CharField(max_length=255)
    contract_type = serializers.ChoiceField(choices=Contract.ContractType.choices, default=Contract.ContractType.OTHER)
    effective_date = serializers.DateField(required=False, allow_null=True)
    expiry_date = serializers.DateField(required=False, allow_null=True)


class ContractQuerySerializer(serializers.ModelSerializer):
    asked_by_email = serializers.EmailField(source="asked_by.email", read_only=True)

    class Meta:
        model = ContractQuery
        fields = [
            "id", "asked_by", "asked_by_email", "contract", "question_text",
            "answer_text", "retrieved_chunk_ids", "created_at",
        ]
        read_only_fields = ["id", "asked_by", "answer_text", "retrieved_chunk_ids", "created_at"]


class AskQuestionSerializer(serializers.Serializer):
    question_text = serializers.CharField()
    contract_id = serializers.IntegerField(required=False, allow_null=True)
    top_k = serializers.IntegerField(required=False, default=5, min_value=1, max_value=20)
