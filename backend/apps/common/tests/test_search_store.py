from django.test import TestCase

from apps.common import search_store


class SearchStoreStubTests(TestCase):
    def setUp(self):
        search_store.clear_index("unit-test-index")

    def test_is_stub_mode_by_default(self):
        self.assertTrue(search_store.is_stub_mode())

    def test_upsert_and_search_returns_closest_match(self):
        items = [
            {"id": "a", "vector": [1.0, 0.0, 0.0], "payload": {"label": "a"}},
            {"id": "b", "vector": [0.0, 1.0, 0.0], "payload": {"label": "b"}},
            {"id": "c", "vector": [0.9, 0.1, 0.0], "payload": {"label": "c"}},
        ]
        count = search_store.upsert_chunks("unit-test-index", items)
        self.assertEqual(count, 3)

        results = search_store.search("unit-test-index", [1.0, 0.0, 0.0], top_k=2)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["id"], "a")
        self.assertEqual(results[1]["id"], "c")

    def test_search_respects_filters(self):
        items = [
            {"id": "x1", "vector": [1.0, 0.0], "payload": {"contract_id": 1}},
            {"id": "x2", "vector": [1.0, 0.0], "payload": {"contract_id": 2}},
        ]
        search_store.upsert_chunks("unit-test-index", items)
        results = search_store.search("unit-test-index", [1.0, 0.0], top_k=5, filters={"contract_id": 2})
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "x2")

    def test_upsert_overwrites_existing_id(self):
        search_store.upsert_chunks("unit-test-index", [{"id": "a", "vector": [1.0], "payload": {"v": 1}}])
        search_store.upsert_chunks("unit-test-index", [{"id": "a", "vector": [1.0], "payload": {"v": 2}}])
        results = search_store.search("unit-test-index", [1.0], top_k=5)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["payload"]["v"], 2)
