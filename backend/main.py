"""ScoreLayer FastAPI app."""

from __future__ import annotations

import logging
import os
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from services import analyzer, omr

load_dotenv()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("scorelayer")

app = FastAPI(title="ScoreLayer", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_TYPES = {
    "image/png": "image/png",
    "image/jpeg": "image/jpeg",
    "image/jpg": "image/jpeg",
    "application/pdf": "application/pdf",
}


class AnalyzeResponse(BaseModel):
    musicxml: str
    annotations: list[dict[str, Any]]


class AnalyzeXMLRequest(BaseModel):
    musicxml: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_endpoint(file: UploadFile = File(...)) -> AnalyzeResponse:
    media_type = ALLOWED_TYPES.get((file.content_type or "").lower())
    if media_type is None:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported media type: {file.content_type}. Use jpg/png/pdf.",
        )

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty upload")

    try:
        musicxml = omr.image_to_musicxml(image_bytes, media_type=media_type)
    except Exception as e:
        log.exception("OMR failed")
        raise HTTPException(status_code=502, detail=f"OMR failed: {e}")

    try:
        annotations = analyzer.analyze(musicxml)
    except Exception as e:
        log.exception("Analysis failed")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")

    return AnalyzeResponse(musicxml=musicxml, annotations=annotations)


@app.post("/analyze-xml", response_model=AnalyzeResponse)
def analyze_xml(req: AnalyzeXMLRequest) -> AnalyzeResponse:
    """Useful for tests / debugging when you already have MusicXML."""
    annotations = analyzer.analyze(req.musicxml)
    return AnalyzeResponse(musicxml=req.musicxml, annotations=annotations)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=True)
