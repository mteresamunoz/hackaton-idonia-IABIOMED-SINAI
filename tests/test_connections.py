"""
test_connections.py — Hackathon IABiomed 2026 — SINAI-UJA

Run this BEFORE the main pipeline to verify everything is wired up correctly:
  1. JWT generation works
  2. Idonia /whoami responds
  3. Recog endpoint responds (with a tiny test payload)
  4. Informe RM RODILLA.pdf exists in documentacion/

Usage:
    python tests/test_connections.py
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "background" / "src"))

from utils.config import load_config
from clients.idonia_client import generate_jwt
from utils.logging_config import get_logger
from utils.helpers import create_idonia_client, create_recog_client

parser = argparse.ArgumentParser(description="Test de conexiones — SINAI-UJA")
parser.add_argument("--log-dir", type=str, default=None,
                    help="Carpeta donde guardar los logs de este test.")
args, _ = parser.parse_known_args()

logger = get_logger("test_connections", log_dir=args.log_dir)


def check(label: str, fn):
    try:
        result = fn()
        logger.info("[OK] %s", label)
        if result:
            logger.info("    -> %s", result)
        return True
    except Exception as e:
        logger.error("[ERROR] %s", label)
        logger.error("    Error: %s", e)
        return False


def main():
    logger.info("")
    logger.info("Test de conexiones — SINAI-UJA Hackathon")
    logger.info("=" * 50)

    try:
        cfg = load_config()
    except EnvironmentError as e:
        logger.error("Config error: %s", e)
        sys.exit(1)

    idonia = create_idonia_client(cfg)
    recog = create_recog_client(cfg)

    results = []

    logger.info("")
    logger.info("[1] JWT Generation")
    results.append(check(
        "Generar JWT para Idonia",
        lambda: generate_jwt(cfg.idonia_api_key, cfg.idonia_api_secret)[:40] + "...",
    ))

    logger.info("")
    logger.info("[2] Idonia API")
    results.append(check(
        "GET /whoami → Idonia Connect Cloud",
        lambda: idonia.whoami(),
    ))

    logger.info("")
    logger.info("[3] Recog API")
    results.append(check(
        "POST /report-results → Recog (informe de prueba)",
        lambda: f"{len(recog.humanize_report('Paciente con dolor de rodilla. Sin hallazgos graves.'))} bytes PDF",
    ))

    logger.info("")
    logger.info("[4] PDF del informe")
    pdf_path = Path(__file__).parent.parent / "background" / "Informes" / "Informe RM RODILLA.pdf"
    results.append(check(
        "Informe_RM_RODILLA.pdf encontrado en Informes/",
        lambda: str(pdf_path) if pdf_path.exists() else (_ for _ in ()).throw(
            FileNotFoundError(f"No encontrado en {pdf_path}")
        ),
    ))

    logger.info("")
    logger.info("[5] Imagen del estudio")
    img_path = Path(__file__).parent.parent / "background" / "Informes" / "RM Rodilla.png"
    results.append(check(
        "RM_Rodilla.png encontrado en Informes/",
        lambda: str(img_path) if img_path.exists() else (_ for _ in ()).throw(
            FileNotFoundError(f"No encontrado en {img_path}")
        ),
    ))

    logger.info("")
    logger.info("=" * 50)
    passed = sum(results)
    total = len(results)
    logger.info("Resultado: %s/%s checks pasados", passed, total)

    if passed == total:
        logger.info("[OK] Todo listo para ejecutar el pipeline.")
        logger.info("Ejecuta: python src/pipeline.py --phase 1")
    else:
        logger.warning("AVISO: Hay checks fallidos. Revisa los errores antes de continuar.")

    logger.info("")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
