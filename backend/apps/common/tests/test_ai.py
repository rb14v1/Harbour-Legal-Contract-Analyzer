from django.test import TestCase

from apps.common import ai


class AiStubTests(TestCase):
    def test_is_stub_mode_by_default(self):
        self.assertTrue(ai.is_stub_mode())

    def test_generate_embedding_has_correct_dimensions(self):
        vector = ai.generate_embedding("termination clause text")
        self.assertEqual(len(vector), 1536)
        self.assertTrue(all(isinstance(v, float) for v in vector))

    def test_generate_embedding_is_deterministic(self):
        first = ai.generate_embedding("same input text")
        second = ai.generate_embedding("same input text")
        self.assertEqual(first, second)

    def test_generate_embedding_differs_for_different_text(self):
        first = ai.generate_embedding("alpha text")
        second = ai.generate_embedding("beta text")
        self.assertNotEqual(first, second)

    def test_pad_vector_truncates_and_pads(self):
        self.assertEqual(len(ai.pad_vector([1.0, 2.0, 3.0], 2)), 2)
        padded = ai.pad_vector([1.0, 2.0], 5)
        self.assertEqual(padded, [1.0, 2.0, 0.0, 0.0, 0.0])

    def test_chat_completion_returns_deterministic_stub_text(self):
        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "What is the termination notice period?"},
        ]
        first = ai.chat_completion(messages)
        second = ai.chat_completion(messages)
        self.assertEqual(first, second)
        self.assertIn("stub-answer", first)
