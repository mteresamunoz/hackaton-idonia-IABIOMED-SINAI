"""
Multimodal LLM Client — Hackathon IABiomed 2026 — SINAI-UJA

Client for the multimodal model (gemma-4-31B-it) in charge of:
  1. Describing medical images objectively and literally.

Connects to the same OpenAI-compatible endpoint as the error agent
and the multilingual translator, but specializes in vision tasks.
"""

import base64
from pathlib import Path
from typing import Optional

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

from utils.config import load_config


def _get_multimodal_client() -> Optional[OpenAI]:
    if OpenAI is None:
        return None
    cfg = load_config()
    return OpenAI(api_key=cfg.openai_api_key, base_url=cfg.openai_base_url)


class MultimodalClient:
    """
    Client for medical vision tasks using an OpenAI-compatible multimodal LLM.
    """

    def __init__(self, api_key: str, base_url: str, model_name: str):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model_name = model_name

    def describe_medical_image(self, image_path: str | Path, logger=None) -> str:
        """
        Generates an objective description of a medical image using the configured
        multimodal model (gemma-4-31B-it by default).

        Args:
            image_path: Local path to the image (PNG, JPEG, etc.).
            logger: Optional logger to record progress.

        Returns:
            Textual description of the image. Empty string if it fails.
        """
        image_path = Path(image_path)
        if not image_path.exists():
            if logger:
                logger.warning("Imagen no encontrada: %s", image_path)
            return ""

        # Encode image in base64
        image_bytes = image_path.read_bytes()
        b64_image = base64.b64encode(image_bytes).decode("utf-8")

        # Detect MIME type by extension
        suffix = image_path.suffix.lower()
        mime = "image/png" if suffix == ".png" else "image/jpeg"

        system_prompt = (
            "Eres un asistente radiológico experto. Tu única tarea es describir "
            "imágenes médicas de forma objetiva y literal. NUNCA inventes hallazgos, "
            "diagnósticos, medidas ni conclusiones que no puedas ver directamente "
            "en la imagen. Si no estás seguro de algo, indícalo explícitamente. "
            "Describe anatomía visible, contraste, planos de corte y cualquier "
            "observable evidente. No añadas recomendaciones clínicas."
        )

        user_prompt = (
            "Describe detalladamente esta imagen médica. Indica qué tipo de prueba "
            "parece ser (RM, TC, radiografía, etc.), las estructuras anatómicas "
            "visibles y cualquier observable objetivo. NO inventes información ni "
            "des diagnósticos."
        )

        if logger:
            logger.info(
                "Enviando imagen %s al modelo multimodal (%s)...",
                image_path.name,
                self.model_name,
            )

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime};base64,{b64_image}"
                                },
                            },
                        ],
                    },
                ],
                temperature=0.1,
                max_tokens=2048,
            )
        except Exception as exc:
            if logger:
                logger.warning(
                    "El modelo multimodal no pudo describir la imagen: %s", exc
                )
            return ""

        msg = response.choices[0].message
        description = msg.content or ""
        if not description:
            description = getattr(msg, "reasoning", "") or ""

        usage = getattr(response, "usage", None)
        if logger and usage:
            logger.info(
                "   Tokens usados (descripción imagen): prompt=%s, completion=%s",
                getattr(usage, "prompt_tokens", "?"),
                getattr(usage, "completion_tokens", "?"),
            )

        return description.strip()


def create_multimodal_client() -> MultimodalClient:
    cfg = load_config()
    return MultimodalClient(
        api_key=cfg.openai_api_key,
        base_url=cfg.openai_base_url,
        model_name=cfg.multilingual_model_name,
    )
