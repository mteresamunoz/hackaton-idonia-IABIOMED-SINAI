"""
Anonymizer & GDPR Compliance Module
Hackathon IABiomed 2026 — Team SINAI-UJA

Decouples the data channels in the backend:
  • Channel A (Secure / Idonia): maintains real DNI to create folders and DICOM routes.
  • Channel B (Anonymous / AI): cleans text of PII before sending it to Recog, Gemma,
    Qwen or any external LLM.

Replacement tokens:
  [DNI_OCULTO]               → Spanish DNI / NIE
  [PACIENTE_DESIDENTIFICADO] → patient's full name (configured)
  [TELEFONO_OCULTO]          → Spanish telephone numbers (+34 optional)
  [EMAIL_OCULTO]             → email addresses
  [FECHA_NACIMIENTO_OCULTA]  → explicit date of birth (if configured)
  [NOMBRE_OCULTO]            → proper names detected by heuristic (aggressive mode)

Typical usage in pipeline:
    from anonymizer import build_anonymizer_from_config
    anon = build_anonymizer_from_config(cfg)
    clean_text = anon.anonymize_text(raw_report_text)
    # clean_text → Recog / Multilingual LLM
    # cfg.dicom_patient_id → Idonia (Channel A)
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Optional

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


# Normalization Utilities

def _unaccent(text: str) -> str:
    """Removes accents while maintaining string length (á → a, é → e)."""
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


# Token constants (must never contain real data)

DEFAULT_REPLACEMENTS: dict[str, str] = {
    "dni": "[DNI_OCULTO]",
    "patient_name": "[PACIENTE_DESIDENTIFICADO]",
    "doctor_name": "[MEDICO_DESIDENTIFICADO]",
    "hospital_name": "[HOSPITAL_OCULTO]",
    "study_date": "[FECHA_ESTUDIO_OCULTA]",
    "phone": "[TELEFONO_OCULTO]",
    "email": "[EMAIL_OCULTO]",
    "dob": "[FECHA_NACIMIENTO_OCULTA]",
    "nhc": "[HISTORIA_OCULTA]",
    "volante": "[VOLANTE_OCULTO]",
    "address": "[DIRECCION_OCULTA]",
    "generic_name": "[NOMBRE_OCULTO]",
}

# Spanish DNI: 8 digits + letter, or NIE (X/Y/Z + 7 digits + letter)
# Accepts optional separators: 12345678-A, 12.345.678-A, etc.
_DNI_PATTERN = re.compile(
    r"\b(?:\d[\s.\-]?){7}\d[\s.\-]?[A-HJ-NP-TV-Z]\b"  # 8 digits + letter
    r"|"
    r"\b[XYZ][\s.\-]?(?:\d[\s.\-]?){7}\d[\s.\-]?[A-HJ-NP-TV-Z]\b",  # NIE
    re.IGNORECASE,
)

# Spanish telephone numbers (mobile 6/7 and landline 8/9)
_PHONE_PATTERN = re.compile(
    r"\b(?:\+34[\s.]?)?(?:6|7[1-9]|8[0-9]|9[0-9])\d{1}[\s.]?\d{2}[\s.]?\d{2}[\s.]?\d{2}\b",
    re.IGNORECASE,
)

# Emails
_EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    re.IGNORECASE,
)

# Date of birth: DD/MM/YYYY or DD-MM-YYYY with years 1900-2025
# Used carefully so as not to destroy study dates.
_DOB_PATTERN = re.compile(
    r"\b(0?[1-9]|[12]\d|3[01])[/-](0?[1-9]|1[0-2])[/-](19\d{2}|20[0-2]\d)\b",
)

# Clinical History Number (NHC)
# Detects: "Nº Historia: 3245678", "NoHistoria: 3245678", "NHC: 12345", "Historia Clínica: 1234"
_NHC_PATTERN = re.compile(
    r"\b(?:N[º°.]?\s*|No\s*)(?:Historia|HC|H\.C\.|Hist\.?)\s*(?:Cl[ií]nica)?\s*[:\-]?\s*\d[\d\s.\-/]*\b",
    re.IGNORECASE,
)

# Voucher / reference / report number
# Detects: "Nº Volante: RM-25/1987", "No Informe: RM-25/1987", "Volante: ABC-123"
_VOLANTE_PATTERN = re.compile(
    r"\b(?:N[º°.]?\s*|No\s*)(?:Volante|Informe)\s*[:\-]?\s*[A-Z]{1,3}[-/]?\d+[-/]?\d*\b",
    re.IGNORECASE,
)

# Spanish postal addresses (without AI, pure regex)
# Detects: "Av.Constitucion,45 28015Madrid", "Calle Mayor 5 28001 Madrid"
# Uses (?<!\d)(?!\d) instead of \b because digits don't have word boundary
# with letters (e.g.: "28015Madrid").
_ADDRESS_PATTERN = re.compile(
    r"(?:"
    r"\b(?:Av\.?|Avda\.?|Avenida|C\.?|C/|Calle|P\.?|Pza\.?|Plaza|Pso\.?|Paseo|"
    r"Ronda|Trav\.?|Travesía|Ctra\.?|Carretera|Urb\.?|Urbanización|Edif\.?|Edificio)"
    r"[^\n]{0,60}?"
    r"(?<!\d)[0-5]\d{4}(?!\d)"
    r"[^\n]{0,40}"
    r")",
    re.IGNORECASE,
)

# Proper names heuristic: 2-4 words with initial capital letter.
# Avoids common words at the beginning of a sentence and medical acronyms.
_NAME_HEURISTIC_PATTERN = re.compile(
    r"\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s+){1,3}[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\b",
)

# Common words in capital letters that are NOT person names
_MEDICAL_ACRONYMS = {
    "rm", "tc", "rx", "ecografia", "resonancia", "tomografia", "radiografia",
    "tac", "pet", "rmn", "dicom", "pdf", "url", "qr", "pin", "ia", "ai",
    "urgencias", "hospital", "consulta", "paciente", "medico", "doctor",
    "izquierda", "derecha", "superior", "inferior", "anterior", "posterior",
    "cranial", "caudal", "proximal", "distal", "lateral", "medial",
    "axial", "sagital", "coronal", "oblicua",
}


# Config

@dataclass
class AnonymizerConfig:
    """Anonymizer engine configuration."""

    patient_dni: Optional[str] = None
    # Recommended way: separate fields
    patient_first_name: Optional[str] = None
    patient_last_name1: Optional[str] = None
    patient_last_name2: Optional[str] = None
    doctor_first_name: Optional[str] = None
    doctor_last_name1: Optional[str] = None
    doctor_last_name2: Optional[str] = None
    # Fallback: full name in a single field
    patient_full_name: Optional[str] = None
    doctor_full_name: Optional[str] = None
    hospital_name: Optional[str] = None
    study_date: Optional[str] = None
    patient_dob:       Optional[str] = None  # DD/MM/YYYY for explicit replacement
    openai_api_key:    Optional[str] = None
    openai_base_url:   Optional[str] = None
    model_name:        Optional[str] = None
    replacements: dict[str, str] = field(default_factory=lambda: DEFAULT_REPLACEMENTS.copy())


#  Motor 

#  Name utilities

def _name_variants(name: str) -> set[str]:
    """
    Generates variants of a full name to cover medical and OCR formats.

    Supports:
      • "García López, Antonio"  → also "Antonio García López"
      • "Antonio García López"   → also "García López, Antonio", "López, Antonio García"
      • Capitalization of all variants
      • Versions without accents (for imperfect OCR: Garcia Lopez)
    """
    name = name.strip()
    if not name:
        return set()

    base_variants: set[str] = {name}

    if "," in name:
        parts = [p.strip() for p in name.split(",", 1)]
        if len(parts) == 2:
            apellidos, nombre = parts
            base_variants.add(f"{nombre} {apellidos}")
    else:
        words = name.split()
        if len(words) >= 2:
            for cut in range(1, len(words)):
                nombre_part = " ".join(words[:cut])
                apellidos_part = " ".join(words[cut:])
                base_variants.add(f"{apellidos_part}, {nombre_part}")

    # Expand: uppercase + without accents (OCR) + without space after period (OCR)
    variants: set[str] = set()
    for v in base_variants:
        variants.add(v)
        variants.add(v.upper())
        variants.add(_unaccent(v))
        variants.add(_unaccent(v).upper())
        # OCR usually joins: "P. Martínez" → "P.Martinez"
        no_space = v.replace(". ", ".")
        if no_space != v:
            variants.add(no_space)
            variants.add(no_space.upper())
            variants.add(_unaccent(no_space))
            variants.add(_unaccent(no_space).upper())

    return variants


def _generate_name_combinations(
    first_name: Optional[str],
    last_name1: Optional[str],
    last_name2: Optional[str],
) -> set[str]:
    """
    Generates all possible combinations of a name from its parts.

    Inputs:
      first_name:  "Antonio" or "A." or "P."
      last_name1:  "García"
      last_name2:  "López" (can be None)

    Outputs (example for Antonio García López):
      • Antonio García López
      • García López, Antonio
      • García, Antonio
      • A. García López, A.García López
      • A. García, A.García
      • García López, A.
      • García, A.
      • García López
      • García
      + all versions without accents, in uppercase, etc.
    """
    first = (first_name or "").strip()
    ln1 = (last_name1 or "").strip()
    ln2 = (last_name2 or "").strip()

    if not first and not ln1:
        return set()

    # Determine initial (if first_name is "A.", "A" or "Antonio")
    initial = ""
    if first:
        if len(first) <= 2 and first.endswith("."):
            initial = first  # "A."
        elif len(first) == 1:
            initial = first + "."  # "A" → "A."
        else:
            initial = first[0] + "."  # "Antonio" → "A."

    # Construct last names
    last_names = ln1
    if ln2:
        last_names = f"{ln1} {ln2}"

    base: set[str] = set()

    # 1. Full name
    if first and last_names:
        base.add(f"{first} {last_names}")

    # 2. Last names, First name
    if first and last_names:
        base.add(f"{last_names}, {first}")

    # 3. First last name, First name
    if first and ln1:
        base.add(f"{ln1}, {first}")

    # 4. Initial + last names
    if initial and last_names:
        base.add(f"{initial} {last_names}")
        base.add(f"{initial}{last_names}")

    # 5. Initial + first last name
    if initial and ln1:
        base.add(f"{initial} {ln1}")
        base.add(f"{initial}{ln1}")

    # 6. Last names, Initial
    if initial and last_names:
        base.add(f"{last_names}, {initial}")

    # 7. First last name, Initial
    if initial and ln1:
        base.add(f"{ln1}, {initial}")

    # 8. Only last names
    if last_names:
        base.add(last_names)
    if ln1:
        base.add(ln1)

    # 9. Only first name (if short it can be an initial, if long it can be a name)
    if first:
        base.add(first)

    # Expand: without accents, uppercase, without space after period
    variants: set[str] = set()
    for v in base:
        if not v:
            continue
        variants.add(v)
        variants.add(v.upper())
        variants.add(_unaccent(v))
        variants.add(_unaccent(v).upper())
        no_space = v.replace(". ", ".")
        if no_space != v:
            variants.add(no_space)
            variants.add(no_space.upper())
            variants.add(_unaccent(no_space))
            variants.add(_unaccent(no_space).upper())

    return variants


#  Motor

class Anonymizer:
    """
    Anonymizer engine for medical text for GDPR compliance.

    Designed to run JUST after OCR/PDF extraction
    and BEFORE any calls to AI APIs (Recog, Gemma, Qwen).

    The data flow is separated into two channels:
      • Channel A (Secure): the real DNI travels only to Idonia to create folders.
      • Channel B (Anonymous): the clean text travels to the LLMs.
    """

    def __init__(self, config: AnonymizerConfig):
        self.cfg = config
        self.replacements = config.replacements
        self.client = None
        if OpenAI is not None and config.openai_api_key:
            self.client = OpenAI(
                api_key=config.openai_api_key,
                base_url=config.openai_base_url
            )
        self._patterns: list[tuple[re.Pattern, str]] = []
        self._compile_patterns()

    #  Pattern compilation

    def _compile_patterns(self) -> None:
        """Constructs the list of regex patterns in deterministic order."""
        self._patterns = []

        # 1. Explicit DNI/NIE of the patient (maximum priority)
        if self.cfg.patient_dni:
            escaped = re.escape(self.cfg.patient_dni)
            # Variants with/without separators for the exact DNI
            self._patterns.append(
                (
                    re.compile(rf"\b{escaped}\b", re.IGNORECASE),
                    self.replacements["dni"],
                )
            )

        # 2. Patient name (recommended separate fields, fallback to full_name)
        patient_names = _generate_name_combinations(
            self.cfg.patient_first_name,
            self.cfg.patient_last_name1,
            self.cfg.patient_last_name2,
        )
        if self.cfg.patient_full_name:
            patient_names.update(_name_variants(self.cfg.patient_full_name))
        # Sort from longest to shortest to avoid partial replacements
        for variant in sorted(patient_names, key=len, reverse=True):
            escaped = re.escape(variant)
            self._patterns.append(
                (
                    re.compile(rf"\b{escaped}\b", re.IGNORECASE),
                    self.replacements["patient_name"],
                )
            )

        # 3. Doctor name (recommended separate fields, fallback to full_name)
        doctor_names = _generate_name_combinations(
            self.cfg.doctor_first_name,
            self.cfg.doctor_last_name1,
            self.cfg.doctor_last_name2,
        )
        if self.cfg.doctor_full_name:
            doctor_names.update(_name_variants(self.cfg.doctor_full_name))
        # Sort from longest to shortest to avoid partial replacements
        for variant in sorted(doctor_names, key=len, reverse=True):
            escaped = re.escape(variant)
            self._patterns.append(
                (
                    re.compile(rf"\b{escaped}\b", re.IGNORECASE),
                    self.replacements["doctor_name"],
                )
            )

        # 4. Hospital / health center name
        if self.cfg.hospital_name:
            escaped_hosp = re.escape(self.cfg.hospital_name)
            self._patterns.append(
                (
                    re.compile(rf"\b{escaped_hosp}\b", re.IGNORECASE),
                    self.replacements["hospital_name"],
                )
            )

        # 5. Study date (can be identifying in combination)
        if self.cfg.study_date:
            escaped_date = re.escape(self.cfg.study_date)
            self._patterns.append(
                (
                    re.compile(rf"\b{escaped_date}\b"),
                    self.replacements["study_date"],
                )
            )

        # 6. Explicit patient date of birth
        if self.cfg.patient_dob:
            escaped_dob = re.escape(self.cfg.patient_dob)
            self._patterns.append(
                (
                    re.compile(rf"\b{escaped_dob}\b"),
                    self.replacements["dob"],
                )
            )

        # 5. Clinical History Number (NHC)
        self._patterns.append(
            (_NHC_PATTERN, self.replacements["nhc"])
        )

        # 6. Voucher / reference number
        self._patterns.append(
            (_VOLANTE_PATTERN, self.replacements["volante"])
        )

        # 7. Spanish postal addresses (detects type of road + postal code)
        self._patterns.append(
            (_ADDRESS_PATTERN, self.replacements["address"])
        )

        # 8. Generic DNI/NIE (any Spanish DNI in the text)
        self._patterns.append(
            (_DNI_PATTERN, self.replacements["dni"])
        )

        # 10. Telephones
        self._patterns.append(
            (_PHONE_PATTERN, self.replacements["phone"])
        )

        # 11. Emails
        self._patterns.append(
            (_EMAIL_PATTERN, self.replacements["email"])
        )

        # 12. Generic dates of birth (caution: may affect study dates)
        # Only activated if patient_dob is configured or aggressive mode is requested
        if self.cfg.patient_dob:
            self._patterns.append(
                (_DOB_PATTERN, self.replacements["dob"])
            )

    #  Anonymization

    def anonymize_text(self, text: str, aggressive_names: bool = False) -> str:
        """
        Cleans the text of personally identifiable information (PII).

        Args:
            text: Text extracted from the medical report (Channel B).
            aggressive_names: If True, applies proper names heuristic for
                capitalized names. Useful if the report contains names of doctors,
                family members, etc. May generate false positives.

        Returns:
            Anonymized text ready to send to AI APIs.
        """
        if self.client is not None:
            try:
                # Build list of specific data to guide the LLM
                patient_name_str = f"{self.cfg.patient_first_name or ''} {self.cfg.patient_last_name1 or ''} {self.cfg.patient_last_name2 or ''}".strip() or self.cfg.patient_full_name or "Desconocido"
                doctor_name_str = f"{self.cfg.doctor_first_name or ''} {self.cfg.doctor_last_name1 or ''} {self.cfg.doctor_last_name2 or ''}".strip() or self.cfg.doctor_full_name or "Desconocido"
                patient_dni_str = self.cfg.patient_dni or "Desconocido"
                hospital_name_str = self.cfg.hospital_name or "Desconocido"
                study_date_str = self.cfg.study_date or "Desconocido"
                patient_dob_str = self.cfg.patient_dob or "Desconocido"

                system_prompt = (
                    "Eres un experto en privacidad médica y RGPD. Tu tarea es anonimizar informes médicos.\n"
                    "Debes identificar cualquier dato personal identificativo (PII) en el texto del informe y sustituirlo por el token correspondiente de esta lista:\n"
                    "- DNI, NIE o pasaporte (de cualquier persona en el texto) -> `[DNI_OCULTO]`\n"
                    "- Nombres de pila, apellidos o iniciales del PACIENTE -> `[PACIENTE_DESIDENTIFICADO]`\n"
                    "- Nombres de pila, apellidos o iniciales del MÉDICO/DOCTOR -> `[MEDICO_DESIDENTIFICADO]`\n"
                    "- Nombres de hospitales, clínicas o centros de salud -> `[HOSPITAL_OCULTO]`\n"
                    "- Fechas del estudio o exploración -> `[FECHA_ESTUDIO_OCULTA]`\n"
                    "- Fechas de nacimiento de personas (o edades muy específicas que puedan identificar) -> `[FECHA_NACIMIENTO_OCULTA]`\n"
                    "- Números de teléfono -> `[TELEFONO_OCULTO]`\n"
                    "- Direcciones de correo electrónico (email) -> `[EMAIL_OCULTO]`\n"
                    "- Direcciones postales o físicas -> `[DIRECCION_OCULTA]`\n"
                    "- Números de historia clínica (NHC) -> `[HISTORIA_OCULTA]`\n"
                    "- Números de volante, referencia o informe -> `[VOLANTE_OCULTO]`\n"
                    "- Cualquier otro nombre de pila propio o apellido genérico (familiares, etc.) -> `[NOMBRE_OCULTO]`\n\n"
                    "Instrucciones críticas:\n"
                    "1. No alteres la terminología clínica, diagnósticos, hallazgos, ni tratamientos médicos. Solo debes anonimizar datos identificativos de personas, centros y fechas.\n"
                    "2. Devuelve ÚNICAMENTE el texto anonimizado directamente. No agregues ninguna explicación, prefacio, comentario ni bloques de markdown (como ``` o ```text)."
                )

                user_prompt = (
                    f"Anonimiza el siguiente informe médico.\n\n"
                    f"Información conocida del paciente y del estudio para ayudarte a identificar PII:\n"
                    f"- Paciente: {patient_name_str}\n"
                    f"- DNI/NIE Paciente: {patient_dni_str}\n"
                    f"- Médico: {doctor_name_str}\n"
                    f"- Hospital: {hospital_name_str}\n"
                    f"- Fecha de estudio: {study_date_str}\n"
                    f"- Fecha de nacimiento: {patient_dob_str}\n\n"
                    f"=== TEXTO DEL INFORME ===\n"
                    f"{text}\n"
                )

                # Call LLM
                response = self.client.chat.completions.create(
                    model=self.cfg.model_name or "gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.1,
                )

                raw_anonymized = response.choices[0].message.content or ""
                # Strip markdown code blocks if the LLM returned them
                if raw_anonymized.strip().startswith("```"):
                    lines = raw_anonymized.strip().splitlines()
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    raw_anonymized = "\n".join(lines)
                
                return raw_anonymized.strip()

            except Exception as e:
                import logging
                logging.getLogger("anonymizer").warning("LLM anonymization failed: %s. Falling back to regex anonymization.", e)

        # Fallback regex-based anonymization
        result = text

        # Patterns compiled in deterministic order
        for pattern, replacement in self._patterns:
            result = pattern.sub(replacement, result)

        # Aggressive heuristic: capitalized proper names
        if aggressive_names:
            result = self._apply_name_heuristic(result)

        return result

    def anonymize_text_with_mapping(
        self, text: str, aggressive_names: bool = False
    ) -> tuple[str, dict[str, Optional[str]]]:
        """
        Same as :meth:`anonymize_text` but returns a minimal mapping
        for internal re-identification in the backend (never exposed to AI).

        Returns:
            (anonymized_text, mapping_dict)
        """
        mapping: dict[str, Optional[str]] = {
            "patient_dni": self.cfg.patient_dni,
            "patient_full_name": self.cfg.patient_full_name,
            "doctor_full_name": self.cfg.doctor_full_name,
            "patient_dob": self.cfg.patient_dob,
        }
        return self.anonymize_text(text, aggressive_names=aggressive_names), mapping

    #  Name heuristic

    def _apply_name_heuristic(self, text: str) -> str:
        """Replaces sequences of capitalized words that look like names."""

        def _replace_name(match: re.Match) -> str:
            candidate = match.group(0)
            # Do not replace if it is a known medical acronym
            words = [w.strip().lower() for w in candidate.split()]
            if any(w in _MEDICAL_ACRONYMS for w in words):
                return candidate
            # Do not replace if it is at the beginning of a sentence (could be a common word)
            start = match.start()
            if start > 0 and text[start - 1] in ".\n\r":
                # Check if it is a common word
                first_word = words[0] if words else ""
                if first_word in _MEDICAL_ACRONYMS:
                    return candidate
            return self.replacements["generic_name"]

        return _NAME_HEURISTIC_PATTERN.sub(_replace_name, text)

    #  Utilities

    def stats(self, original: str, anonymized: str) -> dict[str, int]:
        """
        Returns quick statistics of how much the text has been modified.
        Useful for audit logging.
        """
        return {
            "original_length": len(original),
            "anonymized_length": len(anonymized),
            "reduction_chars": len(original) - len(anonymized),
            "tokens_replaced": original.count("[") - anonymized.count("["),
        }


#  Factory (with config.py)

def build_anonymizer_from_config(cfg) -> Anonymizer:
    """
    Creates an :class:`Anonymizer` from the project's :class:`Config` object.

    Reads from ``.env`` (recommended way: separate fields):
      * ``PATIENT_FIRST_NAME``, ``PATIENT_LAST_NAME1``, ``PATIENT_LAST_NAME2``
      * ``DOCTOR_FIRST_NAME``, ``DOCTOR_LAST_NAME1``, ``DOCTOR_LAST_NAME2``
      * Fallback: ``PATIENT_FULL_NAME``, ``DOCTOR_FULL_NAME``
    """
    return Anonymizer(
        AnonymizerConfig(
            patient_dni=getattr(cfg, "dicom_patient_id", None),
            patient_first_name=getattr(cfg, "patient_first_name", None),
            patient_last_name1=getattr(cfg, "patient_last_name1", None),
            patient_last_name2=getattr(cfg, "patient_last_name2", None),
            doctor_first_name=getattr(cfg, "doctor_first_name", None),
            doctor_last_name1=getattr(cfg, "doctor_last_name1", None),
            doctor_last_name2=getattr(cfg, "doctor_last_name2", None),
            patient_full_name=getattr(cfg, "patient_full_name", None),
            doctor_full_name=getattr(cfg, "doctor_full_name", None),
            hospital_name=getattr(cfg, "hospital_name", None),
            study_date=getattr(cfg, "study_date", None),
            patient_dob=getattr(cfg, "patient_dob", None),
            openai_api_key=getattr(cfg, "openai_api_key", None),
            openai_base_url=getattr(cfg, "openai_base_url", None),
            model_name=getattr(cfg, "agent_model_name", getattr(cfg, "model_name", None)),
        )
    )
