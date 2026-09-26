"""Multimodal Vision Judge for MIRA-Web.

Uses Gemini Vision (gemini-3.8-flash) to evaluate whether visual evidence
in a screenshot supports or contradicts a claimed UI status or action response.
Includes resilient fallback when API is unavailable or rate-limited.
"""

from __future__ import annotations
import io
import json
import logging
import os
import re
from typing import Any, Dict, Optional
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

logger = logging.getLogger("mira.vision_judge")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

_CLIENT_INITIALIZED = False


def _init_gemini() -> bool:
    global _CLIENT_INITIALIZED
    if _CLIENT_INITIALIZED:
        return True

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY not found in environment.")
        return False

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        _CLIENT_INITIALIZED = True
        return True
    except Exception as e:
        logger.warning("Failed to configure Gemini client: %s", e)
        return False


def judge(
    screenshot_bytes: bytes,
    context: Dict[str, Any],
    model_name: str = "gemini-3.8-flash",
) -> Dict[str, Any]:
    """Inspect visual evidence against claimed state.

    Args:
        screenshot_bytes: PNG or JPEG image bytes of the UI region or page.
        context: Generic dictionary containing:
            - "region_description": str
            - "claimed_state": str
            - "observed_change": str

    Returns:
        dict: {
            "verdict": "supported" | "contradicted" | "ambiguous" | "needs_review",
            "reasoning": str,
            "confidence": float
        }
    """
    region_description = context.get("region_description", "UI region")
    claimed_state = context.get("claimed_state", "unspecified")
    observed_change = context.get("observed_change", "unspecified")

    # Fallback response structure
    fallback_result = {
        "verdict": "needs_review",
        "reasoning": "Vision API unavailable or query failed; manual review suggested.",
        "confidence": 0.5,
    }

    if not _init_gemini():
        return fallback_result

    prompt = f"""You are an autonomous UI testing judge evaluating visual ground truth.
A UI element or region has been inspected:
- Region Description: {region_description}
- Claimed State / Text: "{claimed_state}"
- Observed Physical Behavior: "{observed_change}"

Analyze the provided image alongside the context.
Does the visible evidence support or contradict the claimed state?

You must respond ONLY with a valid JSON object in this exact schema:
{{
    "verdict": "supported" | "contradicted" | "ambiguous",
    "reasoning": "Concise 1-2 sentence explanation of why visual evidence supports or contradicts the claim",
    "confidence": 0.95
}}
"""

    try:
        import google.generativeai as genai
        img = Image.open(io.BytesIO(screenshot_bytes))

        model = genai.GenerativeModel(model_name)
        response = model.generate_content([prompt, img])
        raw_text = response.text.strip()

        # Parse JSON from response
        # Strip potential markdown code block backticks
        json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            verdict = str(data.get("verdict", "")).lower().strip()
            if verdict not in ("supported", "contradicted", "ambiguous"):
                verdict = "ambiguous"
            reasoning = str(data.get("reasoning", "")).strip()
            confidence = float(data.get("confidence", 0.8))
            return {
                "verdict": verdict,
                "reasoning": reasoning,
                "confidence": confidence,
            }
        else:
            logger.warning("Could not parse JSON from Gemini response: %s", raw_text)
            return {
                "verdict": "ambiguous",
                "reasoning": raw_text[:200],
                "confidence": 0.6,
            }

    except Exception as e:
        logger.warning("Error during vision judge evaluation: %s", e)
        fallback_result["reasoning"] = f"Vision judge API error: {str(e)[:150]}"
        return fallback_result


if __name__ == "__main__":
    # Test with synthetic image
    img = Image.new("RGB", (200, 60), color="red")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    test_bytes = buf.getvalue()

    ctx = {
        "region_description": "status indicator badge",
        "claimed_state": "System is healthy and green",
        "observed_change": "Badge is solid red with no updates",
    }
    result = judge(test_bytes, ctx)
    print("Verdict:", result)
