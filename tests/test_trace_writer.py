import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from local_coding_agent.trace.writer import TraceWriter, trace_path


class TracePathTest(unittest.TestCase):
    def test_names_file_by_start_time(self) -> None:
        path = trace_path(Path("traces"), datetime(2026, 10, 24, 15, 30, 12))
        self.assertEqual(path, Path("traces/20261024-153012.jsonl"))


class TraceWriterTest(unittest.TestCase):
    def test_appends_one_json_line_per_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "traces" / "run.jsonl"
            writer = TraceWriter(path)
            writer.write({"type": "request", "turn": 1})
            writer.write({"type": "response", "turn": 1, "text": "日本語"})
            lines = path.read_text(encoding="utf-8").splitlines()
        records = [json.loads(line) for line in lines]
        self.assertEqual([r["type"] for r in records], ["request", "response"])
        self.assertEqual(records[1]["text"], "日本語")
        self.assertIn("time", records[0])


if __name__ == "__main__":
    unittest.main()
