"""queue_worker: quoted --command tolerance and the drain contract.

The backend command is separate shell words (argparse REMAINDER), but a
quoted single string must also work (it is the natural way to type the
flag). These tests pin normalize_command and drain_once against a stub
backend: answers land in done/, backend failures land in failed/ with
the error attached, and nothing is ever lost. No LLM backend required.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKER_PATH = ROOT / "jobs" / "local-llm-queue" / "queue_worker.py"

_spec = importlib.util.spec_from_file_location("queue_worker", WORKER_PATH)
worker = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(worker)


@pytest.fixture
def queue_dirs(tmp_path, monkeypatch):
    dirs = {}
    for name in ("pending", "processing", "done", "failed"):
        directory = tmp_path / name
        directory.mkdir()
        dirs[name] = directory
        monkeypatch.setattr(worker, name.upper(), directory)
    return dirs


def test_quoted_single_string_command_is_split():
    assert worker.normalize_command(["ollama run qwen3:4b"]) == \
        ["ollama", "run", "qwen3:4b"]


def test_separate_words_command_is_unchanged():
    assert worker.normalize_command(["ollama", "run", "qwen3:4b"]) == \
        ["ollama", "run", "qwen3:4b"]


def test_single_word_command_is_unchanged():
    assert worker.normalize_command(["/usr/local/bin/clerk-backend"]) == \
        ["/usr/local/bin/clerk-backend"]


def test_empty_quoted_command_splits_to_nothing():
    assert worker.normalize_command([""]) == []


def test_unbalanced_quotes_are_rejected():
    with pytest.raises(ValueError):
        worker.normalize_command(['ollama run "mistral'])


def test_drain_once_answers_and_archives(queue_dirs):
    prompt = queue_dirs["pending"] / "job-0001.md"
    prompt.write_text("say ok", encoding="utf-8")
    echo = [sys.executable, "-c",
            "import sys; sys.stdout.write(sys.stdin.read().upper())"]

    ok, failed = worker.drain_once(echo, timeout=30)

    assert (ok, failed) == (1, 0)
    answer = queue_dirs["done"] / "job-0001.answer.md"
    assert answer.read_text(encoding="utf-8").strip().endswith("SAY OK")
    assert (queue_dirs["done"] / "job-0001.md").exists()
    assert not list(queue_dirs["processing"].iterdir())
    assert not list(queue_dirs["pending"].iterdir())


def test_backend_failure_is_data_not_a_crash(queue_dirs):
    prompt = queue_dirs["pending"] / "job-0002.md"
    prompt.write_text("will fail", encoding="utf-8")
    failing = [sys.executable, "-c",
               "import sys; sys.stderr.write('boom'); sys.exit(3)"]

    ok, failed = worker.drain_once(failing, timeout=30)

    assert (ok, failed) == (0, 1)
    assert not (queue_dirs["done"] / "job-0002.answer.md").exists()
    text = (queue_dirs["failed"] / "job-0002.md").read_text(encoding="utf-8")
    assert text.startswith("will fail")
    assert "<!-- ERROR:" in text and "backend exited 3" in text


def test_missing_backend_program_lands_in_failed(queue_dirs):
    prompt = queue_dirs["pending"] / "job-0003.md"
    prompt.write_text("no such program", encoding="utf-8")

    ok, failed = worker.drain_once(
        ["definitely-not-a-real-backend-program"], timeout=30)

    assert (ok, failed) == (0, 1)
    text = (queue_dirs["failed"] / "job-0003.md").read_text(encoding="utf-8")
    assert "no such program" in text and "<!-- ERROR:" in text


def test_empty_backend_output_is_a_failure(queue_dirs):
    prompt = queue_dirs["pending"] / "job-0004.md"
    prompt.write_text("empty output", encoding="utf-8")
    silent = [sys.executable, "-c", ""]

    ok, failed = worker.drain_once(silent, timeout=30)

    assert (ok, failed) == (0, 1)
    text = (queue_dirs["failed"] / "job-0004.md").read_text(encoding="utf-8")
    assert "backend exited 0" in text

