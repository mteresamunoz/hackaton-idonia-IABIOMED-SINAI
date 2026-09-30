"""
Prueba rápida de conectividad con el LLM local.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "src"))

from utils.config import load_config
from utils.logging_config import get_logger

try:
    from openai import OpenAI
except ImportError:
    print("❌ openai no instalado. Ejecuta: pip install openai")
    sys.exit(1)

parser = argparse.ArgumentParser(description="Test LLM local — SINAI-UJA")
parser.add_argument("--log-dir", type=str, default=None,
                    help="Carpeta donde guardar los logs de este test.")
args, _ = parser.parse_known_args()

logger = get_logger("test_llm", log_dir=args.log_dir)

cfg = load_config()
client = OpenAI(api_key=cfg.openai_api_key, base_url=cfg.openai_base_url)

logger.info("URL base : %s", cfg.openai_base_url)
logger.info("Agente   : %s", cfg.agent_model_name)
logger.info("Multilingüe : %s", cfg.multilingual_model_name)

# ── Test 1: Modelo agente (Qwen) ─────────────────────────────────────────────
logger.info("")
logger.info("[1] Test modelo AGENTE (%s)", cfg.agent_model_name)
try:
    response = client.chat.completions.create(
        model=cfg.agent_model_name,
        messages=[
            {"role": "system", "content": "Eres un asistente útil."},
            {"role": "user", "content": "Di hola en español y nada más."},
        ],
        temperature=0.1,
        max_tokens=8192,
    )
    logger.info("✅ Respuesta recibida:")
    choice = response.choices[0]
    msg = choice.message
    logger.info("   Finish reason: %s", choice.finish_reason)
    logger.info("   Prompt tokens: %s", getattr(response.usage, 'prompt_tokens', 'N/A'))
    logger.info("   Completion tokens: %s", getattr(response.usage, 'completion_tokens', 'N/A'))

    text = msg.content or getattr(msg, "reasoning", "") or ""
    logger.info("--- Texto extraído ---")
    logger.info(text)

    if not text:
        logger.warning("--- raw response dump (primeros 2000 chars) ---")
        logger.warning(response.model_dump_json(indent=2)[:2000])
except Exception as e:
    logger.error("❌ Error llamando al LLM agente: %s", e)

# ── Test 2: Modelo multilingüe (gemma) ───────────────────────────────────────
logger.info("")
logger.info("[2] Test modelo MULTILINGÜE (%s)", cfg.multilingual_model_name)
try:
    response = client.chat.completions.create(
        model=cfg.multilingual_model_name,
        messages=[
            {"role": "system", "content": "Eres un traductor médico experto."},
            {"role": "user", "content": "Traduce 'Paciente con dolor de rodilla' al catalán y nada más."},
        ],
        temperature=0.2,
        max_tokens=4096,
    )
    logger.info("✅ Respuesta recibida:")
    choice = response.choices[0]
    msg = choice.message
    logger.info("   Finish reason: %s", choice.finish_reason)
    logger.info("   Prompt tokens: %s", getattr(response.usage, 'prompt_tokens', 'N/A'))
    logger.info("   Completion tokens: %s", getattr(response.usage, 'completion_tokens', 'N/A'))

    text = msg.content or getattr(msg, "reasoning", "") or ""
    logger.info("--- Texto extraído ---")
    logger.info(text)

    if not text:
        logger.warning("--- raw response dump (primeros 2000 chars) ---")
        logger.warning(response.model_dump_json(indent=2)[:2000])
except Exception as e:
    logger.error("❌ Error llamando al LLM multilingüe: %s", e)
