from django.contrib import admin

from .models import Contract, ContractChunk, ContractClause, ContractQuery


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ["title", "counterparty", "contract_type", "status", "uploaded_by", "created_at"]
    list_filter = ["status", "contract_type"]
    search_fields = ["title", "counterparty"]


@admin.register(ContractClause)
class ContractClauseAdmin(admin.ModelAdmin):
    list_display = ["contract", "clause_type", "page_number", "is_risky"]
    list_filter = ["clause_type", "is_risky"]


@admin.register(ContractChunk)
class ContractChunkAdmin(admin.ModelAdmin):
    list_display = ["contract", "chunk_index", "search_doc_id"]


@admin.register(ContractQuery)
class ContractQueryAdmin(admin.ModelAdmin):
    list_display = ["question_text", "asked_by", "contract", "created_at"]
    search_fields = ["question_text"]
