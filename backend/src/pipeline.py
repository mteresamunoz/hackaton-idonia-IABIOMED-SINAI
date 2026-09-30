"""
Main pipeline — Hackathon IABiomed 2026 — SINAI-UJA
Challenge: Interoperability and humanization of medical information

Phase I   — Ingestion:   upload PDF report to Idonia
Phase II  — Humanization: call Recog + upload report for patient to Idonia
Phase III — Magic Link:   generate QR+PIN link for patient and doctor

Usage:
    python src/pipeline.py                     # executes all 3 phases
    python src/pipeline.py --phase 1
    python src/pipeline.py --phase 2
    python src/pipeline.py --phase 3
    python src/pipeline.py --auto-fix          # activates retries + LLM diagnosis
    python src/pipeline.py --simulate-error 1  # forces Idonia timeout
"""

import argparse
import sys
import traceback
from pathlib import Path

from utils.config import load_config
from utils.handle_errors import handle_error
from utils.latex_compiler import compile_latex
from utils.logging_config import get_logger
from clients.idonia_client import IdoniaClient
from clients.recog_client import RecogClient
from clients.multilingual_client import MultilingualClient, SUPPORTED_LANGUAGES
from clients.multimodal_client import MultimodalClient
from utils.anonymizer import build_anonymizer_from_config
from utils.helpers import (
    is_image_file,
    create_idonia_client,
    create_recog_client,
    create_multilingual_client,
    create_multimodal_client
)


# File Paths

DOCS_DIR   = Path(__file__).parent.parent / "Informes"
OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

RM_REPORT_PDF = DOCS_DIR / "Informe RM RODILLA.pdf"
RM_IMAGE_PNG  = DOCS_DIR / "RM Rodilla.png"
HUMANIZED_PDF = OUTPUT_DIR / "Informe para paciente.pdf"

# Original upload names coming from the client/UI.
RM_REPORT_UPLOAD_NAME: str | None = None
RM_IMAGE_UPLOAD_NAME: str | None = None

# Path of the report to process (PDF or image); can be overwritten with --report-path
REPORT_PATH = RM_REPORT_PDF

# Global variable for custom logs folder (set in main)
_LOG_DIR: Path | None = None




# Phase I  

def phase_1_ingest(idonia: IdoniaClient, cfg, simulate_error: int | None = None) -> bool:
    """
    Simulates reception from Cantabria.
    - Verifies JWT with /whoami
    - Uploads Informe_RM_RODILLA.pdf to Idonia
      Endpoint: POST /files/report_hak_<num_participante>
      Route:    <DICOMPatientID>/<DICOMAccessionNumber>/<DICOMStudyDescription>
    """
    if simulate_error == 1:
        import requests
        # Simulate network timeout: Idonia does not respond
        raise requests.exceptions.ConnectTimeout(
            "HTTPSConnectionPool(host='connect-staging.idonia.com', port=443): "
            "Max retries exceeded with url: /whoami"
        )
    if simulate_error == 2:
        import requests
        # Simulate invalid credentials
        resp = requests.Response()
        resp.status_code = 401
        resp._content = b'{"error": "Unauthorized"}'
        raise requests.exceptions.HTTPError("401 Client Error: Unauthorized", response=resp)
    if simulate_error == 3:
        import requests
        # Simulate service unavailable
        resp = requests.Response()
        resp.status_code = 503
        resp._content = b'{"error": "Service Unavailable"}'
        raise requests.exceptions.HTTPError("503 Server Error: Service Unavailable", response=resp)

    logger = get_logger("pipeline.fase1", log_dir=_LOG_DIR)
    logger.info("=" * 55)
    logger.info("FASE I — Ingesta (Interoperabilidad)")
    logger.info("=" * 55)

    logger.info("Verificando autenticación con /whoami...")
    identity = idonia.whoami()
    logger.info("OK Autenticado: %s", identity.get('actorId', identity))

    logger.info("\n")
    logger.info("Subiendo informe médico y/o imagen de estudio a Idonia...")
    endpoint = f"/files/report_hak_{cfg.idonia_num_participante}"
    logger.info("  Endpoint : %s", endpoint)
    logger.info("  PatientID: %s", cfg.dicom_patient_id)
    logger.info("  Accession: %s", cfg.dicom_accession_num)
    logger.info("  StudyDesc: %s", cfg.dicom_study_desc)

    if not RM_REPORT_PDF.exists():
        logger.warning("AVISO: Archivo principal no encontrado en %s", RM_REPORT_PDF)
        return False

    report_path = Path(RM_REPORT_PDF)
    report_upload_name = RM_REPORT_UPLOAD_NAME or report_path.name
    if is_image_file(report_path):
        logger.info("Subiendo archivo principal como imagen DICOM/JPEG/PNG...")
        report_result = idonia.upload_dicom(
            image_path          = report_path,
            dicom_patient_id    = cfg.dicom_patient_id,
            dicom_accession_num = cfg.dicom_accession_num,
            dicom_study_desc    = cfg.dicom_study_desc,
        )
        logger.info("[OK] Archivo principal subido como imagen '%s'. Respuesta: %s", report_upload_name, report_result)
    else:
        logger.info("Subiendo informe médico PDF...")
        report_result = idonia.upload_report(
            pdf_path            = report_path,
            dicom_patient_id    = cfg.dicom_patient_id,
            dicom_accession_num = cfg.dicom_accession_num,
            dicom_study_desc    = cfg.dicom_study_desc,
        )
        logger.info("[OK] Informe subido como '%s'. Respuesta: %s", report_upload_name, report_result)

    study_image_path = Path(RM_IMAGE_PNG) if RM_IMAGE_PNG else None
    if study_image_path and study_image_path.exists() and study_image_path.resolve() != report_path.resolve():
        logger.info("")
        logger.info("Subiendo imagen del estudio a Idonia...")
        image_upload_name = RM_IMAGE_UPLOAD_NAME or study_image_path.name
        img_result = idonia.upload_dicom(
            image_path          = study_image_path,
            dicom_patient_id    = cfg.dicom_patient_id,
            dicom_accession_num = cfg.dicom_accession_num,
            dicom_study_desc    = cfg.dicom_study_desc,
        )
        logger.info("[OK] Imagen subida como '%s'. Respuesta: %s", image_upload_name, img_result)
    elif study_image_path and study_image_path.exists():
        logger.info("Imagen de estudio ya incluida en el archivo principal; se omite la subida duplicada.")
    else:
        logger.info("No se recibió imagen de estudio del cliente; se omite la subida de imagen.")

    logger.info("[OK] Phase I completada.")
    return True


#  Phase II  

def phase_2_humanize(
    idonia: IdoniaClient,
    recog: RecogClient,
    multilingual: MultilingualClient,
    multimodal: MultimodalClient,
    cfg,
    language: str = "es",
    describe_image: bool = False,
    anonymize: bool = True,
    simulate_error: int | None = None,
    image_description: str | None = None,
) -> bool:
    """
    - Extracts text from the PDF with docling
    - Calls Recog API → receives humanized PDF
    - Uploads 'Informe para paciente.pdf' to Idonia
      Endpoint: POST /files/report_hak_<num_participante>
      Same route as Phase I
    """
    if simulate_error == 4:
        import requests
        # Simulate that Recog does not respond
        raise requests.exceptions.ConnectionError(
            "HTTPSConnectionPool(host='api.recog.es', port=443): "
            "Name or service not known"
        )

    logger = get_logger("pipeline.fase2", log_dir=_LOG_DIR)
    logger.info("=" * 55)
    logger.info("FASE II — Humanización (IA)")
    logger.info("=" * 55)

    logger.info("Extrayendo texto del informe médico...")
    if not REPORT_PATH.exists():
        logger.warning("AVISO: Informe no encontrado en %s", REPORT_PATH)
        return False

    try:
        from docling.document_converter import DocumentConverter
        converter = DocumentConverter()
        doc = converter.convert(str(REPORT_PATH)).document
        report_text = doc.export_to_text().strip()
    except ImportError as _imp_err:
        logger.warning("AVISO: docling no instalado o no importable. Ejecuta: pip install docling")
        logger.warning("   Python usado: %s", sys.executable)
        logger.warning("   Error: %s", _imp_err)
        return False

    logger.info("[OK] Texto extraído (%s caracteres)", len(report_text))

    #  GDPR: Anonymization of Channel B (AI)
    output_target = _LOG_DIR if _LOG_DIR else OUTPUT_DIR
    output_target = Path(output_target)
    output_target.mkdir(parents=True, exist_ok=True)

    # Save original text (internal audit, never leaves the backend)
    original_txt = output_target / "texto_extraido_original.txt"
    original_txt.write_text(report_text, encoding="utf-8")
    logger.info("[RGPD] Texto original guardado en %s (auditoría interna)", original_txt)

    anonymizer = build_anonymizer_from_config(cfg)
    if anonymize:
        # Anonymize: Clean Channel B for Recog, Gemma, Qwen
        report_text = anonymizer.anonymize_text(report_text)
        logger.info("[RGPD] Texto anonimizado (%s caracteres)", len(report_text))
    else:
        logger.info("[RGPD] Anonimización desactivada por el usuario; se conserva el texto original para procesamiento.")

    # Save text for Channel B
    extracted_txt = output_target / "texto_extraido.txt"
    extracted_txt.write_text(report_text, encoding="utf-8")
    logger.info("[OK] Texto guardado en %s", extracted_txt)

    # ── Description of medical image via multimodal LLM ───────────────────────
    if image_description:
        logger.info("")
        logger.info("Usando descripción de imagen proporcionada por el médico...")
        report_text += f"\n\nDESCRIPCIÓN DE LA IMAGEN:\n{image_description}"
        extracted_txt.write_text(report_text, encoding="utf-8")
        logger.info("[OK] Descripción del médico añadida (%s caracteres)", len(image_description))
        logger.info("[OK] Texto actualizado guardado en %s", extracted_txt)
    elif describe_image:
        logger.info("")
        logger.info("Generando descripción de la imagen médica con LLM multimodal...")
        if RM_IMAGE_PNG and RM_IMAGE_PNG.exists():
            image_desc = multimodal.describe_medical_image(RM_IMAGE_PNG, logger=logger)
            if image_desc:
                report_text += f"\n\nDESCRIPCIÓN DE LA IMAGEN:\n{image_desc}"
                extracted_txt.write_text(report_text, encoding="utf-8")
                logger.info("[OK] Descripción añadida (%s caracteres)", len(image_desc))
                logger.info("[OK] Texto actualizado guardado en %s", extracted_txt)
            else:
                logger.warning("AVISO: No se pudo generar descripción de la imagen. Continuing sin ella.")
        else:
            logger.info("No se recibió imagen de estudio del cliente; se omite la descripción multimodal.")
    else:
        logger.info("   Descripción de imagen omitida (usa --imagen para activarla).")

    logger.info("")
    logger.info("Llamando API Recog para humanizar el informe...")
    pdf_es_bytes = recog.humanize_report(report_text)
    logger.info("[OK] Recog devolvió PDF (%s bytes)", len(pdf_es_bytes))

    # Name for Spanish humanized report.
    es_idonia_filename = "Informe para paciente.pdf"
    es_local_filename  = "Informe para paciente.pdf"

    # Save base PDF in Spanish locally
    pdf_es_path = OUTPUT_DIR / es_local_filename
    pdf_es_path.write_bytes(pdf_es_bytes)
    logger.info("[OK] PDF español guardado localmente en %s", pdf_es_path)

    logger.info("")
    logger.info("Subiendo '%s' a Idonia...", es_idonia_filename)
    logger.info("  Endpoint : /files/report_hak_%s", cfg.idonia_num_participante)
    logger.info("  PatientID: %s", cfg.dicom_patient_id)
    logger.info("  Accession: %s", cfg.dicom_accession_num)
    logger.info("  StudyDesc: %s", cfg.dicom_study_desc)

    result = idonia.upload_patient_report(
        pdf_bytes           = pdf_es_bytes,
        dicom_patient_id    = cfg.dicom_patient_id,
        dicom_accession_num = cfg.dicom_accession_num,
        dicom_study_desc    = cfg.dicom_study_desc,
        filename            = es_idonia_filename,
    )
    logger.info("[OK] '%s' subido a Idonia. Respuesta: %s", es_idonia_filename, result)

    #  Multilingual: translate to the requested language
    if language != "es":
        logger.info("")
        logger.info("=" * 55)
        logger.info("MULTILINGÜE — Generando informe en %s", SUPPORTED_LANGUAGES.get(language, language))
        logger.info("=" * 55)

        # Extract text from the Spanish PDF generated by Recog
        logger.info("Extrayendo texto del PDF español con docling...")
        try:
            from docling.document_converter import DocumentConverter
            converter = DocumentConverter()
            doc = converter.convert(str(pdf_es_path)).document
            recog_text_es = doc.export_to_text().strip()
        except Exception as conv_err:
            logger.error("Error extrayendo texto del PDF de Recog: %s", conv_err)
            return False

        logger.info("[OK] Texto extraído del PDF español (%s caracteres)", len(recog_text_es))

        if anonymize:
            # GDPR: re-anonymize Recog text before translator (defense in depth)
            recog_text_es = anonymizer.anonymize_text(recog_text_es)
            logger.info("[RGPD] Texto de Recog re-anonimizado (%s caracteres)", len(recog_text_es))
        else:
            logger.info("[RGPD] Se omite la re-anonimización del texto de Recog porque está desactivada.")

        # Save extracted text for evidence
        recog_txt_path = output_target / "texto_recog_es.txt"
        recog_txt_path.write_text(recog_text_es, encoding="utf-8")
        logger.info("[OK] Texto de Recog guardado en %s", recog_txt_path)

        # Read LaTeX template
        template_path = Path(__file__).parent.parent / "latex_template" / "results_template.tex"
        if not template_path.exists():
            logger.error("Plantilla LaTeX no encontrada: %s", template_path)
            return False
        latex_template = template_path.read_text(encoding="utf-8")

        # Translate with multilingual LLM
        logger.info("Traduciendo informe al %s vía LLM multilingüe (%s)...", language, cfg.multilingual_model_name)
        latex_translated = multilingual.translate_latex(
            latex_template=latex_template,
            source_text=recog_text_es,
            target_lang=language,
            logger=logger,
        )

        # Save translated .tex for evidence
        tex_path = output_target / f"informe_resultados_{language}.tex"
        tex_path.write_text(latex_translated, encoding="utf-8")
        logger.info("[OK] Plantilla LaTeX traducida guardada en %s", tex_path)

        # Compile LaTeX to PDF
        logger.info("Compilando LaTeX a PDF con pdflatex...")
        lang_code = language.upper()
        try:
            pdf_target_path = OUTPUT_DIR / f"Informe para paciente ({lang_code}).pdf"
            compile_latex(
                latex_translated,
                output_pdf=pdf_target_path,
                compiler_path=cfg.latex_compiler_path,
                clean_aux=True,
            )
            logger.info("[OK] PDF compilado: %s", pdf_target_path)
        except RuntimeError as latex_err:
            logger.error("Error compilando LaTeX: %s", latex_err)
            return False

        # Upload translated PDF to Idonia — standard name: 'Informe RM RODILLA (XX).pdf'
        idonia_target_filename = f"Informe RM RODILLA ({lang_code}).pdf"
        logger.info("Subiendo '%s' a Idonia...", idonia_target_filename)
        pdf_target_bytes = pdf_target_path.read_bytes()
        result_target = idonia.upload_patient_report(
            pdf_bytes           = pdf_target_bytes,
            dicom_patient_id    = cfg.dicom_patient_id,
            dicom_accession_num = cfg.dicom_accession_num,
            dicom_study_desc    = cfg.dicom_study_desc,
            filename            = idonia_target_filename,
        )
        logger.info("[OK] Informe RM RODILLA (%s) subido. Respuesta: %s", lang_code, result_target)

    logger.info("[OK] Fase II completada.")
    return True


#  Phase III

def phase_3_magic_link(idonia: IdoniaClient, cfg, language: str = "es", simulate_error: int | None = None) -> dict:
    """
    Generates Magic Link (QR + PIN) for patient and doctor access.
    Endpoint: PUT /ml?route=<DICOMPatientID>/<DICOMAccessionNumber>/<DICOMStudyDescription>
    Final URL: https://demo.idonia.com/v/<num_participante>
    """
    logger = get_logger("pipeline.fase3", log_dir=_LOG_DIR)
    logger.info("=" * 55)
    logger.info("FASE III — Magic Link (Acceso sin barreras)")
    logger.info("=" * 55)

    route = f"{cfg.dicom_patient_id}/{cfg.dicom_accession_num}/{cfg.dicom_study_desc}"
    logger.info("Generando Magic Link para ruta: %s", route)
    logger.info("Endpoint: PUT /ml")

    result = idonia.get_or_create_magic_link(
        dicom_patient_id    = cfg.dicom_patient_id,
        dicom_accession_num = cfg.dicom_accession_num,
        dicom_study_desc    = cfg.dicom_study_desc,
    )

    pin = result.get("PIN", "")
    url = result.get("magic_link_url", "")

    logger.info("")
    logger.info("[OK] Magic Link generado:")
    logger.info("   URL : %s", url)
    logger.info("   PIN : %s", pin)
    logger.info("")
    logger.info("   Con este enlace, el paciente y su médico de Panes pueden ver:")
    logger.info("   • El informe médico original de Sierrallana")
    logger.info("   • La imagen del estudio (RM de rodilla)")
    logger.info("   • El informe humanizado por la IA de Recog")
    if language != "es":
        logger.info("   • El informe humanizado en %s", SUPPORTED_LANGUAGES.get(language, language))

    return result


#  Main

def main():
    parser = argparse.ArgumentParser(description="Pipeline IABiomed 2026 — SINAI-UJA")
    parser.add_argument("--phase", type=int, choices=[1, 2, 3], default=None,
                        help="Ejecutar solo una fase (1, 2 o 3). Por defecto: todas.")
    parser.add_argument("--auto-fix", action="store_true",
                        help="Activa el agente LLM para diagnóstico y reintentos automáticos.")
    parser.add_argument("--simulate-error", type=int, choices=[1, 2, 3, 4], default=None,
                        help="Fuerza un error de API real: 1=Timeout Idonia, 2=401 Unauthorized, 3=503 Service Unavailable, 4=Recog sin conexión.")
    parser.add_argument("--log-dir", type=str, default=None,
                        help="Carpeta personalizada donde guardar los logs de esta ejecución.")
    parser.add_argument("--report-path", type=str, default=None,
                        help="Ruta al informe a procesar (PDF, PNG, JPEG, etc.). Por defecto: Informes/Informe RM RODILLA.pdf")
    parser.add_argument("--language", type=str, choices=["es", "ca", "va", "gl", "eu"], default="es",
                        help="Idioma adicional para el informe humanizado. Siempre se genera español. Por defecto: es")
    parser.add_argument("--imagen", action="store_true",
                        help="Activa la descripción de la imagen médica con LLM multimodal (gemma-4-31B-it) antes de humanizar.")
    args = parser.parse_args()

    # Determine logs folder
    global _LOG_DIR
    _LOG_DIR = Path(args.log_dir) if args.log_dir else None

    # Determine report path
    global REPORT_PATH
    if args.report_path:
        REPORT_PATH = Path(args.report_path)
    else:
        REPORT_PATH = RM_REPORT_PDF

    logger = get_logger("pipeline.main", log_dir=_LOG_DIR)
    logger.info("")
    logger.info("Hackathon IABiomed 2026 — SINAI-UJA")
    logger.info("Reto: Interoperabilidad y humanización médica")

    try:
        cfg = load_config()
    except EnvironmentError as e:
        logger.error("Error de configuración: %s", e)
        sys.exit(1)

    idonia = create_idonia_client(cfg)
    recog = create_recog_client(cfg)
    multilingual = create_multilingual_client(cfg)
    multimodal = create_multimodal_client(cfg)

    logger.info("Participante  : %s", cfg.idonia_num_participante)
    logger.info("PatientID     : %s", cfg.dicom_patient_id)
    logger.info("AccessionNum  : %s", cfg.dicom_accession_num)
    logger.info("StudyDesc     : %s", cfg.dicom_study_desc)
    logger.info("Idioma extra  : %s (%s)", args.language, SUPPORTED_LANGUAGES.get(args.language, "es"))

    run_all = args.phase is None
    exit_code = 0

    def _run_phase(phase_func, phase_label, *phase_args):
        """Executes a phase with automatic retries and diagnosis via LLM."""
        nonlocal exit_code
        try:
            ok = phase_func(*phase_args)
            if not ok and run_all:
                exit_code = 1
                return False
            return True
        except Exception as exc:
            # Show error to user BEFORE calling the agent
            print("\n" + "!" * 60)
            print(f" ERROR EN {phase_label.upper()}")
            print("!" * 60)
            print(f"   Tipo: {type(exc).__name__}")
            print(f"   Mensaje: {exc}")
            print(f"   Archivo: {traceback.extract_tb(exc.__traceback__)[-1].filename}")
            print(f"   Línea: {traceback.extract_tb(exc.__traceback__)[-1].lineno}")
            print("!" * 60)
            print()

            # Automatic retries with backoff for temporary errors
            if args.auto_fix:
                from handle_errors import _retry_with_backoff, _is_retryable_error
                if _is_retryable_error(exc):
                    print(" Error temporal detectado. Intentando reintentos automáticos...")
                    success, retry_result = _retry_with_backoff(phase_func, phase_args)
                    if success:
                        print(f"\n {phase_label} completada tras reintentos automáticos.")
                        return True
                    else:
                        exc = retry_result  # use the last exception for the diagnosis

            print(" Activando agente LLM para diagnóstico...")
            print()

            result = handle_error(
                exc,
                phase_name=phase_label,
                auto_fix=args.auto_fix,
                log_dir=_LOG_DIR,
                language=args.language,
            )
            exit_code = 1
            return False

    if run_all or args.phase == 1:
        _run_phase(phase_1_ingest, "Fase I — Ingesta", idonia, cfg, args.simulate_error)
        if exit_code and run_all:
            sys.exit(1)

    if (run_all or args.phase == 2) and not exit_code:
        _run_phase(phase_2_humanize, "Fase II — Humanización", idonia, recog, multilingual, multimodal, cfg, args.language, args.imagen, args.simulate_error)
        if exit_code and run_all:
            sys.exit(1)

    if (run_all or args.phase == 3) and not exit_code:
        _run_phase(phase_3_magic_link, "Fase III — Magic Link", idonia, cfg, args.language, args.simulate_error)
        if exit_code and run_all:
            sys.exit(1)

    if run_all and not exit_code:
        logger.info("=" * 55)
        logger.info("[OK] PIPELINE COMPLETO")
        logger.info("=" * 55)
        logger.info("Las 3 fases ejecutadas correctamente.")


if __name__ == "__main__":
    main()
