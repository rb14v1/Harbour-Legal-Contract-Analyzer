from django.apps import AppConfig


class ContractsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.contracts"
    label = "contracts"

    def ready(self):
        # The in-memory search_store fallback only lives for one process run.
        # On every process start (e.g. `manage.py runserver`), rebuild it from
        # whatever ContractChunk rows already exist in the DB so previously
        # processed/seeded contracts stay searchable without reprocessing.
        # Embeddings are deterministic (SHA256-seeded in stub mode), so
        # regenerating them here is equivalent to having persisted them.
        import sys

        # Only worth doing for a long-lived server process; every other
        # management command (migrate, test, shell, createsuperuser, ...)
        # either doesn't need it or already gets a warm index from the
        # seed data migration running in the same process.
        if "runserver" not in sys.argv:
            return

        try:
            self._warm_search_index()
        except Exception:
            # Tables may not exist yet (e.g. before first migrate) - safe to skip.
            pass

    def _warm_search_index(self):
        from apps.common import search_store

        if not search_store.is_stub_mode():
            return

        from apps.common import ai

        ContractChunk = self.get_model("ContractChunk")
        items = []
        for chunk in ContractChunk.objects.all().only(
            "id", "chunk_text", "chunk_index", "search_doc_id", "contract_id"
        ):
            vector = ai.generate_embedding(chunk.chunk_text)
            items.append({
                "id": chunk.search_doc_id,
                "vector": vector,
                "payload": {
                    "contract_id": chunk.contract_id,
                    "chunk_id": chunk.id,
                    "chunk_index": chunk.chunk_index,
                    "text": chunk.chunk_text[:500],
                },
            })
        if items:
            search_store.upsert_chunks("contract_chunks", items)
