import unittest

from scripts.collect_docs_sitemap import _extract_content_text, _normalize_content_lines


class FakeTag:
    def __init__(self, text):
        self._text = text

    def get_text(self, separator=" ", strip=False):
        text = self._text
        if strip:
            text = text.strip()
        return text


class FakeArticle:
    def __init__(self, primary_texts=None, fallback_lines=None):
        self._primary_texts = primary_texts or {}
        self._fallback_lines = fallback_lines or []

    def find_all(self, tags):
        found = []
        for tag in tags:
            for text in self._primary_texts.get(tag, []):
                found.append(FakeTag(text))
        return found

    def get_text(self, separator="\n", strip=False):
        text = separator.join(self._fallback_lines)
        if strip:
            text = text.strip()
        return text


class TestCollectDocsSitemapExtraction(unittest.TestCase):
    def test_normalize_lines_removes_duplicates_and_boilerplate(self):
        lines = [
            "Table of Contents",
            "   Query Result   ",
            "Query Result",
            "Next",
            "A valid descriptive line",
        ]

        result = _normalize_content_lines(lines)

        self.assertEqual(result, ["Query Result", "A valid descriptive line"])

    def test_extract_content_text_supports_glossary_definition_markup(self):
        article = FakeArticle(
            primary_texts={
                "h2": ["Query Result"],
                "dd": ["Result object returned by a query operation with metadata."],
            }
        )

        text = _extract_content_text(article)

        self.assertIn("Query Result", text)
        self.assertIn("Result object returned by a query operation", text)
        self.assertGreater(len(text), 40)

    def test_extract_content_text_falls_back_to_raw_text_when_markup_is_sparse(self):
        article = FakeArticle(
            primary_texts={},
            fallback_lines=[
                "This page uses custom markup but still has meaningful content.",
                "Additional technical context for indexing behavior.",
            ],
        )

        text = _extract_content_text(article)

        self.assertIn("custom markup", text)
        self.assertIn("indexing behavior", text)


if __name__ == "__main__":
    unittest.main()
