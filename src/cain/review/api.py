"""Read-only routes of the question map for the local web interface."""

from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse


def mount(app, memory_path):
    from cain.findings.archive import FindingsArchive
    from cain.memory.store import MemoryStore, MemoryStoreError
    from cain.review.board import ReviewBoard

    page = Path(__file__).resolve().parents[1] / "web" / "review.html"

    @app.get("/review/{domain}/{hypothesis_id}")
    def review_map(domain: str, hypothesis_id: str, as_of: str | None = None):
        memory = MemoryStore(memory_path)  # opened per request: the map is read from disk, not from memory
        try:
            return ReviewBoard(memory, FindingsArchive(memory)).question_map(
                domain, hypothesis_id, as_of=as_of or memory.now())
        except MemoryStoreError as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.get("/review-map", include_in_schema=False)
    def review_page():
        return FileResponse(page)
