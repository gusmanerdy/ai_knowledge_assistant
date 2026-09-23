from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
FRONTEND_ROOT = PROJECT_ROOT / "frontend"
FRONTEND_PAGES = FRONTEND_ROOT / "pages"
FRONTEND_STATIC = FRONTEND_ROOT / "static"
STORAGE_ROOT = PROJECT_ROOT / "storage"
MODEL_SETTINGS_PATH = STORAGE_ROOT / "model_settings.json"
