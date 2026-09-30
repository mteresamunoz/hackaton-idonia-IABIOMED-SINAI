"""
Recog API Client
Hackathon IABiomed 2026 — Equipo SINAI-UJA

Calls the Recog dictation endpoint to transform a medical report
into a patient-friendly PDF.
"""

import os
from pathlib import Path

import requests


class RecogClient:
    """
    Client for the Recog report humanization API.

    Usage:
        client = RecogClient(api_key="rrk_yourPublicId_yourSecret")
        pdf_bytes = client.humanize_report("Informe médico aquí...")
    """

    def __init__(self, api_key: str, base_url: str | None = None, endpoint: str | None = None):
        self.api_key = api_key
        self.base_url = (base_url or os.getenv("RECOG_BASE_URL", "https://api.recog.es")).rstrip("/")
        self.endpoint = endpoint or os.getenv("RECOG_ENDPOINT", "/relisten/dictation/process/report-results")

    def _get_headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
        }

    def humanize_report(self, report_text: str, timeout: int = 60) -> bytes:
        """
        POST /relisten/dictation/process/report-results

        Transforms a medical report into a patient-friendly PDF.

        Args:
            report_text: The medical report text (plain text, Spanish).
            timeout: Request timeout in seconds.

        Returns:
            Raw PDF bytes of the humanized report.

        Raises:
            requests.HTTPError: On 4xx/5xx responses with details.
        """
        resp = requests.post(
            f"{self.base_url}{self.endpoint}",
            headers=self._get_headers(),
            json={"dictationReport": report_text},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.content

    def humanize_and_save(
        self,
        report_text: str,
        output_path: str | Path = "informe_paciente.pdf",
        timeout: int = 60,
    ) -> Path:
        """
        Humanize a report and save the PDF to disk.

        Args:
            report_text: Medical report text.
            output_path: Where to save the resulting PDF.
            timeout: Request timeout in seconds.

        Returns:
            Path to the saved PDF.
        """
        pdf_bytes = self.humanize_report(report_text, timeout=timeout)
        output_path = Path(output_path)
        output_path.write_bytes(pdf_bytes)
        return output_path
