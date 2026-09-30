import sys
import os
import shutil
import uuid
import asyncio
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import pdfplumber

# Add src to sys.path
backend_dir = Path(__file__).parent
sys.path.append(str(backend_dir / "src"))

from utils.config import load_config
from utils.helpers import (
    is_image_file,
    create_idonia_client,
    create_recog_client,
    create_multilingual_client,
    create_multimodal_client
)
import pipeline
from fastapi.middleware.cors import CORSMiddleware
from utils.handle_errors import handle_error, _is_retryable_error, _retry_with_backoff

app = FastAPI(title="IABiomed 2026 SINAI-UJA API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure directories exist
OUTPUT_DIR = backend_dir / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
TMP_DIR = OUTPUT_DIR / "tmp"
TMP_DIR.mkdir(exist_ok=True)

# Lock to prevent race conditions on module-level globals
pipeline_lock = asyncio.Lock()

def collect_logs(log_dir: Path) -> list:
    log_lines = []
    if log_dir.exists():
        for file in log_dir.glob("*.log"):
            try:
                for line in file.read_text(encoding="utf-8").splitlines():
                    log_lines.append(line)
            except Exception:
                pass
    # Sort logs chronologically by their timestamp prefix
    log_lines.sort()
    return log_lines

def extract_text_from_pdf(pdf_path: Path) -> str:
    try:
        with pdfplumber.open(pdf_path) as pdf:
            return "\n".join([page.extract_text() or "" for page in pdf.pages]).strip()
    except Exception as e:
        return f"No se pudo extraer el texto del PDF: {e}"



@app.post("/api/describe-image")
async def describe_image_endpoint(
    image: UploadFile = File(...)
):
    try:
        cfg = load_config()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Configuration error: {e}")
        
    multimodal = create_multimodal_client(cfg)
    
    # Save temp image
    run_id = f"run_{uuid.uuid4().hex[:8]}"
    temp_image_path = TMP_DIR / f"{run_id}_{image.filename}"
    with temp_image_path.open("wb") as buffer:
        shutil.copyfileobj(image.file, buffer)
        
    try:
        description = multimodal.describe_medical_image(temp_image_path)
    finally:
        if temp_image_path.exists():
            temp_image_path.unlink()
            
    return {"description": description}

@app.post("/api/process")
async def process_report(
    file: UploadFile = File(...),
    study_image: UploadFile = File(None),
    language: str = Form("es"),
    describe_image: bool = Form(False),
    anonymize: bool = Form(True),
    image_description: str = Form(None),
    patient_id: str = Form(None),
    accession_num: str = Form(None),
    study_desc: str = Form(None)
):
    # Create unique run ID
    run_id = f"run_{uuid.uuid4().hex[:8]}"
    run_log_dir = backend_dir / "logs" / run_id
    run_log_dir.mkdir(parents=True, exist_ok=True)

    # Save uploaded files into a per-run subdirectory so the filename
    # stays clean (no run_id prefix) when uploaded to Idonia.
    run_tmp_dir = TMP_DIR / run_id
    run_tmp_dir.mkdir(parents=True, exist_ok=True)

    temp_report_path = run_tmp_dir / file.filename
    with temp_report_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    temp_image_path = None
    if study_image:
        temp_image_path = run_tmp_dir / study_image.filename
        with temp_image_path.open("wb") as buffer:
            shutil.copyfileobj(study_image.file, buffer)

    # Run the pipeline with lock
    async with pipeline_lock:
        # Set pipeline globals
        pipeline.RM_REPORT_PDF = temp_report_path
        pipeline.REPORT_PATH = temp_report_path
        pipeline.RM_REPORT_UPLOAD_NAME = file.filename
        if temp_image_path:
            pipeline.RM_IMAGE_PNG = temp_image_path
            pipeline.RM_IMAGE_UPLOAD_NAME = study_image.filename if study_image else file.filename
        elif is_image_file(temp_report_path):
            pipeline.RM_IMAGE_PNG = temp_report_path
            pipeline.RM_IMAGE_UPLOAD_NAME = file.filename
        else:
            pipeline.RM_IMAGE_PNG = None
            pipeline.RM_IMAGE_UPLOAD_NAME = None
        pipeline._LOG_DIR = run_log_dir
        
        # Override output dir to backend output dir
        pipeline.OUTPUT_DIR = OUTPUT_DIR

        # Initialize clients
        try:
            cfg = load_config()
            if patient_id:
                cfg.dicom_patient_id = patient_id
            if accession_num:
                cfg.dicom_accession_num = accession_num
            if study_desc:
                cfg.dicom_study_desc = study_desc
        except Exception as e:
            return JSONResponse(
                status_code=200,
                content={
                    "success": False,
                    "error": {
                        "phase": "Inicialización",
                        "type": "ConfigError",
                        "message": f"Error de configuración: {e}. ¿Has configurado el archivo .env?",
                        "actions": ["Copia .env.example a .env en el directorio background/ y rellena tus credenciales reales."]
                    },
                    "logs": [f"Error de configuración: {e}"]
                }
            )

        idonia = create_idonia_client(cfg)
        recog = create_recog_client(cfg)
        multilingual = create_multilingual_client(cfg)
        multimodal = create_multimodal_client(cfg)

        success = True
        error_info = None

        def run_phase_1():
            return pipeline.phase_1_ingest(idonia, cfg)

        def run_phase_2():
            return pipeline.phase_2_humanize(
                idonia, recog, multilingual, multimodal, cfg,
                language=language, describe_image=describe_image, anonymize=anonymize,
                image_description=image_description
            )

        def run_phase_3():
            return pipeline.phase_3_magic_link(idonia, cfg, language)

        # Run Phase 1
        try:
            # raise Exception("Simulated connection failure for testing Tirita")
            p1_ok = run_phase_1()
            if not p1_ok:
                success = False
                error_info = {"phase": "Fase I — Ingesta", "message": "La subida de archivos falló."}
        except Exception as exc:
            success = False
            diag = handle_error(exc, "Fase I — Ingesta", auto_fix=False, log_dir=run_log_dir, language=language)
            error_info = {
                "phase": "Fase I — Ingesta",
                "type": type(exc).__name__,
                "message": diag.get("user_message", str(exc)),
                "technical": diag.get("technical_analysis", ""),
                "actions": diag.get("suggested_actions", [])
            }

        # Run Phase 2
        if success:
            try:
                p2_ok = run_phase_2()
                if not p2_ok:
                    success = False
                    error_info = {"phase": "Fase II — Humanización", "message": "La humanización falló."}
            except Exception as exc:
                success = False
                diag = handle_error(exc, "Fase II — Humanización", auto_fix=False, log_dir=run_log_dir, language=language)
                error_info = {
                    "phase": "Fase II — Humanización",
                    "type": type(exc).__name__,
                    "message": diag.get("user_message", str(exc)),
                    "technical": diag.get("technical_analysis", ""),
                    "actions": diag.get("suggested_actions", [])
                }

        # Run Phase 3
        magic_link_res = {}
        if success:
            try:
                magic_link_res = run_phase_3()
            except Exception as exc:
                success = False
                diag = handle_error(exc, "Fase III — Magic Link", auto_fix=False, log_dir=run_log_dir, language=language)
                error_info = {
                    "phase": "Fase III — Magic Link",
                    "type": type(exc).__name__,
                    "message": diag.get("user_message", str(exc)),
                    "technical": diag.get("technical_analysis", ""),
                    "actions": diag.get("suggested_actions", [])
                }

        # Clean up the per-run temp directory and all its files
        try:
            shutil.rmtree(run_tmp_dir, ignore_errors=True)
        except Exception:
            pass

        # Collect logs
        run_logs = collect_logs(run_log_dir)

        if not success:
            return JSONResponse(
                status_code=200,
                content={
                    "success": False,
                    "error": error_info,
                    "logs": run_logs
                }
            )

        # Extract text comparison
        original_text = ""
        orig_txt_path = run_log_dir / "texto_extraido.txt"
        if orig_txt_path.exists():
            original_text = orig_txt_path.read_text(encoding="utf-8")

        # Humanized text extraction from generated PDF
        humanized_text = ""
        # Match the filenames written in pipeline.py:
        #   language == "es"  → 'Informe para paciente.pdf'
        #   language != "es"  → 'Informe RM RODILLA (XX).pdf'
        if language == "es":
            target_pdf_path = OUTPUT_DIR / "Informe para paciente.pdf"
            if not target_pdf_path.exists():
                target_pdf_path = OUTPUT_DIR / "Informe RM RODILLA.pdf"
        else:
            target_pdf_path = OUTPUT_DIR / f"Informe RM RODILLA ({language.upper()}).pdf"
            if not target_pdf_path.exists():
                target_pdf_path = OUTPUT_DIR / f"Informe para paciente ({language.upper()}).pdf"

        if target_pdf_path.exists():
            humanized_text = extract_text_from_pdf(target_pdf_path)

        return {
            "success": True,
            "magic_link_url": magic_link_res.get("magic_link_url", ""),
            "pin": magic_link_res.get("PIN", ""),
            "original_text": original_text,
            "humanized_text": humanized_text,
            "pdf_url": f"/api/pdf?language={language}",
            "logs": run_logs,
            "language": language
        }

@app.get("/api/status")
def get_status():
    return {"status": "ok", "app": "IABiomed SINAI-UJA API Server"}


@app.get("/api/pdf")
def get_generated_pdf(language: str = "es"):
    """
    Serves the last generated patient PDF so the frontend can embed it.
    Tries the new names first, falls back to legacy names.
    """
    candidates = [
        OUTPUT_DIR / "Informe para paciente.pdf",
        OUTPUT_DIR / "Informe RM RODILLA.pdf",
    ]
    if language != "es":
        lang_code = language.upper()
        candidates = [
            OUTPUT_DIR / f"Informe RM RODILLA ({lang_code}).pdf",
            OUTPUT_DIR / f"Informe para paciente ({lang_code}).pdf",
        ] + candidates

    for path in candidates:
        if path.exists():
            from fastapi.responses import Response
            pdf_bytes = path.read_bytes()
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"inline; filename=\"{path.name}\"",
                    "Cache-Control": "no-cache",
                },
            )

    raise HTTPException(status_code=404, detail="PDF no encontrado. Ejecuta el pipeline primero.")


# Serve frontend static files
frontend_dir = Path(__file__).parent.parent / "frontend"
frontend_dist = frontend_dir / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
elif frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
