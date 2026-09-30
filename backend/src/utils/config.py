"""
Configuration loader — Hackathon IABiomed 2026 — SINAI-UJA
Reads credentials from the .env file. Never hardcode real values here.
"""

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv():
    env_file = Path(__file__).parent.parent.parent / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        val = value.partition("#")[0].strip()
        os.environ[key.strip()] = val


_load_dotenv()


@dataclass
class Config:
    # Idonia
    idonia_api_key:          str
    idonia_api_secret:       str
    idonia_base_url:         str
    idonia_num_participante: str

    # Idonia: study route parameters (manual section 5 and 6)
    # File path  : <DICOMPatientID>/<DICOMAccessionNumber>/<DICOMStudyDescription>
    # Magic Link : <DICOMPatientID>/<DICOMAccessionNumber>
    # Visual example    : 12345678A > Traslados desde Asturias > RM-RODILLA-2026
    dicom_patient_id:      str   # DICOMPatientID        → e.g.: "12345678A"
    dicom_accession_num:   str   # DICOMAccessionNumber  → e.g.: "Traslados desde Asturias"
    dicom_study_desc:      str   # DICOMStudyDescription → e.g.: "RM-RODILLA-2026"

    # Magic Link
    idonia_ml_id:  str           # ML ID received from Idonia → e.g.: "hacknumX"

    # Recog
    recog_api_key:  str
    recog_base_url: str
    recog_endpoint: str

    # LLM (error correction agent)
    openai_api_key: str
    openai_base_url: str
    model_name:      str   # backward compatibility — alias of agent_model_name

    # Multilingual LLM (report translation)
    agent_model_name: str
    multilingual_model_name: str

    # LaTeX Compiler (for multilingual PDFs)
    latex_compiler_path: str | None

    # GDPR Anonymization (optional)
    # Recommended format: separate fields
    patient_first_name: str | None = None
    patient_last_name1: str | None = None
    patient_last_name2: str | None = None
    doctor_first_name:  str | None = None
    doctor_last_name1:  str | None = None
    doctor_last_name2:  str | None = None
    # Alternative format (fallback): full name in a single field
    patient_full_name: str | None = None
    doctor_full_name:  str | None = None
    hospital_name:     str | None = None
    study_date:        str | None = None
    patient_dob:       str | None = None


def load_config() -> Config:
    def _require(key: str) -> str:
        val = os.getenv(key)
        if not val:
            raise EnvironmentError(
                f"Variable de entorno requerida no encontrada: {key}\n"
                f"Añádela a tu fichero .env."
            )
        return val

    return Config(
        idonia_api_key          = _require("IDONIA_API_KEY"),
        idonia_api_secret       = _require("IDONIA_API_SECRET"),
        idonia_base_url         = os.getenv("IDONIA_BASE_URL", "https://connect-staging.idonia.com"),
        idonia_num_participante = _require("IDONIA_NUM_PARTICIPANTE"),

        dicom_patient_id    = os.getenv("PATIENT_DNI",         "12345678A"),
        dicom_accession_num = os.getenv("DICOM_ACCESSION_NUM", "Traslados desde Asturias"),
        dicom_study_desc    = os.getenv("DICOM_STUDY_DESC") or os.getenv("ROOT_FOLDER", "RM-RODILLA-2026"),

        idonia_ml_id = _require("IDONIA_ML_ID"),

        recog_api_key  = _require("RECOG_API_KEY"),
        recog_base_url = os.getenv("RECOG_BASE_URL", "https://api.recog.es"),
        recog_endpoint = os.getenv("RECOG_ENDPOINT", "/relisten/dictation/process/report-results"),

        openai_api_key  = os.getenv("OPENAI_API_KEY", "sk-no-key"),
        openai_base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        model_name      = os.getenv("MODEL_NAME", os.getenv("AGENT_MODEL_NAME", "gpt-4o")),

        agent_model_name        = os.getenv("AGENT_MODEL_NAME", "gpt-4o"),
        multilingual_model_name = os.getenv("MULTILINGUAL_MODEL_NAME", "gpt-4o"),

        latex_compiler_path = os.getenv("LATEX_COMPILER_PATH") or None,

        patient_first_name = os.getenv("PATIENT_FIRST_NAME") or None,
        patient_last_name1 = os.getenv("PATIENT_LAST_NAME1") or None,
        patient_last_name2 = os.getenv("PATIENT_LAST_NAME2") or None,
        doctor_first_name  = os.getenv("DOCTOR_FIRST_NAME") or None,
        doctor_last_name1  = os.getenv("DOCTOR_LAST_NAME1") or None,
        doctor_last_name2  = os.getenv("DOCTOR_LAST_NAME2") or None,

        patient_full_name = os.getenv("PATIENT_FULL_NAME") or None,
        doctor_full_name  = os.getenv("DOCTOR_FULL_NAME") or None,
        hospital_name     = os.getenv("HOSPITAL_NAME") or None,
        study_date        = os.getenv("STUDY_DATE") or None,
        patient_dob       = os.getenv("PATIENT_DOB") or None,
    )