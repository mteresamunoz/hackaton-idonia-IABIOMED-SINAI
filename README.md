# Hackathon IABiomed 2026 — SINAI-UJA

> **Reto:** Interoperabilidad y humanización de la información médica  
> **Organiza:** Idonia + Recog — [IABiomed 2026](https://www.iabiomed.es/)

---

## El problema

Un montañero asturiano de Panes sufre una lesión de rodilla en los Picos de Europa. Lo trasladan al **Hospital de Sierrallana (Cantabria)** para cirugía y le realizan una **RM**. Una semana después vuelve a Asturias y su médico de cabecera necesita acceder a las imágenes y al informe. ¿Cómo conseguimos que esa información cruce fronteras regionales y sea comprensible para el paciente?

## Nuestra solución

Pipeline automatizado en **3 fases** que integra **Idonia Connect Cloud** (interoperabilidad), **Recog** (IA humanizadora) y un **sistema de resiliencia** (Qwen 3.6 vía LLM local):

1. **Ingesta** — Subimos el informe médico y la imagen del estudio a Idonia, simulando la recepción desde Cantabria.
2. **Humanización** — Extraemos el texto del informe con `docling` (incluso si está en formato imagen PNG/JPEG). Un **LLM multimodal** (`gemma-4-31B-it`) describe objetivamente la imagen médica (`RM_Rodilla.png`) y añade esa descripción al texto extraído. Luego enviamos el texto completo a la API de Recog y obtenemos un informe en lenguaje claro para el paciente. Lo subimos de nuevo a Idonia.
3. **Magic Link** — Generamos un enlace seguro con QR + PIN para que médico y paciente accedan desde cualquier dispositivo a ambos informes.
4. **(Nuevo) Resiliencia** — Si alguna fase falla por un error de red o de las APIs externas (timeout, 401, 503, etc.), el sistema **reintenta automáticamente** con backoff y, si persiste, un **agente LLM local** explica el problema al usuario en lenguaje sencillo y sugiere acciones concretas.

---

## Tecnologías

- **Python 3.10+**
- **Idonia Connect Cloud API** (JWT HS256, staging)
- **Recog API** (`api.recog.es/relisten/dictation/process/report-results`)
- **docling** — extracción de texto y estructura de PDFs médicos
- **requests** — cliente HTTP
- **openai** — cliente para los LLMs locales (OpenAI-compatible, vLLM)
- **Qwen 3.6-35B-A3B** — modelo de IA agentica para diagnóstico y resiliencia
- **gemma-4-31B-it** — modelo multilingüe y multimodal para traducción de informes y descripción de imágenes médicas
- **pdflatex / MiKTeX** — compilación de plantillas LaTeX a PDF para los informes traducidos

---

## Estructura del repositorio

```
├── .env.example              # Template de credenciales (copiar a .env)
├── requirements.txt
├── README.md
├── EXPLICACION.md            # Explicación del flujo para no técnicos
├── EVIDENCIAS.md             # Guía de evidencias para el entregable
│
├── src/
│   ├── config.py             # Carga variables de entorno desde .env
│   ├── idonia_client.py      # Cliente Idonia: JWT, upload, Magic Link
│   ├── recog_client.py       # Cliente Recog: humanización de informes
│   ├── multilingual_client.py # Cliente LLM multilingüe: traducción médica
│   ├── multimodal_client.py   # Cliente LLM multimodal: descripción de imágenes médicas
│   ├── latex_compiler.py     # Compila plantillas LaTeX a PDF
│   ├── anonymizer.py         # Anonimización RGPD: limpia PII antes de enviar a IA
│   ├── handle_errors.py      # Agente LLM: diagnóstico y resiliencia
│   ├── pipeline.py           # Orquesta las 3 fases del flujo
│   └── logging_config.py     # Logger por módulo (consola + archivos)
│
├── tests/
│   ├── test_connections.py   # Verifica JWT, Idonia, Recog y archivos
│   ├── test_llm.py           # Verifica conectividad con los LLMs (agente + multilingüe)
│   └── test_multilingual.py  # Verifica traducción y compilación LaTeX
│
├── Informes/                 # Archivos de prueba del caso médico
│   ├── Informe RM RODILLA.pdf       # Informe original (médico técnico)
│   ├── Informe RM a mano.png        # Informe escrito a mano (OCR con docling)
│   └── RM Rodilla.png               # Imagen del estudio (subida a Idonia)
│
├── output/                   # Generado en Fase II
│   └── Informe para paciente.pdf
│
└── logs/                     # Logs organizados por escenario
    ├── 01_pipeline_normal/
    ├── 02_docling_mano/
    ├── 03_errores_simulados/
    └── 04_tests/
```

---

## Setup rápido (Paso a Paso desde Cero)

Esta guía te guiará para configurar todo el entorno de ejecución desde cero. El pipeline requiere de un entorno en Python y de compilar la interfaz frontend.

### Paso 0: Requisitos Previos

Antes de empezar, asegúrate de tener instalado en tu sistema:
1. **Conda** o **Miniconda** (Recomendado para manejar el entorno de Python de forma aislada).
2. **Node.js** (versión 18+ recomendada) y **npm** (para compilar la interfaz de usuario).
3. **WSL** (si estás en Windows, ya que los comandos se ejecutan bajo este entorno).
4. **pdflatex** (opcional, solo si quieres generar informes en formato PDF multilingüe/LaTeX).
   - En WSL / Linux, para soportar los idiomas co-oficiales (Euskera, Catalán, Gallego) mediante LaTeX, debes instalar el soporte de idiomas europeo ejecutando:
     ```bash
     sudo apt-get update
     sudo apt-get install -y texlive-lang-european
     ```

---

### Paso 1: Configurar el Entorno de Python

Elige una de las siguientes opciones para aislar y configurar las dependencias del backend:

#### Opción A: Con Conda (Recomendado)

Esta opción crea un entorno virtual llamado `iabiomed` para evitar conflictos con otras versiones de Python y librerías que tengas instaladas.

1. **Crear el entorno Conda con Python 3.10**:
   Abre tu terminal (o terminal de WSL) y ejecuta:
   ```bash
   conda create -n iabiomed python=3.10 -y
   ```
   *¿Qué hace esto?* Descarga e instala una instalación limpia de Python 3.10 en un contenedor aislado llamado `iabiomed`.

2. **Activar el entorno recién creado**:
   ```bash
   conda activate iabiomed
   ```
   *¿Qué hace esto?* Cambia tu contexto de Python actual por el del entorno `iabiomed`. Verás que el prompt de tu terminal ahora comienza con `(iabiomed)`.

3. **Instalar las dependencias del backend**:
   Desde el directorio raíz del proyecto, ejecuta:
   ```bash
   pip install -r backend/requirements.txt
   ```
   *¿Qué hace esto?* Instala todas las librerías necesarias para el backend de Python (`FastAPI`, `uvicorn`, `docling`, `requests`, `openai`, etc.) dentro del entorno aislado.

---

#### Opción B: Con Python `venv` (Alternativa)

Si no tienes Conda, puedes usar el gestor de entornos nativo de Python:

1. **Crear el entorno virtual**:
   ```bash
   python3 -m venv .venv
   ```
2. **Activar el entorno**:
   - En Windows (Git Bash/CMD/VSCode): `source .venv/Scripts/activate`
   - En Linux / macOS / WSL: `source .venv/bin/activate`
3. **Instalar dependencias de Python**:
   ```bash
   pip install -r backend/requirements.txt
   ```

---

#### Opción C: Ejecución Automática por Script (Solo WSL/Linux)

Si usas WSL, puedes automatizar todo el Paso 1 y parte del Paso 2 ejecutando el script proporcionado en la raíz:
```bash
chmod +x setup_env.sh
./setup_env.sh
```
*¿Qué hace esto?* Detecta automáticamente Conda en tu sistema WSL, crea el entorno `iabiomed`, instala las dependencias mediante `pip install -r backend/requirements.txt` y copia la plantilla `.env.example` a `.env`.

---

### Paso 2: Configurar las Credenciales (.env)

El backend necesita conectarse a las APIs de Idonia, Recog y OpenAI/LLM. Para configurar tus claves:

1. **Copiar la plantilla del archivo de configuración**:
   Desde la raíz del proyecto, ejecuta:
   ```bash
   cp backend/.env.example backend/.env
   ```
2. **Editar las claves reales**:
   Abre el archivo `backend/.env` recién creado con tu editor de texto favorito (ej. VSCode, nano) y rellena los campos necesarios:
   - `IDONIA_API_KEY` y `IDONIA_API_SECRET`
   - `RECOG_API_KEY`
   - `OPENAI_API_KEY` (y `OPENAI_BASE_URL` si utilizas un servidor local/vLLM)
   - *Nota:* El archivo `.env` ya viene limpio y preconfigurado solo con las 12 variables principales indispensables.

---

### Paso 3: Instalar y Compilar el Frontend

La interfaz de usuario está desarrollada en React + Vite. Para servirla, primero debemos compilar los archivos estáticos:

1. **Entrar al directorio del frontend e instalar las dependencias de Node**:
   ```bash
   cd frontend
   npm install
   ```
2. **Compilar el frontend para producción**:
   ```bash
   npm run build
   ```
   *¿Qué hace esto?* Crea una carpeta `frontend/dist` con el código HTML, CSS y JS optimizado que el servidor backend de FastAPI servirá automáticamente.
3. **Regresar al directorio raíz del proyecto**:
   ```bash
   cd ..
   ```

---

### Paso 4: Verificar que todo funcione

Antes de arrancar la aplicación, es recomendable ejecutar las pruebas de conexión para asegurarte de que las credenciales del `.env` y las llamadas a las APIs externas funcionan correctamente.

Con tu entorno virtual/Conda activado (`conda activate iabiomed`), ejecuta desde la raíz:
```bash
python3 tests/test_connections.py
python3 tests/test_multilingual.py
```

> **Nota:** Para compilar informes en formato PDF multilingües, necesitarás tener instalado `pdflatex` (por ejemplo, [MiKTeX](https://miktex.org/download) en Windows o TeX Live en Linux/Mac).

**Resultado esperado al verificar conexiones:**
```
[1] JWT Generation
  ✅ Generar JWT para Idonia

[2] Idonia API
  ✅ GET /whoami → Idonia Connect Cloud

[3] Recog API
  ✅ POST /report-results → Recog (informe de prueba)

[4] PDF del informe
  ✅ Informe_RM_RODILLA.pdf encontrado en Informes/

[5] Imagen del estudio
  ✅ RM_Rodilla.png encontrado en Informes/

Resultado: 5/5 checks pasados
✅ Todo listo para ejecutar el pipeline o arrancar el servidor web.
```

---

## Uso del pipeline

### Fase a fase (recomendado para pruebas)

```bash
# Fase I — Subir el informe PDF original a Idonia
python src/pipeline.py --phase 1

# Fase II — Humanizar con Recog y subir el informe para paciente
python src/pipeline.py --phase 2

# Fase III — Generar Magic Link (QR + PIN)
python src/pipeline.py --phase 3
```

### Todo de una vez

```bash
python src/pipeline.py
```

### Guardar logs en carpeta personalizada

Útil para organizar evidencias por escenario:

```bash
python src/pipeline.py --log-dir logs/01_pipeline_normal
```

### Procesar un informe en formato imagen (PNG/JPEG)

```bash
python src/pipeline.py --phase 2 --report-path "Informes/Informe RM a mano.png"
```

### Con resiliencia automática (reintentos + agente LLM)

Si una fase falla por un error de red o de las APIs externas, activa `--auto-fix`:

```bash
python src/pipeline.py --auto-fix
```

Esto hará dos cosas:
1. **Reintentos automáticos** con backoff para errores temporales (timeout, 503, etc.).
2. Si persiste, el **agente LLM** explica el problema en lenguaje sencillo y sugiere acciones concretas.

### Simular errores de API (modo prueba del agente)

Puedes forzar errores reales de red/API para ver cómo reacciona el sistema:

```bash
# Fuerza timeout de Idonia (error de red)
python src/pipeline.py --simulate-error 1 --auto-fix

# Fuerza 401 Unauthorized (credenciales inválidas)
python src/pipeline.py --simulate-error 2 --auto-fix

# Fuerza 503 Service Unavailable (servidor sobrecargado)
python src/pipeline.py --simulate-error 3 --auto-fix

# Fuerza error de conexión con Recog
python src/pipeline.py --simulate-error 4 --auto-fix
```

### Multilingüe — Informes en lenguas co-oficiales de España

El pipeline soporta **Castellano, Catalán, Valenciano, Gallego y Euskera**. Recog siempre genera el informe base en español. Si el usuario solicita otro idioma, un LLM multilingüe (`gemma-4-31B-it`) traduce el contenido y rellena una plantilla LaTeX que se compila a PDF.

**Requisito:** tener instalado [MiKTeX](https://miktex.org/download) (Windows) o TeX Live.

```bash
# Solo español (comportamiento por defecto)
python src/pipeline.py --phase 2 --language es

# Español + Catalán
python src/pipeline.py --phase 2 --language ca --log-dir logs/multilingue_ca

# Español + Valenciano
python src/pipeline.py --phase 2 --language va --log-dir logs/multilingue_va

# Español + Gallego
python src/pipeline.py --phase 2 --language gl --log-dir logs/multilingue_gl

# Español + Euskera
python src/pipeline.py --phase 2 --language eu --log-dir logs/multilingue_eu

# Pipeline completo en catalán (con resiliencia)
python src/pipeline.py --auto-fix --language ca

# Informe original en euskera → salida en español + catalán
```

---

## Ejecución de la Interfaz Web (API y Frontend)

La aplicación web puede ejecutarse en dos modalidades: **Unificada** (un único servidor sirve el frontend y la API) o **Separada** (ideal para desarrollo de frontend con recarga en vivo).

### Opción 1: Ejecución Unificada (Recomendada)
El servidor backend de FastAPI está configurado para servir automáticamente los archivos estáticos del frontend (`frontend/dist`) desde la ruta raíz `/`. Solo necesitas iniciar el backend:

1. **Activar el entorno virtual o de Conda** (ej. Conda):
   ```bash
   conda activate iabiomed
   ```
2. **Iniciar el servidor FastAPI desde el directorio raíz**:
   ```bash
   # Asegúrate de estar en el directorio raíz del proyecto
   python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
   ```
3. **Acceder a la aplicación**: Abre tu navegador e ingresa a `http://localhost:8000`.

---

### Opción 2: Ejecución Separada (Modo Desarrollo)
Si estás realizando modificaciones en el frontend de React y deseas actualizaciones automáticas (hot-reload):

1. **Arrancar el Backend**:
   ```bash
   conda activate iabiomed
   # Desde el directorio raíz
   python -m uvicorn backend.main:app --reload --port 8000
   ```
2. **Arrancar el Frontend (Vite)**:
   En otra pestaña del terminal:
   ```bash
   cd frontend
   npm run dev
   ```
3. **Acceder a la aplicación**: Abre tu navegador e ingresa a `http://localhost:5173`. Las peticiones se redirigirán dinámicamente al backend en el puerto `8000` sin conflictos de CORS.

---

## Qué hace cada fase

### Fase I — Ingesta (Interoperabilidad)
```
GET  /whoami        → verifica que el JWT es válido
POST /files/report_hak_<num> → sube Informe_RM_RODILLA.pdf
                                 a <DNI>/Traslados desde Asturias/RM-RODILLA-2026
POST /files/dicom_hak_<num>  → sube RM_Rodilla.png (imagen del estudio)
                                 a la misma carpeta del paciente
```

### Fase II — Humanización (IA)
```
docling             → extrae el texto del informe (PDF, PNG, JPEG, etc.)
LLM multimodal      → describe objetivamente la imagen médica (RM_Rodilla.png)
POST api.recog.es/relisten/dictation/process/report-results → PDF humanizado
POST /files/report_hak_<num> → sube "Informe para paciente.pdf"
                                 a <DNI>/Traslados desde Asturias/RM-RODILLA-2026

Si --language != es:
  docling           → extrae texto del PDF español generado por Recog
  LLM multilingüe   → traduce el contenido a ca/gl/eu
  Plantilla LaTeX   → rellena con el texto traducido
  pdflatex          → compila a PDF
  POST /files/...   → sube "Informe para paciente (CA/GL/EU).pdf"
  NOTA: el informe base en español siempre se sube como "Informe para paciente.pdf" (sin sufijo).
```

> **Nota sobre formatos:** docling puede extraer texto no solo de PDFs, sino también de **imágenes** (PNG, JPEG, etc.) usando OCR nativo. Esto permite humanizar incluso informes escaneados o escritos a mano.

> **Nota sobre descripción de imagen:** si se activa con `--imagen`, un modelo multimodal (`gemma-4-31B-it`) analiza la imagen del estudio (`RM_Rodilla.png`) y genera una descripción objetiva de lo visible (anatomía, contraste, planos). Esta descripción se añade al final del texto extraído bajo el epígrafe `DESCRIPCIÓN DE LA IMAGEN:`, enriqueciendo el informe humanizado con contexto visual sin inventar diagnósticos.

> **Nota multilingüe:** Recog genera el informe siempre en español. Si el usuario solicita otro idioma, un modelo LLM multilingüe (`gemma-4-31B-it`) traduce el contenido del PDF español y rellena la plantilla LaTeX `Plantilla_latex/informe_resultados.tex`, que luego se compila con `pdflatex`.

### Fase III — Magic Link
```
PUT /ml?route=<DICOMPatientID>/<DICOMAccessionNumber>/<DICOMStudyDescription>
→ genera { url, pin }
→ Médico y paciente acceden desde cualquier dispositivo
   a informe médico + informe humanizado
```

---

## Anonimización y cumplimiento RGPD

Antes de que el texto del informe salga hacia las APIs de IA (Recog, Gemma, Qwen), el sistema **anonimiza automáticamente** cualquier dato personal identificable (PII) mediante el módulo `src/anonymizer.py`.

### ¿Por qué es necesario?

- **Idonia** es una infraestructura médica segura: necesita el DNI real para crear carpetas DICOM.
- **Recog y los LLMs** procesan el texto del informe. Enviar nombres, DNI, direcciones o teléfonos a estas APIs externas sería una **violación del RGPD**.
- **Solución:** el backend separa el flujo en dos canales:
  - **Canal A (Seguro / Idonia):** mantiene DNI, nombres y datos reales intactos.
  - **Canal B (Anónimo / IA):** el texto se limpia de PII antes de llegar a Recog o a los LLMs.

### ¿Qué se anonimiza?

| Dato | ¿Cómo? | Ejemplo |
|------|--------|---------|
| DNI / NIE | Regex genérico + DNI específico del `.env` | `12345678A` → `[DNI_OCULTO]` |
| Nombre del paciente | Regex específico + variantes OCR | `García López, Antonio` → `[PACIENTE_DESIDENTIFICADO]` |
| Nombre del médico | Regex específico + variantes OCR | `P. Martínez` → `[MEDICO_DESIDENTIFICADO]` |
| Hospital | Regex específico del `.env` | `Hospital San José` → `[HOSPITAL_OCULTO]` |
| Fecha del estudio | Regex específica del `.env` | `21/05/2025` → `[FECHA_ESTUDIO_OCULTA]` |
| Teléfonos | Regex genérico | `912345678` → `[TELEFONO_OCULTO]` |
| Emails | Regex genérico | `juan@email.com` → `[EMAIL_OCULTO]` |
| Nº Historia Clínica (NHC) | Regex genérico | `Nº Historia: 3245678` → `[HISTORIA_OCULTA]` |
| Nº Volante / Informe | Regex genérico | `Nº Volante: RM-25/1987` → `[VOLANTE_OCULTO]` |
| Dirección postal | Regex genérico (tipo de vía + CP) | `Av.Constitucion,45 28015Madrid` → `[DIRECCION_OCULTA]` |

### Variables de entorno relacionadas

**Forma RECOMENDADA (campos separados):** el motor genera automáticamente todas las combinaciones posibles (iniciales, sin tildes, mayúsculas, formato médico/natural...) para cubrir errores de OCR.

```bash
# ── Paciente ──────────────────────────────────────
PATIENT_FIRST_NAME=Antonio            # Nombre (o inicial: A.)
PATIENT_LAST_NAME1=García             # Primer apellido
PATIENT_LAST_NAME2=López              # Segundo apellido (opcional)

# ── Médico ────────────────────────────────────────
DOCTOR_FIRST_NAME=P.                  # Nombre o inicial (P. → detecta Pilar, Pedro...)
DOCTOR_LAST_NAME1=Martínez            # Primer apellido
DOCTOR_LAST_NAME2=                    # Segundo apellido (opcional)

# ── Otros datos opcionales ────────────────────────
HOSPITAL_NAME=Hospital San José       # Centro de salud
STUDY_DATE=21/05/2025                 # Fecha del estudio
PATIENT_DOB=                          # Fecha de nacimiento (opcional)

# Fallback (solo si NO usas los campos separados):
# PATIENT_FULL_NAME=García López, Antonio
# DOCTOR_FULL_NAME=P. Martínez
```

**Importante:** las variables de arriba son **opcionales** pero recomendadas. Incluso sin ellas, el motor detecta automáticamente DNI, teléfonos, emails, NHC, volantes y direcciones postales.

### Archivos de auditoría

Durante la Fase II se generan dos archivos:

| Archivo | Canal | Descripción |
|---------|-------|-------------|
| `logs/.../texto_extraido_original.txt` | **A** | Texto crudo con datos personales intactos (auditoría interna) |
| `logs/.../texto_extraido.txt` | **B** | Texto limpio con tokens de reemplazo (enviado a IA) |

> `texto_extraido_original.txt` **nunca sale del backend**. Solo se usa para trazabilidad y cumplimiento normativo.

### Modo agresivo (heurística de nombres)

Si el informe contiene nombres de familiares, médicos de guardia o terceros que no están en `.env`, puedes activar la heurística de nombres propios (detecta secuencias de 2-4 palabras capitalizadas):

```bash
# Aún no expuesto como flag CLI; se activa en código:
anonymizer.anonymize_text(text, aggressive_names=True)
```

> ⚠️ Puede generar falsos positivos con acrónimos médicos (RM, TC, TAC...). Por eso está desactivado por defecto.

---

## Agente de resiliencia y diagnóstico (LLM)

Además de las 3 fases del pipeline, hemos incorporado un **sistema de resiliencia** que actúa cuando las APIs externas fallan.

### ¿Qué hace?

Cuando una fase lanza un error de red o de API (timeout, 401, 503, connection error, etc.), el sistema reacciona automáticamente si se activó con `--auto-fix`:

1. **Reintentos automáticos** — Para errores temporales (timeout, 503, connection error), el sistema espera unos segundos y vuelve a intentarlo hasta 3 veces con backoff exponencial.
2. **Diagnóstico inteligente** — Si el error persiste, consulta al modelo local **Qwen 3.6-35B-A3B**  para generar un mensaje amigable que explique al usuario no experto qué pasó y qué puede hacer. El agente responde en el idioma seleccionado por el usuario (`--language`).
3. **Sugerencias concretas** — El agente propone acciones reales que el usuario puede tomar: revisar credenciales, esperar unos minutos si el servidor está caído, contactar con soporte, etc.

### ¿Qué NO hace?

- **No modifica código fuente**. El agente no toca archivos `.py`. Su trabajo es ayudar al usuario a entender y resolver problemas de infraestructura/API, no corregir bugs de programación.

### ¿Cómo funciona por dentro?

```
Fase X falla (timeout/503/401)
    │
    ▼
¿Es un error temporal?
    ├── Sí  → Reintenta automáticamente (backoff)
    │             └── Funciona → continúa pipeline
    └── No / sigue fallando
        │
        ▼
    handle_errors.py
        │
        ├── Prompt al LLM: tipo de error + endpoint + traceback
        │
        ▼
       Qwen
        │
        ├── Devuelve: mensaje amigable + análisis técnico + acciones sugeridas
        │
        ▼
    Muestra al usuario qué pasó y qué hacer
```

### Variables de entorno del agente

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `OPENAI_API_KEY` | API key para vLLM (puede ser dummy) | `sk-no-key` |
| `OPENAI_BASE_URL` | URL del servidor vLLM local | `http://ada01.ujaen.es:8080/v1` |
| `AGENT_MODEL_NAME` | Modelo para diagnóstico de errores | `Qwen3.6-35B-A3B` |
| `MULTILINGUAL_MODEL_NAME` | Modelo para traducción de informes y descripción de imágenes | `gemma-4-31B-it` |

---

## Opciones avanzadas del pipeline

| Flag | Descripción | Ejemplo |
|------|-------------|---------|
| `--phase 1/2/3` | Ejecutar solo una fase | `python src/pipeline.py --phase 2` |
| `--log-dir PATH` | Guardar logs en carpeta personalizada | `python src/pipeline.py --log-dir logs/mi_ejecucion` |
| `--report-path PATH` | Usar otro informe (PDF o imagen) | `python src/pipeline.py --report-path "Informes/mi_informe.png"` |
| `--language es/ca/va/gl/eu` | Idioma adicional para el informe humanizado | `python src/pipeline.py --language ca` |
| `--imagen` | Activa la descripción de la imagen médica con LLM multimodal | `python src/pipeline.py --phase 2 --imagen` |
| `--auto-fix` | Activar reintentos + diagnóstico LLM | `python src/pipeline.py --auto-fix` |
| `--simulate-error N` | Forzar error de API (1-4) | `python src/pipeline.py --simulate-error 1 --auto-fix` |

---

## Datos del caso de uso

| Campo | Valor |
|-------|-------|
| Paciente | PRUEBA RODILLA, PACIENTE |
| DNI (ficticio) | `12345678A` (configurable en `.env`) |
| Hospital origen | Hospital de Sierrallana (Cantabria) |
| Hospital destino | Consultorio de Panes (Asturias) |
| Prueba | RM RODILLA DERECHA |
| Prescriptor | PRUEBA PRESCRIPTOR, MÉDICO/TRAUMATOLOGÍA |

**Jerarquía DICOM en Idonia** :

| Campo DICOM | Valor | Significado visual en Idonia |
|-------------|-------|------------------------------|
| `DICOMPatientID` | `12345678A` | Carpeta raíz del paciente |
| `DICOMAccessionNumber` | `Traslados desde Asturias` | Subcarpeta / categoría |
| `DICOMStudyDescription` | `RM-RODILLA-2026` | Descripción del estudio |

> Resultado: el paciente ve `12345678A > Traslados desde Asturias > RM-RODILLA-2026`

---

## Equipo

**SINAI-UJA** — Universidad de Jaén

