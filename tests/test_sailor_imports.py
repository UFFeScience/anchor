import unittest


class SailorImportTests(unittest.TestCase):
    def test_sailor_imports(self) -> None:
        import anchor.sailor
        import anchor.sailor.beeai
        from anchor.sailor import compare_tools

        self.assertTrue(anchor.sailor)
        self.assertTrue(anchor.sailor.beeai)
        self.assertTrue(compare_tools)
