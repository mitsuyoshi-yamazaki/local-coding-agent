"""文書 docs/request-formats.md を生成し直す: .venv/bin/python -m tests.request_formats"""

import sys

from tests.request_formats.document import DOCUMENT, REPOSITORY, render_document


def main() -> int:
    DOCUMENT.write_text(render_document(), encoding="utf-8")
    sys.stdout.write(f"書いた: {DOCUMENT.relative_to(REPOSITORY)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
