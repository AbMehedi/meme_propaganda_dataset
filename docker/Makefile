# ============================================================================
# Bangla Meme Propaganda Dataset — Makefile (Docker shortcuts)
# ============================================================================
# Usage:
#   make up          — start pipeline container
#   make migrate     — run database schema migration
#   make download    — run Layer 2: download images
#   make ocr         — run Layer 3: EasyOCR extraction
#   make reconstruct — run Layer 3+: reading-order reconstruction
#   make verify      — run QA: visual OCR check
#   make shell       — open bash shell in app container
#   make gpu-check   — verify PyTorch CUDA / GPU availability
#   make down        — stop containers
#   make logs        — tail container logs
# ============================================================================

.PHONY: up down logs shell migrate download ocr reconstruct verify gpu-check

# ── Docker Lifecycle ─────────────────────────────────────────────────────────
up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

# ── Pipeline Steps ───────────────────────────────────────────────────────────
migrate:
	docker compose exec app python migrate_db.py

download:
	docker compose exec app python download_and_hash.py

ocr:
	docker compose exec app python ocr_and_store.py

reconstruct:
	docker compose exec app python reconstruct_text.py

verify:
	docker compose exec app python verify_ocr.py

# ── Utilities ────────────────────────────────────────────────────────────────
shell:
	docker compose exec app bash

gpu-check:
	docker compose exec app python -c "import torch; print('CUDA:', torch.cuda.is_available()); print('Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
