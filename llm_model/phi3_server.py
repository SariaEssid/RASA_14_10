"""
llm_model/phi3_server.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Optional
from fastapi import FastAPI, HTTPException
from llama_cpp import Llama
from pydantic import BaseModel
from actions.settings.settings import settings

import os
import psutil
import logging

log = logging.getLogger(__name__)

app = FastAPI(title="Phi-3-mini LLM API", version="1.0")

# --- MODEL CONFIGURATION ---
MODEL_FILENAME = os.getenv("PHI3_GGUF_FILENAME", "Phi-3-mini-4k-instruct-q4.gguf")
MODEL_PATH = Path(settings.PHI_MODEL_PATH) / MODEL_FILENAME

EXISTING_THREADS = int(os.cpu_count())

N_THREADS = int(os.getenv("PHI3_THREADS", "30"))
N_BATCH = int(os.getenv("PHI3_BATCH", "64"))
CTX_SIZE = int(os.getenv("PHI3_CTX", "4096"))
N_GPU_LAYERS = int(os.getenv("PHI3_GPU_LAYERS", "0"))

_MODEL_LOCK = Lock()
_MODEL: Optional[Llama] = None
_MODEL_LOAD_ERROR: Optional[str] = None


@app.on_event("startup")
def _startup_load_model() -> None:
    """
    Load Phi-3 at startup, but keep the server alive if it fails so you can see /health.
    """
    global _MODEL, _MODEL_LOAD_ERROR

    if not MODEL_PATH.exists():
        _MODEL = None
        _MODEL_LOAD_ERROR = (
            f"-> 3. Phi-3 GGUF not found at '{MODEL_PATH}'. "
            f"-> Check env PHI3_PATH='{settings.PHI_MODEL_PATH}' and PHI3_GGUF_FILENAME='{MODEL_FILENAME}'."
        )
        log.info(f"❌ {_MODEL_LOAD_ERROR} [{datetime.now()}]")
        return

    log.info(
        f"->\n🚀  Loading PHI-3 model {MODEL_PATH} at [{datetime.now()}]\n"
             f"▫  EXIST THEDS | {EXISTING_THREADS} \n"
             f"▫  USED THREDS | {N_THREADS} \n"
             f"▫  batch       | {N_BATCH} \n"
             f"▫  ctx         | {CTX_SIZE} \n"
             f"▫  gpu_layers  | {N_GPU_LAYERS}\n"
             f"▫  CPU COUNT   | {str(psutil.cpu_count(logical=False))}\n"
             f"▫  CPU LOGICAL | {str(psutil.cpu_count(logical=True))}\n"
             f"▫  CPU FREQ    | {str(psutil.cpu_freq())}"
    )

    try:
        _MODEL = Llama(
            model_path=str(MODEL_PATH),
            n_ctx=CTX_SIZE,
            n_threads=N_THREADS,
            n_batch=N_BATCH,
            n_gpu_layers=N_GPU_LAYERS,
            verbose=False,
            use_mlock=False,
            embedding=False,
        )
        _MODEL_LOAD_ERROR = None
        log.info(f"✅ Phi-3 model loaded successfully [{datetime.now()}]")
    except Exception as exc:
        _MODEL = None
        _MODEL_LOAD_ERROR = f"Phi-3 model load failed: {exc.__class__.__name__}: {exc}"
        log.info(f"❌ {_MODEL_LOAD_ERROR} [{datetime.now()}]")


class PromptRequest(BaseModel):
    prompt: str
    max_tokens: int = 200
    temperature: float = 0.0
    stop: Optional[list[str]]


@app.get("/health")
def health():
    return {
        "status": "ok" if _MODEL is not None else "error",
        "model_path": str(MODEL_PATH),
        "loaded": _MODEL is not None,
        "error": _MODEL_LOAD_ERROR,
    }


@app.post("/generate")
def generate(request: PromptRequest):
    """Generate text using Phi-3-mini model."""
    if _MODEL is None:
        raise HTTPException(status_code=503, detail=_MODEL_LOAD_ERROR or "Phi-3 model not loaded")

    with _MODEL_LOCK:
        response = _MODEL(
            request.prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            stop=request.stop,
            echo=False,
        )

    text = response["choices"][0]["text"].strip()
    return {"response": text, "timestamp": datetime.now().isoformat()}