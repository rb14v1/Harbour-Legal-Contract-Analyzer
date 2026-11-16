import io

from django.test import TestCase, override_settings

from apps.common import blob_store


class BlobStoreStubTests(TestCase):
    def test_is_stub_mode_when_no_connection_string(self):
        self.assertTrue(blob_store.is_stub_mode())

    def test_upload_and_download_roundtrip(self):
        content = b"hello contract world"
        blob_path = blob_store.upload_document(io.BytesIO(content), "test-container", "sample.txt")
        self.assertEqual(blob_path, "test-container/sample.txt")

        downloaded = blob_store.download_document(blob_path)
        self.assertEqual(downloaded, content)

    def test_upload_generates_name_when_not_given(self):
        blob_path = blob_store.upload_document(io.BytesIO(b"data"), "test-container")
        self.assertTrue(blob_path.startswith("test-container/"))
        self.assertEqual(blob_store.download_document(blob_path), b"data")

    @override_settings(AZURE_STORAGE_CONNECTION_STRING="fake-conn-string-not-stub")
    def test_is_stub_mode_false_when_connection_string_set(self):
        self.assertFalse(blob_store.is_stub_mode())
