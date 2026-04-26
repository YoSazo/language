import unittest

from backend.app.text_utils import normalize_japanese_text, pronunciation_feedback, similarity_score


class TextUtilsTests(unittest.TestCase):
    def test_normalize_hiragana_and_katakana(self) -> None:
        self.assertEqual(normalize_japanese_text("コンニチハ！"), "こんにちは")

    def test_similarity_score_is_high_for_same_sentence(self) -> None:
        self.assertEqual(similarity_score("今日は元気？", "今日は元気？"), 100)

    def test_pronunciation_feedback_mentions_difference(self) -> None:
        score, feedback = pronunciation_feedback("今日は元気？", "今日は平気？")
        self.assertLess(score, 100)
        self.assertTrue(feedback)


if __name__ == "__main__":
    unittest.main()

