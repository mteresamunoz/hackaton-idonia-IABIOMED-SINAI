#!/bin/bash
# Script para configurar el entorno Conda y las dependencias de la aplicación.
# Debe ejecutarse en WSL.

set -e

echo "=========================================================="
echo "   Configurando Entorno Conda para IABiomed (SINAI-UJA)"
echo "=========================================================="

# Inicializar conda para el shell actual
# conda suele estar configurado en ~/.bashrc
if [ -f ~/.bashrc ]; then
    source ~/.bashrc
fi

# Intentar detectar si conda está disponible
if ! command -v conda &> /dev/null; then
    echo "⚠️  No se encontró el comando 'conda' en el PATH actual."
    echo "Intentando cargar conda desde las rutas por defecto..."
    if [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
        source "$HOME/miniconda3/etc/profile.d/conda.sh"
    elif [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
        source "$HOME/anaconda3/etc/profile.d/conda.sh"
    elif [ -f "/opt/conda/etc/profile.d/conda.sh" ]; then
        source "/opt/conda/etc/profile.d/conda.sh"
    else
        echo "❌ No se pudo encontrar conda. Por favor, asegúrate de que Conda está instalado en WSL."
        exit 1
    fi
fi

echo "✅ Conda detectado correctamente."

# Crear entorno conda si no existe
ENV_NAME="iabiomed"
if conda env list | grep -q "$ENV_NAME"; then
    echo "🔄 El entorno Conda '$ENV_NAME' ya existe. Saltando creación."
else
    echo "📦 Creando entorno Conda '$ENV_NAME' con Python 3.10..."
    conda create -n "$ENV_NAME" python=3.10 -y
fi

# Inicializar conda en este script
eval "$(conda shell.bash hook)"

echo "🔄 Activando entorno Conda '$ENV_NAME'..."
conda activate "$ENV_NAME"

echo "📥 Instalando dependencias de Python desde backend/requirements.txt..."
# Usamos pip dentro de conda para instalar los paquetes requeridos
pip install -r backend/requirements.txt

# Configurar el archivo .env si no existe
if [ ! -f "backend/.env" ]; then
    echo "📝 Archivo backend/.env no encontrado. Creando copia desde .env.example..."
    cp backend/.env.example backend/.env
    echo "⚠️  Recuerda editar backend/.env con tus claves reales de Idonia, Recog y OpenAI/LLM."
else
    echo "✅ Archivo backend/.env ya existe."
fi

echo "=========================================================="
echo "🎉 ¡Configuración completada con éxito!"
echo "Para activar el entorno ejecuta: conda activate $ENV_NAME"
echo "Para iniciar el backend ejecuta: python -m uvicorn backend.main:app --reload --port 8000"
echo "Para iniciar el frontend ejecuta: cd frontend && npm run dev"
echo "=========================================================="
