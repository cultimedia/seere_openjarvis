"""AssetIntelligenceOperative — vision-based asset cataloging and analysis.

Scans image directories, analyzes each asset with MLX VLM (Python API),
stores structured metadata in SQLite/FTS5, then synthesizes thematic insights
via orchestrator.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from mlx_vlm import load, generate
from mlx_vlm.prompt_utils import apply_chat_template
from mlx_vlm.utils import load_config

from openjarvis.agents.operative import OperativeAgent
from openjarvis.core.events import EventBus
from openjarvis.core.registry import AgentRegistry
from openjarvis.core.types import Message, Role
from openjarvis.engine._stubs import InferenceEngine
from openjarvis.tools._stubs import BaseTool
from openjarvis.tools.storage._stubs import MemoryBackend

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SOURCE_FOLDERS = [
    "~/Creative Cloud Files  wilkins.keith@gmail.com 1853487558315A8D0A495ED5@AdobeID/Midjourney",
    "~/Creative Cloud Files  wilkins.keith@gmail.com 1853487558315A8D0A495ED5@AdobeID/Behance 2023",
    "~/Creative Cloud Files  wilkins.keith@gmail.com 1853487558315A8D0A495ED5@AdobeID/OTW Templates",
    "~/Creative Cloud Files  wilkins.keith@gmail.com 1853487558315A8D0A495ED5@AdobeID/milanote",
    "~/Creative Cloud Files  wilkins.keith@gmail.com 1853487558315A8D0A495ED5@AdobeID/outtamyhead",
    "~/Creative Cloud Files  wilkins.keith@gmail.com 1853487558315A8D0A495ED5@AdobeID/Legacy Cult",
]

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg"}

# Vision model for per-image analysis (Qwen2-VL-7B - known working vision model)
MLX_VISION_MODEL_PATH = "mlx-community/Qwen2-VL-7B-Instruct-4bit"

# Analysis prompt for structured JSON extraction
ASSET_ANALYSIS_PROMPT = """Analyze this creative asset and return structured JSON with the following fields:

{
  "asset_type": "photo|illustration|logo|template|mockup|icon|texture|other",
  "style_tags": ["tag1", "tag2", "tag3"],  // 3-5 descriptive style tags
  "mood": "energetic|calm|professional|playful|dark|bright|minimal|complex",
  "color_palette": ["#hex1", "#hex2", "#hex3"],  // dominant colors
  "use_cases": ["web design", "branding", "social media"],  // 2-4 potential uses
  "quality_tier": "draft|production|archive",
  "commercial_potential": "high|medium|low",
  "notes": "brief description of key visual elements"
}

Return ONLY valid JSON, no explanation."""

# ---------------------------------------------------------------------------
# AssetIntelligenceOperative
# ---------------------------------------------------------------------------


@AgentRegistry.register("asset_intelligence")
class AssetIntelligenceOperative(OperativeAgent):
    """Operative agent for intelligent asset cataloging and analysis.

    Two-model architecture:
    - Qwen2-VL-7B-Instruct-4bit: Dedicated vision analyst for per-image analysis
    - Orchestrator engine (text-only): Theme synthesis across all assets

    Workflow:
    1. Scan source folders for images (PNG/JPG/SVG)
    2. For each image: Qwen2-VL vision analysis → structured JSON
    3. Store metadata in SQLite/FTS5 memory backend
    4. Run text orchestrator pass to identify thematic clusters
    5. Generate markdown report with insights
    """

    agent_id = "asset_intelligence"
    accepts_tools = True

    def __init__(
        self,
        engine: InferenceEngine,
        model: str,
        *,
        tools: Optional[List[BaseTool]] = None,
        bus: Optional[EventBus] = None,
        memory_backend: Optional[MemoryBackend] = None,
        source_folders: Optional[List[str]] = None,
        mlx_vision_model_path: str = MLX_VISION_MODEL_PATH,
        batch_size: int = 10,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            engine,
            model,
            tools=tools,
            bus=bus,
            memory_backend=memory_backend,
            operator_id="asset_intelligence",
            **kwargs,
        )
        self._source_folders = source_folders or SOURCE_FOLDERS
        self._batch_size = batch_size
        self._analyzed_count = 0
        self._error_count = 0

        # Load MLX vision model once at initialization (Qwen2-VL for vision analysis)
        logger.info(f"Loading MLX vision model: {mlx_vision_model_path}")
        logger.info("This may take a few minutes on first run (~4GB download)...")
        self._mlx_model, self._mlx_processor = load(mlx_vision_model_path)
        self._mlx_config = load_config(mlx_vision_model_path)
        logger.info("✅ MLX vision model loaded successfully")
        logger.info(f"   Orchestrator engine ({model}) will handle theme synthesis")

    # -----------------------------------------------------------------------
    # Main workflow methods
    # -----------------------------------------------------------------------

    def scan_and_analyze_assets(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """Main entry point: scan folders, analyze images, store metadata.

        Args:
            limit: Optional limit on number of images to process (for testing)

        Returns:
            Summary dict with counts and errors.
        """
        logger.info("Starting asset intelligence scan...")

        # 1. Discover all image files
        image_paths = self._discover_images()
        if limit:
            image_paths = image_paths[:limit]
            logger.info(f"Found {len(image_paths)} images (limited to {limit} for testing)")
        else:
            logger.info(f"Found {len(image_paths)} images across {len(self._source_folders)} folders")

        # 2. Analyze each image in batches
        for i in range(0, len(image_paths), self._batch_size):
            batch = image_paths[i:i + self._batch_size]
            logger.info(f"Processing batch {i//self._batch_size + 1} ({len(batch)} images)")

            for img_path in batch:
                try:
                    self._analyze_and_store_image(img_path)
                    self._analyzed_count += 1
                except Exception as exc:
                    logger.error(f"Failed to analyze {img_path}: {exc}")
                    self._error_count += 1

        logger.info(
            f"Asset scan complete: {self._analyzed_count} analyzed, "
            f"{self._error_count} errors"
        )

        return {
            "total_found": len(image_paths),
            "analyzed": self._analyzed_count,
            "errors": self._error_count,
        }

    def synthesize_themes(self) -> str:
        """Run orchestrator pass over all asset descriptions to find themes.

        Returns:
            Synthesized themes and patterns as markdown.
        """
        if not self._memory_backend:
            return "No memory backend configured"

        logger.info("Synthesizing themes from asset metadata...")

        # Retrieve all stored asset metadata
        results = self._memory_backend.retrieve(
            "asset_type style_tags mood", top_k=1000
        )

        if not results:
            return "No asset metadata found in memory"

        # Build synthesis prompt for orchestrator
        metadata_summary = "\n\n".join(
            f"**Asset {i+1}:** {r.content[:500]}"
            for i, r in enumerate(results[:100])  # Cap at 100 for context
        )

        synthesis_prompt = f"""Analyze the following creative asset metadata and identify:

1. **Thematic clusters** — groups of assets with similar styles/moods
2. **Dominant aesthetics** — recurring visual patterns across the collection
3. **Unnamed styles** — aesthetic directions that don't fit standard categories
4. **Commercial opportunities** — high-potential asset groups for monetization
5. **Gaps** — missing asset types or styles in the collection

## Asset Metadata

{metadata_summary}

## Analysis

Provide structured markdown with clear sections for each category above."""

        # Use parent's _generate method with proper Message objects
        # Note: _generate uses self._temperature and self._max_tokens, so don't pass them again
        messages = [Message(role=Role.USER, content=synthesis_prompt)]

        # Temporarily override defaults for synthesis pass
        old_temp = self._temperature
        old_max = self._max_tokens
        self._temperature = 0.7
        self._max_tokens = 2048

        try:
            result = self._generate(messages)
            return result.get("content", "") if isinstance(result, dict) else str(result)
        finally:
            # Restore original values
            self._temperature = old_temp
            self._max_tokens = old_max

    def generate_report(self, themes: str, summary: Dict[str, Any]) -> str:
        """Generate final markdown report with clusters and insights.

        Args:
            themes: Synthesized theme analysis from orchestrator
            summary: Scan summary dict

        Returns:
            Markdown report content
        """
        report = f"""# Asset Intelligence Report

## Scan Summary

- **Total images found:** {summary['total_found']}
- **Successfully analyzed:** {summary['analyzed']}
- **Errors:** {summary['errors']}
- **Source folders:** {len(self._source_folders)}

---

## Thematic Analysis

{themes}

---

## Next Steps

### Recommendations

1. **High-value clusters** — Identify asset groups with strong commercial potential
2. **Style consolidation** — Merge similar aesthetic directions
3. **Gap filling** — Create missing asset types to round out portfolio
4. **Archive cleanup** — Move low-quality/draft assets to separate storage

### Search Examples

Use OpenJarvis memory search to explore assets:

```bash
jarvis memory search "professional logo minimal"
jarvis memory search "vibrant social media template"
jarvis memory search "dark moody photography"
```

---

*Generated by AssetIntelligenceOperative • {self._analyzed_count} assets indexed*
"""
        return report

    # -----------------------------------------------------------------------
    # Image processing methods
    # -----------------------------------------------------------------------

    def _discover_images(self) -> List[Path]:
        """Scan source folders and return list of image file paths."""
        image_paths: List[Path] = []

        for folder_str in self._source_folders:
            folder = Path(folder_str).expanduser()

            if not folder.exists():
                logger.warning(f"Source folder not found: {folder}")
                continue

            for ext in IMAGE_EXTENSIONS:
                image_paths.extend(folder.rglob(f"*{ext}"))

        return sorted(image_paths)

    def _analyze_and_store_image(self, image_path: Path) -> None:
        """Analyze single image with MLX VLM and store metadata."""
        # 1. Format prompt with chat template
        formatted_prompt = apply_chat_template(
            self._mlx_processor,
            self._mlx_config,
            ASSET_ANALYSIS_PROMPT,
            num_images=1,
        )

        # 2. Generate analysis using MLX VLM Python API
        result = generate(
            self._mlx_model,
            self._mlx_processor,
            formatted_prompt,
            image=[str(image_path)],  # Pass image path directly
            verbose=False,
            max_tokens=512,
            temp=0.3,
        )

        # Extract text from GenerationResult
        # Try direct attribute access first, fallback to string conversion
        if hasattr(result, 'text'):
            output = result.text
        elif hasattr(result, 'content'):
            output = result.content
        else:
            # Last resort: convert to string and try to extract
            result_str = str(result)
            # If it's a GenerationResult repr, extract the text value
            if 'GenerationResult(text=' in result_str:
                import re
                match = re.search(r"text='(.*?)'(?:,|\))", result_str, re.DOTALL)
                output = match.group(1) if match else result_str
            else:
                output = result_str

        # 3. Parse JSON from response (may be wrapped in markdown code blocks)
        metadata = self._extract_json(output)

        # 4. Store in memory backend with source path
        if self._memory_backend and metadata:
            storage_content = json.dumps(metadata, indent=2)
            self._memory_backend.store(
                content=storage_content,
                source=str(image_path),
                metadata={"file_name": image_path.name, "folder": image_path.parent.name},
            )
            logger.debug(f"Stored metadata for {image_path.name}")

    def _extract_json(self, content: str) -> Dict[str, Any]:
        """Extract JSON from LLM response, handling markdown code blocks."""
        content = content.strip()

        # Remove markdown code fences if present
        if content.startswith("```"):
            lines = content.split("\n")
            # Remove first line (```json or ```) and last line (```)
            content = "\n".join(lines[1:-1]) if len(lines) > 2 else content

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON from response: {content[:200]}")
            return {}


__all__ = ["AssetIntelligenceOperative"]
