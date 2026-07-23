import os
import unittest
from unittest.mock import MagicMock, call, patch

from db import (
    _DELETE_STALE_SANCTIONS_SQL,
    _UPSERT_SANCTION_SQL,
    create_sanctions,
)


class CreateSanctionsTests(unittest.TestCase):
    @patch('db.psycopg.connect')
    def test_upserts_snapshot_and_deletes_stale_entries_in_one_transaction(
        self,
        connect,
    ):
        cursor = MagicMock()
        connection = connect.return_value.__enter__.return_value
        connection.cursor.return_value.__enter__.return_value = cursor
        entries = [
            {
                'source_id': 'first',
                'target_type': 'individual',
                'names': ['First Name'],
                'positions': [],
                'listed_on': '2026-01-01',
                'remarks': 'Updated details',
            },
            {
                'source_id': 'second',
                'target_type': 'entity',
                'names': ['Second Entity'],
                'positions': [],
                'listed_on': None,
                'remarks': None,
            },
        ]
        expected_rows = [
            {**entry, 'source': 'ofac'}
            for entry in entries
        ]

        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test'}):
            create_sanctions('ofac', entries)

        connect.assert_called_once_with('postgresql://test')
        self.assertEqual(
            cursor.method_calls,
            [
                call.executemany(_UPSERT_SANCTION_SQL, expected_rows),
                call.execute(
                    _DELETE_STALE_SANCTIONS_SQL,
                    ('ofac', ['first', 'second']),
                ),
            ],
        )

    @patch('db.psycopg.connect')
    def test_does_not_replace_snapshot_with_an_empty_result(self, connect):
        create_sanctions('ofac', [])

        connect.assert_not_called()


if __name__ == '__main__':
    unittest.main()
