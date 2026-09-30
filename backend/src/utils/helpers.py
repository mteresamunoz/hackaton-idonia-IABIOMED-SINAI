"""
Helpers module for client factories and shared utilities.
Hackathon IABiomed 2026 — Team SINAI-UJA
"""

from pathlib import Path
from clients.idonia_client import IdoniaClient
from clients.recog_client import RecogClient
from clients.multilingual_client import MultilingualClient
from clients.multimodal_client import MultimodalClient
from utils.config import Config


def is_image_file(path: Path) -> bool:
    """Checks if a file path points to an image or DICOM file."""
    return path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".dcm"}


def create_idonia_client(cfg: Config) -> IdoniaClient:
    """Creates an IdoniaClient instance from the Config object."""
    return IdoniaClient(
        api_key=cfg.idonia_api_key,
        api_secret=cfg.idonia_api_secret,
        num_participante=cfg.idonia_num_participante,
        base_url=cfg.idonia_base_url,
    )


def create_recog_client(cfg: Config) -> RecogClient:
    """Creates a RecogClient instance from the Config object."""
    return RecogClient(
        api_key=cfg.recog_api_key,
        base_url=cfg.recog_base_url,
        endpoint=cfg.recog_endpoint,
    )


def create_multilingual_client(cfg: Config) -> MultilingualClient:
    """Creates a MultilingualClient instance from the Config object."""
    return MultilingualClient(
        api_key=cfg.openai_api_key,
        base_url=cfg.openai_base_url,
        model_name=cfg.multilingual_model_name,
    )


def create_multimodal_client(cfg: Config) -> MultimodalClient:
    """Creates a MultimodalClient instance from the Config object."""
    return MultimodalClient(
        api_key=cfg.openai_api_key,
        base_url=cfg.openai_base_url,
        model_name=cfg.multilingual_model_name,
    )
