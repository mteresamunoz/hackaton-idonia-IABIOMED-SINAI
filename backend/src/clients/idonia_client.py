"""
Idonia Connect Cloud API Client
IABiomed Hackathon 2026 — Team SINAI-UJA

Real endpoints (from official manual):
  GET  /whoami                              → verify JWT
  POST /files/report_hak_<num>             → upload PDF report
  POST /files/dicom_hak_<num>              → upload DICOM/JPEG image
  GET  /ml?route=<route>                    → get existing Magic Link
  PUT  /ml?route=<route>                    → create Magic Link

Routes in Idonia (manual section 5 and 6):
  Files (/file, /report, /dicom):
    <DICOMPatientID>/<DICOMAccessionNumber>/<DICOMStudyDescription>
  Magic Link (/ml):
    <DICOMPatientID>/<DICOMAccessionNumber>
"""

import base64
import hashlib
import hmac
import json
import time
import urllib.parse

import requests


BASE_URL = "https://connect-staging.idonia.com"


# JWT

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _decode_api_secret(api_secret: str) -> bytes:
    """
    Decodes the Idonia APISecret (manual section 4.1):
    1. Truncate prefix 'S2'
    2. Replace '-' with '+' and '_' with '/' (urlsafe → standard base64)
    3. Decode base64
    """
    without_prefix = api_secret[2:]
    standard_b64 = without_prefix.replace("-", "+").replace("_", "/")
    padding = 4 - len(standard_b64) % 4
    if padding != 4:
        standard_b64 += "=" * padding
    return base64.b64decode(standard_b64)


def generate_jwt(api_key: str, api_secret: str) -> str:
    """
    Generates HS256 JWT for Idonia.
    iat = now - 5min, exp = now + 5min (recommended by the manual).
    """
    now = int(time.time())
    header  = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": api_key, "iat": now - 300, "exp": now + 300}

    h = _b64url_encode(json.dumps(header,  separators=(",", ":")).encode())
    p = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())

    secret   = _decode_api_secret(api_secret)
    sig      = hmac.new(secret, f"{h}.{p}".encode(), hashlib.sha256).digest()
    return f"{h}.{p}.{_b64url_encode(sig)}"


# Client

class IdoniaClient:
    """
    Client for Idonia Connect Cloud REST API.

    DICOM route parameters (manual section 5 and 6):
      dicom_patient_id     → patient folder (e.g. "12345678A")
      dicom_accession_num  → category / subfolder (e.g. "Transfers from Asturias")
      dicom_study_desc     → study description (e.g. "MRI-KNEE-2026")

    File path (uploads, /file):
      <dicom_patient_id>/<dicom_accession_num>/<dicom_study_desc>

    Magic Link route (/ml):
      <dicom_patient_id>/<dicom_accession_num>
    """

    def __init__(self, api_key: str, api_secret: str, num_participante: str,
                 base_url: str = BASE_URL):
        self.api_key         = api_key
        self.api_secret      = api_secret
        self.num_participante = num_participante
        self.base_url        = base_url.rstrip("/")

    def _headers(self, content_type: str | None = "application/json") -> dict:
        h = {"Authorization": f"Bearer {generate_jwt(self.api_key, self.api_secret)}"}
        if content_type:
            h["Content-Type"] = content_type
        return h

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    # Health / Auth

    def whoami(self) -> dict:
        """GET /whoami — verifies JWT and returns identity."""
        resp = requests.get(self._url("/whoami"), headers=self._headers(), timeout=30)
        resp.raise_for_status()
        return resp.json()

    # Phase I: Upload PDF report

    def upload_report(
        self,
        pdf_path,
        dicom_patient_id: str,
        dicom_accession_num: str,
        dicom_study_desc: str,
    ) -> dict:
        """
        POST /files/report_hak_<num_participante>

        Uploads a PDF report to Idonia (manual section 6.2).
        Response 201 with array of file_uuid.

        Args:
            pdf_path: local path to the PDF.
            dicom_patient_id: patient folder in Idonia (e.g. "12345678A").
            dicom_accession_num: category / subfolder (e.g. "Transfers from Asturias").
            dicom_study_desc: study description (e.g. "MRI-KNEE-2026").
        """
        from pathlib import Path
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF no encontrado: {pdf_path}")

        endpoint = f"/files/report_hak_{self.num_participante}"

        resp = requests.post(
            self._url(endpoint),
            headers=self._headers(content_type=None),  # multipart sets its own
            files={"file": (pdf_path.name, pdf_path.open("rb"), "application/pdf")},
            data={
                "DICOMPatientID":      dicom_patient_id,
                "DICOMAccessionNumber": dicom_accession_num,
                "DICOMStudyDescription": dicom_study_desc,
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()

    # Phase I: Upload DICOM/JPEG image

    def upload_dicom(
        self,
        image_path,
        dicom_patient_id: str,
        dicom_accession_num: str,
        dicom_study_desc: str,
    ) -> dict:
        """
        POST /files/dicom_hak_<num_participante>

        Uploads a DICOM or JPEG image to Idonia (manual section 6.3).
        Response 201 with array of file_uuid.
        """
        from pathlib import Path
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Imagen no encontrada: {image_path}")

        suffix = image_path.suffix.lower()
        if suffix == ".dcm":
            mime = "application/dicom"
        elif suffix == ".png":
            mime = "image/png"
        else:
            mime = "image/jpeg"
        endpoint = f"/files/dicom_hak_{self.num_participante}"

        resp = requests.post(
            self._url(endpoint),
            headers=self._headers(content_type=None),
            files={"file": (image_path.name, image_path.open("rb"), mime)},
            data={
                "DICOMPatientID":        dicom_patient_id,
                "DICOMAccessionNumber":  dicom_accession_num,
                "DICOMStudyDescription": dicom_study_desc,
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()

    # Phase II: Upload humanized report

    def upload_patient_report(
        self,
        pdf_bytes: bytes,
        dicom_patient_id: str,
        dicom_accession_num: str,
        dicom_study_desc: str,
        filename: str = "Informe para paciente.pdf",
    ) -> dict:
        """
        POST /files/report_hak_<num_participante>

        Uploads the humanized PDF generated by Recog to Idonia.
        Same endpoint as upload_report but receives bytes directly.
        """
        endpoint = f"/files/report_hak_{self.num_participante}"

        resp = requests.post(
            self._url(endpoint),
            headers=self._headers(content_type=None),
            files={"file": (filename, pdf_bytes, "application/pdf")},
            data={
                "DICOMPatientID":        dicom_patient_id,
                "DICOMAccessionNumber":  dicom_accession_num,
                "DICOMStudyDescription": dicom_study_desc,
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()

    # Phase III: Magic Link

    def get_or_create_magic_link(
        self,
        dicom_patient_id: str,
        dicom_accession_num: str,
        dicom_study_desc: str,
        password: str | None = None,
    ) -> dict:
        """
        PUT /ml?route=<DICOMPatientID>/<DICOMAccessionNumber>

        Creates the Magic Link on the parent folder of the study.
        According to the Idonia manual (section 6.4), the route must be 2 levels:
          <DICOMPatientID>/<DICOMAccessionNumber>
        (Does NOT include <DICOMStudyDescription>, which only applies to /file files).

        The final URL for the patient will be:
          https://demo.idonia.com/v/<num_participante>
        And it will be accompanied by the PIN returned by the API.

        Args:
            dicom_patient_id: patient folder.
            dicom_accession_num: study category / subfolder (container level).
            dicom_study_desc: study description (kept for client API consistency,
                              but not used in the ML route).
            password: optional password (automatically hashed SHA256 → base64).

        Returns:
            Dict with 'URL', 'PIN' and optionally 'is_expired'.
        """
        # Manual section 6.4: Magic Link route = 2 levels (Patient / Study)
        route = f"{dicom_patient_id}/{dicom_accession_num}"
        params = {"route": route}

        if password:
            sha256_hash = hashlib.sha256(password.encode()).hexdigest()
            params["password"] = base64.b64encode(sha256_hash.encode()).decode()

        resp = requests.put(
            self._url("/ml"),
            headers=self._headers(),
            params=params,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        # API returns an array → get the first element
        if isinstance(data, list):
            data = data[0]

        # Build complete Magic Link URL using the value returned by the API
        # The manual (section 6.4.1) indicates that the response contains "URL": "<num_participante>"
        url_suffix = data.get("URL") or self.num_participante
        data["magic_link_url"] = f"https://demo.idonia.com/v/{url_suffix}"
        return data

    # Utility: Get document

    def get_document(
        self,
        dicom_patient_id: str,
        dicom_accession_num: str,
        dicom_study_desc: str,
    ) -> bytes:
        """
        GET /file?route=<urlsafe_route>

        Downloads a document from Idonia by its route (manual section 6.5).
        """
        route = f"{dicom_patient_id}/{dicom_accession_num}/{dicom_study_desc}"
        safe_route = urllib.parse.quote(route, safe="")

        resp = requests.get(
            self._url("/file"),
            headers=self._headers(),
            params={"route": safe_route},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.content