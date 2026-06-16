from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from bottleneck_os.repository import build_seed_repository
from bottleneck_os.storage import connect, list_runs, load_repository_for_run, persist_run


class StorageTests(unittest.TestCase):
    def test_persist_run_and_list_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conn = connect(Path(tmp) / "runs.sqlite")
            repo = build_seed_repository()
            run_id = persist_run(
                conn,
                repo,
                date(2026, 6, 10),
                "seed_test",
                Path("reports/2026-06-10_report.md"),
                run_id="test_run",
            )
            self.assertEqual("test_run", run_id)
            rows = list_runs(conn)
            self.assertEqual(1, len(rows))
            self.assertEqual("test_run", rows[0]["run_id"])
            self.assertEqual(len(repo.documents), rows[0]["document_count"])
            self.assertEqual(len(repo.claims), rows[0]["claim_count"])
            conn.close()

    def test_load_repository_for_run_round_trips_documents_and_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conn = connect(Path(tmp) / "runs.sqlite")
            repo = build_seed_repository()
            persist_run(conn, repo, date(2026, 6, 10), "seed_test", run_id="roundtrip")
            loaded = load_repository_for_run(conn, "roundtrip")
            self.assertEqual(len(repo.documents), len(loaded.documents))
            self.assertEqual(len(repo.claims), len(loaded.claims))
            self.assertEqual({claim.id for claim in repo.claims}, {claim.id for claim in loaded.claims})
            conn.close()


if __name__ == "__main__":
    unittest.main()
