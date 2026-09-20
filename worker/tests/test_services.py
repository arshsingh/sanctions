"""Tests for worker source services."""

import unittest

from services import _seco_is_currently_listed


class SecoCurrentListingTests(unittest.TestCase):
    def test_imports_target_with_only_legacy_listing(self):
        entry = {
            'modification': {
                '@modification-type': 'listed',
            },
        }

        self.assertTrue(_seco_is_currently_listed(entry))

    def test_excludes_target_whose_latest_modification_is_de_listed(self):
        entry = {
            'modification': [
                {
                    '@modification-type': 'de-listed',
                    '@effective-date': '2026-03-01',
                },
                {
                    '@modification-type': 'listed',
                    '@effective-date': '2024-01-01',
                },
            ],
        }

        self.assertFalse(_seco_is_currently_listed(entry))

    def test_imports_target_listed_again_after_de_listing(self):
        entry = {
            'modification': [
                {
                    '@modification-type': 'de-listed',
                    '@effective-date': '2025-02-01',
                },
                {
                    '@modification-type': 'listed',
                    '@effective-date': '2026-04-01',
                },
                {
                    '@modification-type': 'listed',
                    '@effective-date': '2024-01-01',
                },
            ],
        }

        self.assertTrue(_seco_is_currently_listed(entry))

    def test_excludes_undated_legacy_de_listing(self):
        entry = {
            'modification': [
                {'@modification-type': 'listed'},
                {'@modification-type': 'de-listed'},
            ],
        }

        self.assertFalse(_seco_is_currently_listed(entry))


if __name__ == '__main__':
    unittest.main()
