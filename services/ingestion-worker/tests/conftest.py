"""Shared pytest configuration for ingestion worker tests.

The service is a CLI-style package rather than an installed wheel during local
development, so tests add the service root to ``sys.path`` before importing the
``worker`` package.
"""

from __future__ import annotations

import sys
from pathlib import Path


SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))
