"""
LaTeX Compiler Helper — Hackathon IABiomed 2026 — SINAI-UJA

Compiles LaTeX code to PDF using pdflatex/xelatex.
It is assumed that MiKTeX or TeX Live is installed and available in PATH,
or that WSL (Windows Subsystem for Linux) has TeX Live installed as fallback.
"""

import shutil
import subprocess
from pathlib import Path
from typing import Optional


def _find_latex_compiler(compiler_path: Optional[Path] = None) -> Optional[str]:
    """Searches for pdflatex or xelatex in PATH, in the configured path, and in common locations."""
    # 1. If the user configured an explicit path, search there first
    if compiler_path:
        for compiler in ("pdflatex.exe", "xelatex.exe", "pdflatex", "xelatex"):
            candidate = Path(compiler_path) / compiler
            if candidate.exists():
                return str(candidate)

    # 2. Search in PATH
    for compiler in ("pdflatex", "xelatex"):
        if shutil.which(compiler):
            return compiler

    # 3. Search in common locations of MiKTeX / TeX Live (Windows)
    common_paths = [
        Path.home() / "AppData" / "Local" / "Programs" / "MiKTeX" / "miktex" / "bin" / "x64",
        Path.home() / "AppData" / "Local" / "Programs" / "MiKTeX" / "miktex" / "bin",
        Path("C:/Program Files/MiKTeX/miktex/bin/x64"),
        Path("C:/Program Files/MiKTeX/miktex/bin"),
        Path("C:/Program Files (x86)/MiKTeX/miktex/bin"),
        Path("C:/texlive/2024/bin/windows"),
        Path("C:/texlive/2023/bin/windows"),
    ]
    for compiler in ("pdflatex.exe", "xelatex.exe"):
        for folder in common_paths:
            candidate = folder / compiler
            if candidate.exists():
                return str(candidate)
    return None


def _windows_path_to_wsl(path: Path) -> str:
    """Converts a Windows path (C:\\foo\\bar) to a WSL path (/mnt/c/foo/bar)."""
    path = Path(path).resolve()
    # path.drive is like 'C:' on Windows
    drive = path.drive.rstrip(":").lower()
    # path.as_posix() gives C:/foo/bar — strip the drive prefix
    posix = path.as_posix()
    # Remove 'C:/' prefix → 'foo/bar'
    rest = posix[len(path.drive) + 1:]  # skip 'C:/'
    return f"/mnt/{drive}/{rest}"


def _check_wsl_pdflatex() -> bool:
    """Returns True if pdflatex is available inside WSL."""
    try:
        result = subprocess.run(
            ["wsl", "which", "pdflatex"],
            capture_output=True, text=True, timeout=10,
        )
        return result.returncode == 0 and result.stdout.strip() != ""
    except Exception:
        return False


def compile_latex(
    latex_code: str,
    output_pdf: Path,
    compiler: Optional[str] = None,
    compiler_path: Optional[Path] = None,
    clean_aux: bool = True,
) -> Path:
    """
    Compiles LaTeX code to PDF.

    Args:
        latex_code: Full LaTeX code.
        output_pdf: Destination path of the PDF (e.g.: output/Informe_para_paciente_CA.pdf).
        compiler: Compiler to use (pdflatex/xelatex). If None, searches in PATH.
        compiler_path: Path to the directory where the compiler is located. If provided,
                       it searches there first. Can come from the LATEX_COMPILER_PATH environment variable in .env.
        clean_aux: If True, deletes auxiliary files (.aux, .log, .out) after compiling.

    Returns:
        Path to the generated PDF.

    Raises:
        RuntimeError: If the compiler is not found or compilation fails.
    """
    output_pdf = Path(output_pdf)
    output_dir = output_pdf.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    tex_name = output_pdf.stem + ".tex"
    tex_path = output_dir / tex_name

    # Write the .tex
    tex_path.write_text(latex_code, encoding="utf-8")

    # Search for native Windows compiler first
    latex_bin = compiler or _find_latex_compiler(compiler_path=compiler_path)

    # Fallback: use WSL pdflatex if no native compiler found
    use_wsl = False
    if not latex_bin:
        if _check_wsl_pdflatex():
            use_wsl = True
        else:
            raise RuntimeError(
                "No se encontró pdflatex ni xelatex en PATH ni en WSL.\n"
                "Por favor instala MiKTeX (Windows) o TeX Live (Linux/Mac):\n"
                "  https://miktex.org/download\n"
                "O instala TeX Live en WSL: sudo apt-get install texlive-full"
            )

    # Build the command
    if use_wsl:
        # Convert Windows paths to WSL paths so Linux pdflatex can read them
        wsl_tex_path = _windows_path_to_wsl(tex_path)
        wsl_output_dir = _windows_path_to_wsl(output_dir)
        cmd = [
            "wsl", "pdflatex",
            "-interaction=nonstopmode",
            "-halt-on-error",
            f"-output-directory={wsl_output_dir}",
            wsl_tex_path,
        ]
    else:
        cmd = [
            latex_bin,
            "-interaction=nonstopmode",
            "-halt-on-error",
            f"-output-directory={output_dir}",
            str(tex_path),
        ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.returncode != 0 or not output_pdf.exists():
        # Save error log for debugging
        log_path = output_dir / (output_pdf.stem + ".log")
        log_content = result.stdout + "\n--- STDERR ---\n" + result.stderr
        if log_path.exists():
            log_content = log_path.read_text(encoding="utf-8", errors="replace")
        raise RuntimeError(
            f"La compilación LaTeX falló (código {result.returncode}).\n"
            f"Compilador: {'wsl pdflatex' if use_wsl else latex_bin}\n"
            f"Archivo: {tex_path}\n"
            f"Log:\n{log_content[:2000]}"
        )

    # Clean up auxiliaries
    if clean_aux:
        for ext in (".aux", ".log", ".out", ".tex"):
            aux = output_dir / (output_pdf.stem + ext)
            if aux.exists() and ext != ".tex":
                aux.unlink()
            # Also clean up the intermediate .tex if desired
            # if ext == ".tex":
            #     aux.unlink()

    return output_pdf
