"""
Error handling agent — Hackathon IABiomed 2026 — SINAI-UJA
Manages errors from external APIs (Idonia, Recog) that can occur
to the end user: timeouts, 404, 401, 503, network errors, etc.

The agent:
  1. Detects if the error is temporary (retries with automatic backoff).
  2. If it persists, queries the local LLM to generate a user-friendly message.
  3. Suggests concrete actions to the user.
  4. Saves technical logs for support.
"""

import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

from utils.config import load_config
from utils.logging_config import get_logger

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None


def _get_llm_client() -> Optional[OpenAI]:
    if OpenAI is None:
        return None
    cfg = load_config()
    return OpenAI(api_key=cfg.openai_api_key, base_url=cfg.openai_base_url)


def _is_retryable_error(exc: Exception) -> bool:
    """Determines if an error is temporary and deserves a retry."""
    if isinstance(exc, requests.exceptions.Timeout):
        return True
    if isinstance(exc, requests.exceptions.ConnectionError):
        return True
    if isinstance(exc, requests.exceptions.HTTPError):
        try:
            status = exc.response.status_code
            return status in (429, 500, 502, 503, 504)
        except Exception:
            return False
    return False


def _retry_with_backoff(phase_func, phase_args, log_dir=None, max_retries: int = 3, base_delay: float = 2.0):
    """
    Retries a phase with exponential backoff for temporary errors.
    Returns (success: bool, result).
    """
    logger = get_logger("agente_errores", log_dir=log_dir)
    last_exc = None
    for attempt in range(1, max_retries + 1):
        try:
            return True, phase_func(*phase_args)
        except Exception as exc:
            last_exc = exc
            if not _is_retryable_error(exc) or attempt == max_retries:
                return False, exc
            delay = base_delay * (2 ** (attempt - 1))
            logger.info("⏳ Error temporal detectado. Reintentando en %.0fs... (intento %d/%d)", delay, attempt, max_retries)
            time.sleep(delay)
    return False, last_exc


def handle_error(
    exception: Exception,
    phase_name: str = "",
    extra_context: str = "",
    auto_fix: bool = False,
    log_dir: str | Path | None = None,
    language: str = "es",
) -> dict:
    """
    Captures an API/network error, attempts retries if temporary,
    and queries the LLM to generate a user-friendly message for the user.

    Returns dict with:
      user_message, technical_analysis, suggested_actions, retry_success.
    """
    logger = get_logger("agente_errores", log_dir=log_dir)
    tb_str = traceback.format_exc()
    cfg = load_config()
    client = _get_llm_client()

    # Fallback if there is no LLM
    if client is None:
        msg = (
            f"Error en '{phase_name}': {exception}\n\n"
            f"   El módulo 'openai' no está instalado. Ejecuta: pip install openai"
        )
        logger.error(msg)
        return {
            "user_message": msg,
            "technical_analysis": tb_str,
            "suggested_actions": ["pip install openai"],
            "retry_success": False,
        }

    # Configure prompt language according to the user
    lang_instruction = {
        "es": "Responde SIEMPRE en español.",
        "ca": "Respon SEMPRE en català.",
        "va": "Respon SEMPRE en valencià.",
        "gl": "Responde SEMPRE en galego.",
        "eu": "Erantzun BETI euskaraz.",
    }.get(language, "Responde SIEMPRE en español.")

    system_prompt = (
        "Eres un asistente de soporte experto en APIs REST y sistemas médicos. "
        "Tu trabajo es analizar errores técnicos y explicárselos de forma clara y "
        "tranquila a un usuario que NO es informático. " + lang_instruction
    )

    # Detect error type and HTTP status if applicable
    error_type = type(exception).__name__
    http_status = ""
    endpoint_hint = ""
    if isinstance(exception, requests.exceptions.HTTPError):
        try:
            http_status = str(exception.response.status_code)
            endpoint_hint = exception.request.url if exception.request else ""
        except Exception:
            pass

    user_prompt = (
        f"FASE: {phase_name or 'desconocida'}\n"
        f"TIPO DE ERROR: {error_type}\n"
        f"CÓDIGO HTTP: {http_status or 'N/A'}\n"
        f"ENDPOINT: {endpoint_hint or 'N/A'}\n"
        f"MENSAJE: {exception}\n\n"
        f"TRACEBACK:\n{tb_str}\n\n"
        "Responde EXACTAMENTE con este formato (mantén los delimitadores):\n\n"
        "---USER_MESSAGE---\n"
        "Mensaje amigable para un usuario NO experto (máx 5 frases). Explica qué pasó, por qué es importante y qué puede hacer el usuario para solucionarlo. Usa tono profesional pero cercano.\n\n"
        "---TECHNICAL_ANALYSIS---\n"
        "Análisis técnico conciso para el equipo de soporte.\n\n"
        "---SUGGESTED_ACTIONS---\n"
        "1. Primera acción concreta que puede tomar el usuario\n"
        "2. Segunda acción\n"
        "3. Tercera acción\n"
        "4. Si aplica: cuándo contactar con soporte técnico"
    )

    # Call to LLM
    logger.info("Agente LLM analizando el error...")
    raw = ""
    try:
        response = client.chat.completions.create(
            model=cfg.agent_model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=4096,
        )
        msg = response.choices[0].message
        raw = msg.content or ""
        if not raw:
            raw = getattr(msg, "reasoning", "") or ""
        usage = getattr(response, "usage", None)
        if usage:
            logger.info("   Tokens usados: prompt=%s, completion=%s",
                        getattr(usage, 'prompt_tokens', '?'),
                        getattr(usage, 'completion_tokens', '?'))
    except Exception as llm_err:
        logger.warning("⚠️  El agente LLM no pudo analizar el error: %s", llm_err)
        return {
            "user_message": f"Error en {phase_name}: {exception}",
            "technical_analysis": tb_str,
            "suggested_actions": ["Revisar logs en logs/"],
            "retry_success": False,
        }

    # Save raw response with a unique name (timestamp) to avoid overwriting
    target_dir = Path(log_dir) if log_dir else Path(__file__).parent.parent.parent / "output"
    target_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    debug_path = target_dir / f"llm_diagnostico_{timestamp}.txt"
    debug_path.write_text(raw or "(respuesta vacía)", encoding="utf-8")
    logger.info("[OK] Diagnóstico del LLM guardado en: %s", debug_path)

    #  Parsing the response
    result = {
        "user_message": "",
        "technical_analysis": "",
        "suggested_actions": [],
        "retry_success": False,
    }

    if not raw:
        result["user_message"] = (
            "❌ El agente LLM no ha devuelto una respuesta válida. "
            "Esto puede deberse a una sobrecarga temporal del modelo. "
            "Por favor, inténtalo de nuevo en unos segundos."
        )
        result["technical_analysis"] = tb_str
        result["suggested_actions"] = [
            "Reintentar la operación",
            f"Verificar conectividad con el servidor de IA ({cfg.openai_base_url})",
        ]
        logger.error(result["user_message"])
        return result

    # Parse sections
    sections = [
        ("user_message", "---USER_MESSAGE---"),
        ("technical_analysis", "---TECHNICAL_ANALYSIS---"),
        ("suggested_actions", "---SUGGESTED_ACTIONS---"),
    ]

    for idx, (key, delim) in enumerate(sections):
        if delim not in raw:
            continue
        _, after = raw.split(delim, 1)
        end = len(after)
        for _, next_delim in sections[idx + 1 :]:
            pos = after.find(next_delim)
            if pos != -1 and pos < end:
                end = pos
        value = after[:end].strip()
        result[key] = value

    # Fallback
    if not result["user_message"]:
        result["user_message"] = "❌ El agente no ha podido analizar correctamente el error. Revisa los logs."
        result["technical_analysis"] = tb_str

    # Normalize actions
    if result["suggested_actions"]:
        if isinstance(result["suggested_actions"], str):
            result["suggested_actions"] = [
                line.strip(" -•1234567890.")
                for line in result["suggested_actions"].splitlines()
                if line.strip()
            ]

    # Show summary (also recorded in the log)
    logger.info("=" * 60)
    logger.info(result["user_message"])
    logger.info("=" * 60)
    logger.info("🔍  Análisis técnico:\n%s", result["technical_analysis"])
    if result["suggested_actions"]:
        for i, act in enumerate(result["suggested_actions"], 1):
            logger.info("   %d. %s", i, act)

    return result
