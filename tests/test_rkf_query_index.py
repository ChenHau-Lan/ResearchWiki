from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from rkf.query_index import RetrievalQueryIndex, source_manifest_fingerprint


class RKFQueryIndexStorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / "source.json"
        self.source.write_text('{"title":"safe"}\n', encoding="utf-8")
        self.index = RetrievalQueryIndex(self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def fingerprint(self) -> str:
        return source_manifest_fingerprint((("source.json", self.source),))

    def test_round_trip_is_versioned_and_fingerprint_backed(self) -> None:
        source_fingerprint = self.fingerprint()
        self.assertEqual(
            self.index.load(source_fingerprint=source_fingerprint).state,
            "miss",
        )

        stored = self.index.store(
            source_fingerprint=source_fingerprint,
            payload={"records": [{"title": "safe"}]},
        )
        loaded = self.index.load(source_fingerprint=source_fingerprint)

        self.assertEqual(stored.state, "rebuilt")
        self.assertEqual(loaded.state, "hit")
        self.assertEqual(loaded.generation, stored.generation)
        self.assertEqual(loaded.payload, {"records": [{"title": "safe"}]})
        self.assertEqual(self.index.path.stat().st_mode & 0o777, 0o600)

    def test_changed_source_marks_projection_stale(self) -> None:
        source_fingerprint = self.fingerprint()
        self.index.store(source_fingerprint=source_fingerprint, payload={"records": []})
        self.source.write_text('{"title":"changed"}\n', encoding="utf-8")

        loaded = self.index.load(source_fingerprint=self.fingerprint())

        self.assertEqual(loaded.state, "stale")
        self.assertEqual(loaded.reason, "source-fingerprint-mismatch")

    def test_tampered_payload_fails_closed(self) -> None:
        source_fingerprint = self.fingerprint()
        self.index.store(source_fingerprint=source_fingerprint, payload={"records": []})
        with sqlite3.connect(self.index.path) as connection:
            connection.execute(
                "UPDATE query_index_snapshot SET payload = ? WHERE singleton = 1",
                (json.dumps({"records": [{"title": "forged"}]}),),
            )
            connection.commit()

        loaded = self.index.load(source_fingerprint=source_fingerprint)

        self.assertEqual(loaded.state, "fallback")
        self.assertEqual(loaded.reason, "payload-fingerprint-mismatch")
        self.assertIsNone(loaded.payload)

    def test_corrupt_index_fails_closed_without_overwriting_it(self) -> None:
        self.index.private_root.mkdir(mode=0o700)
        original = b"not a sqlite database"
        self.index.path.write_bytes(original)

        loaded = self.index.load(source_fingerprint=self.fingerprint())
        stored = self.index.store(source_fingerprint=self.fingerprint(), payload={})

        self.assertEqual(loaded.state, "fallback")
        self.assertEqual(stored.state, "fallback")
        self.assertEqual(self.index.path.read_bytes(), original)

    def test_disabled_index_never_creates_private_state(self) -> None:
        index = RetrievalQueryIndex(self.root, enabled=False)

        loaded = index.load(source_fingerprint=self.fingerprint())
        stored = index.store(source_fingerprint=self.fingerprint(), payload={})

        self.assertEqual(loaded.state, "disabled")
        self.assertEqual(stored.state, "disabled")
        self.assertFalse(index.private_root.exists())

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink support is required")
    def test_symlinked_private_root_is_never_followed(self) -> None:
        with tempfile.TemporaryDirectory() as outside_directory:
            outside = Path(outside_directory)
            self.index.private_root.symlink_to(outside, target_is_directory=True)

            loaded = self.index.load(source_fingerprint=self.fingerprint())
            stored = self.index.store(source_fingerprint=self.fingerprint(), payload={})

            self.assertEqual(loaded.state, "fallback")
            self.assertEqual(stored.state, "fallback")
            self.assertEqual(list(outside.iterdir()), [])

    @unittest.skipUnless(hasattr(os, "link"), "hard-link support is required")
    def test_hard_linked_index_target_is_never_written(self) -> None:
        with tempfile.TemporaryDirectory() as outside_directory:
            outside = Path(outside_directory) / "outside.db"
            original = b"outside content"
            outside.write_bytes(original)
            self.index.private_root.mkdir(mode=0o700)
            os.link(outside, self.index.path)

            stored = self.index.store(source_fingerprint=self.fingerprint(), payload={})

            self.assertEqual(stored.state, "fallback")
            self.assertEqual(stored.reason, "unsafe-index-file")
            self.assertEqual(outside.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
