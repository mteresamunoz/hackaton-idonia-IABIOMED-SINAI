"""
Test de integración multilingüe — Hackathon IABiomed 2026 — SINAI-UJA

Verifica:
  1. Conectividad con el LLM multilingüe (gemma-4-31B-it).
  2. Capacidad básica de traducción médica.
  3. Compilación LaTeX a PDF (pdflatex/xelatex).

Usage:
    python tests/test_multilingual.py
    python tests/test_multilingual.py --log-dir logs/04_tests
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "background" / "src"))

from utils.config import load_config
from utils.latex_compiler import compile_latex, _find_latex_compiler
from utils.logging_config import get_logger
from clients.multilingual_client import MultilingualClient, SUPPORTED_LANGUAGES

try:
    from openai import OpenAI
except ImportError:
    print("❌ openai no instalado. Ejecuta: pip install openai")
    sys.exit(1)

parser = argparse.ArgumentParser(description="Test multilingüe — SINAI-UJA")
parser.add_argument("--log-dir", type=str, default=None,
                    help="Carpeta donde guardar los logs de este test.")
args, _ = parser.parse_known_args()

logger = get_logger("test_multilingual", log_dir=args.log_dir)


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
    logger.info("Test multilingüe — SINAI-UJA Hackathon")
    logger.info("=" * 50)

    try:
        cfg = load_config()
    except EnvironmentError as e:
        logger.error("Config error: %s", e)
        sys.exit(1)

    logger.info("URL base    : %s", cfg.openai_base_url)
    logger.info("Modelo mult.: %s", cfg.multilingual_model_name)

    results = []

    # ── 1. Conectividad LLM multilingüe ──────────────────────────────────────
    logger.info("")
    logger.info("[1] Conectividad LLM multilingüe")
    multilingual = MultilingualClient(
        api_key=cfg.openai_api_key,
        base_url=cfg.openai_base_url,
        model_name=cfg.multilingual_model_name,
    )
    results.append(check(
        "LLM multilingüe responde",
        lambda: multilingual.translate_latex(
            latex_template="\\documentclass{article}\\begin{document}Test\\end{document}",
            source_text="Paciente con dolor de rodilla. Sin hallazgos graves.",
            target_lang="ca",
            logger=logger,
        )[:80] + "...",
    ))

    # ── 2. Compilador LaTeX disponible ───────────────────────────────────────
    logger.info("")
    logger.info("[2] Compilador LaTeX")
    compiler_path = cfg.latex_compiler_path
    if compiler_path:
        logger.info("   Ruta configurada: %s", compiler_path)
    compiler = _find_latex_compiler(compiler_path=compiler_path)
    results.append(check(
        "pdflatex/xelatex disponible",
        lambda: compiler or (_ for _ in ()).throw(RuntimeError("No se encontró compilador LaTeX")),
    ))

    # ── 3. Compilación LaTeX mínima ──────────────────────────────────────────
    logger.info("")
    logger.info("[3] Compilación LaTeX a PDF")
    if compiler:
        mini_latex = (
            "\\documentclass[11pt,a4paper]{article}\n"
            "\\usepackage[utf8]{inputenc}\n"
            "\\begin{document}\n"
            "Informe de prueba multilingüe.\n"
            "\\end{document}\n"
        )
        output_pdf = Path(__file__).parent.parent / "output" / "test_multilingual.pdf"
        try:
            compile_latex(
                mini_latex,
                output_pdf=output_pdf,
                compiler_path=compiler_path,
                clean_aux=True,
            )
            logger.info("[OK] PDF compilado correctamente: %s (%s bytes)", output_pdf, output_pdf.stat().st_size)
            results.append(True)
        except Exception as e:
            logger.error("[ERROR] Compilación LaTeX fallida: %s", e)
            results.append(False)
    else:
        logger.warning("[SKIP] No hay compilador LaTeX, se omite test de compilación.")
        results.append(False)

    # ── 4. Idiomas soportados ────────────────────────────────────────────────
    logger.info("")
    logger.info("[4] Idiomas soportados")
    for code, name in SUPPORTED_LANGUAGES.items():
        logger.info("    %s -> %s", code, name)
    results.append(True)

    # ── Resumen ──────────────────────────────────────────────────────────────
    logger.info("")
    logger.info("=" * 50)
    passed = sum(results)
    total = len(results)
    logger.info("Resultado: %s/%s checks pasados", passed, total)

    if passed == total:
        logger.info("[OK] Todo listo para ejecutar el pipeline multilingüe.")
    else:
        logger.warning("AVISO: Hay checks fallidos. Revisa los errores antes de continuar.")

    logger.info("")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
