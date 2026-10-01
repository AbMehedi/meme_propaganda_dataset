# ============================================================================
# Bangla Meme Propaganda Dataset — Makefile (Docker shortcuts)
# ============================================================================
# Usage:
#   make up          — start containers (GPU)
#   make up-cpu      — start containers (CPU-only, no NVIDIA)
#   make download    — run Layer 2: download images
#   make ocr         — run Layer 3: EasyOCR extraction
#   make reconstruct — run Layer 3+: reading-order reconstruction
#   make verify      — run QA: visual OCR check
#   make annotate    — run LLM pre-annotation (auto-detect hardware)
#   make results     — view annotation summary
#   make shell       — open bash shell in app container
#   make pull-model  — pull an Ollama model (default: qwen2.5:3b)
#   make down        — stop all containers
#   make logs        — tail container logs
# ============================================================================

.PHONY: up up-cpu down logs shell \
        download ocr reconstruct verify annotate results \
        pull-model gpu-check

# ── Docker Lifecycle ─────────────────────────────────────────────────────────
up:
	docker compose up -d --build

up-cpu:
	docker compose -f docker-compose.yml -f docker-compose.cpu.yml up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

# ── Pipeline Steps ───────────────────────────────────────────────────────────
download:
	docker compose exec app python download_and_hash.py

ocr:
	docker compose exec app python ocr_and_store.py

reconstruct:
	docker compose exec app python reconstruct_text.py

verify:
	docker compose exec app python verify_ocr.py

annotate:
	docker compose exec app python annotate_ollama.py --auto

results:
	docker compose exec app python view_results.py --summary

# ── Utilities ────────────────────────────────────────────────────────────────
shell:
	docker compose exec app bash

MODEL ?= qwen2.5:3b
pull-model:
	docker compose exec ollama ollama pull $(MODEL)

gpu-check:
	docker compose exec app python -c "import torch; print('CUDA:', torch.cuda.is_available()); print('Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
