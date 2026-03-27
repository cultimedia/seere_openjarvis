#!/usr/bin/env python
"""Asset Intelligence Runner — execute asset cataloging and analysis operative.

Usage:
    python scripts/run_asset_intelligence.py [--test-mode] [--output report.md]
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from openjarvis.agents.asset_intelligence import AssetIntelligenceOperative
from openjarvis.core.registry import EngineRegistry
from openjarvis.tools.storage.sqlite import SQLiteMemory

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Asset Intelligence Operative")
    parser.add_argument(
        "--test-mode",
        action="store_true",
        help="Test with only Midjourney folder (first 10 images)",
    )
    parser.add_argument(
        "--output",
        default="asset_intelligence_report.md",
        help="Output markdown file path (default: asset_intelligence_report.md)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of images to process in each batch (default: 10)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit total number of images to process (for testing)",
    )

    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("Asset Intelligence Operative")
    logger.info("=" * 70)

    # 1. Initialize components
    logger.info("Initializing components...")

    # Engine for text-only orchestrator synthesis
    # Use Ollama engine for theme synthesis with qwen3:14b
    engine_cls = EngineRegistry.get("ollama")
    if engine_cls is None:
        # Fallback: manually register
        from openjarvis.engine.openai_compat_engines import _ENGINES
        logger.error("Ollama engine not found in registry")
        sys.exit(1)

    engine = engine_cls()

    # SQLite memory backend
    memory = SQLiteMemory()
    logger.info(f"Memory backend: {memory.count()} documents currently stored")

    # Source folders (test mode = Midjourney only)
    source_folders = None
    if args.test_mode:
        source_folders = [
            "~/Creative Cloud Files  wilkins.keith@gmail.com 1853487558315A8D0A495ED5@AdobeID/Midjourney"
        ]
        logger.info("TEST MODE: Scanning only Midjourney folder")

    # 2. Create operative
    # Vision analysis: Qwen2-VL-7B (MLX, loaded in-process)
    # Theme synthesis: qwen3:14b (Ollama, via engine)
    operative = AssetIntelligenceOperative(
        engine=engine,
        model="qwen3:14b",  # Text-only orchestrator for theme synthesis
        memory_backend=memory,
        source_folders=source_folders,
        batch_size=args.batch_size,
        # mlx_vision_model_path="mlx-community/Qwen2-VL-7B-Instruct-4bit"  # default
    )

    # 3. Scan and analyze assets
    logger.info("\n" + "=" * 70)
    logger.info("Phase 1: Scanning and analyzing assets")
    logger.info("=" * 70)

    try:
        summary = operative.scan_and_analyze_assets(limit=args.limit)
        logger.info(f"\nScan complete: {summary}")
    except Exception as exc:
        logger.error(f"Scan failed: {exc}", exc_info=True)
        sys.exit(1)

    # 4. Synthesize themes
    logger.info("\n" + "=" * 70)
    logger.info("Phase 2: Synthesizing themes")
    logger.info("=" * 70)

    try:
        themes = operative.synthesize_themes()
        logger.info("Theme synthesis complete")
    except Exception as exc:
        logger.error(f"Theme synthesis failed: {exc}", exc_info=True)
        themes = "Theme synthesis failed"

    # 5. Generate report
    logger.info("\n" + "=" * 70)
    logger.info("Phase 3: Generating report")
    logger.info("=" * 70)

    try:
        report = operative.generate_report(themes, summary)

        # Save to file
        output_path = Path(args.output)
        output_path.write_text(report, encoding="utf-8")

        logger.info(f"\n✅ Report saved to: {output_path.absolute()}")
        logger.info(f"   Total assets analyzed: {summary['analyzed']}")
        logger.info(f"   Errors: {summary['errors']}")

    except Exception as exc:
        logger.error(f"Report generation failed: {exc}", exc_info=True)
        sys.exit(1)

    logger.info("\n" + "=" * 70)
    logger.info("Asset Intelligence Operative Complete")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
