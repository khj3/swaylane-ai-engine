import os
import json
import uuid
import time
import logging
import httpx
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

HUNYUAN_API_KEY = os.getenv("HUNYUAN_API_KEY", "")
MODDDIF_API_KEY = os.getenv("MODDDIF_API_KEY", "")
TOP3D_API_KEY = os.getenv("TOP3D_API_KEY", "")

HUNYUAN_BASE = "https://3d.hunyuan.tencent.com/api/v1"
MODDDIF_BASE = "https://api.modddif.com/v1"


class ThreeDService:
    """Adapter for 3D AI generation tools.
    
    Tools supported:
    - Hunyuan3D: image-to-3D and text-to-3D model generation
    - Modddif: fabric/texture enhancement and normal maps
    - Top3D Arena: benchmark/comparison (manual workflow, no API)
    """

    @staticmethod
    def is_configured(tool: str = "hunyuan") -> bool:
        if tool == "hunyuan":
            return bool(HUNYUAN_API_KEY)
        if tool == "modddif":
            return bool(MODDDIF_API_KEY)
        if tool == "top3d":
            return bool(TOP3D_API_KEY)
        return False

    @staticmethod
    async def generate_hunyuan_3d(
        image_url: str = None,
        prompt: str = None,
        asset_type: str = "model",
        webhook_url: str = None,
    ) -> Tuple[Optional[str], Optional[str], Optional[dict]]:
        """Generate a 3D model from an image or text prompt using Hunyuan3D.
        
        Returns: (task_id, status, result_data)
        """
        if not HUNYUAN_API_KEY:
            return None, "not_configured", {"error": "Hunyuan API key not set"}

        payload = {
            "asset_type": asset_type,
        }
        if image_url:
            payload["input_image"] = image_url
            payload["mode"] = "image_to_3d"
        elif prompt:
            payload["prompt"] = prompt
            payload["mode"] = "text_to_3d"
        else:
            return None, "failed", {"error": "Provide image_url or prompt"}

        if webhook_url:
            payload["webhook"] = webhook_url

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{HUNYUAN_BASE}/generations",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {HUNYUAN_API_KEY}",
                        "Content-Type": "application/json",
                    },
                )
                if resp.status_code >= 400:
                    logger.error("Hunyuan API error: %s %s", resp.status_code, resp.text)
                    return None, "failed", {"error": resp.text}
                data = resp.json()
                task_id = data.get("id") or data.get("task_id")
                return task_id, "processing", data
        except Exception as e:
            logger.error("Hunyuan request failed: %s", e)
            return None, "failed", {"error": str(e)}

    @staticmethod
    async def check_hunyuan_status(task_id: str) -> Optional[dict]:
        if not HUNYUAN_API_KEY:
            return None
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"{HUNYUAN_BASE}/generations/{task_id}",
                    headers={"Authorization": f"Bearer {HUNYUAN_API_KEY}"},
                )
                if resp.status_code >= 400:
                    return None
                return resp.json()
        except Exception as e:
            logger.error("Hunyuan status check failed: %s", e)
            return None

    @staticmethod
    async def enhance_texture_modddif(
        image_url: str,
        enhancement_type: str = "texture",
        fabric_type: str = None,
    ) -> Tuple[Optional[str], Optional[str], Optional[dict]]:
        """Enhance fabric texture or generate normal maps via Modddif.
        
        enhancement_type: 'texture', 'normal_map', 'geometry', 'stitching'
        """
        if not MODDDIF_API_KEY:
            return None, "not_configured", {"error": "Modddif API key not set"}

        payload = {
            "input_image": image_url,
            "enhancement_type": enhancement_type,
        }
        if fabric_type:
            payload["fabric_type"] = fabric_type

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{MODDDIF_BASE}/enhance",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {MODDDIF_API_KEY}",
                        "Content-Type": "application/json",
                    },
                )
                if resp.status_code >= 400:
                    logger.error("Modddif API error: %s %s", resp.status_code, resp.text)
                    return None, "failed", {"error": resp.text}
                data = resp.json()
                task_id = data.get("id") or data.get("task_id")
                return task_id, "processing", data
        except Exception as e:
            logger.error("Modddif request failed: %s", e)
            return None, "failed", {"error": str(e)}

    @staticmethod
    async def check_modddif_status(task_id: str) -> Optional[dict]:
        if not MODDDIF_API_KEY:
            return None
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"{MODDDIF_BASE}/enhancements/{task_id}",
                    headers={"Authorization": f"Bearer {MODDDIF_API_KEY}"},
                )
                if resp.status_code >= 400:
                    return None
                return resp.json()
        except Exception as e:
            logger.error("Modddif status check failed: %s", e)
            return None

    @staticmethod
    def top3d_benchmark_url(product_type: str = "clothing") -> str:
        """Get Top3D AI Arena benchmark URL for comparing 3D tools.
        Used as a reference resource - manual workflow."""
        base = "https://top3d.ai/arena"
        categories = {
            "clothing": "?category=clothing",
            "fashion": "?category=fashion",
            "textiles": "?category=textiles",
        }
        return base + categories.get(product_type, "")


# Convenience exports
three_d_service = ThreeDService()
