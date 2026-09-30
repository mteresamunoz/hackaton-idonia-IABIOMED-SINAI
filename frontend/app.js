// Frontend Logic — Hackathon IABiomed 2026 — SINAI-UJA

document.addEventListener("DOMContentLoaded", () => {
    // --- Elements ---
    const btnProcess = document.getElementById("btn-process");
    const btnText = btnProcess.querySelector(".btn-text");
    const btnLoader = btnProcess.querySelector(".btn-loader");
    
    // Unified File input & Dropzone
    const filesInput = document.getElementById("files-input");
    const filesDropzone = document.getElementById("files-dropzone");
    const filesListContainer = document.getElementById("files-list");
    
    // Inputs Config
    const languageSelect = document.getElementById("language-select");
    const describeImageToggle = document.getElementById("describe-image-toggle");
    const simulateSelect = document.getElementById("simulate-select");
    
    // Cards Results
    const cardProgress = document.getElementById("card-progress");
    const progressBar = document.getElementById("progress-bar");
    const step1 = document.getElementById("step-1");
    const step2 = document.getElementById("step-2");
    const step3 = document.getElementById("step-3");
    
    const cardResults = document.getElementById("card-results");
    const resultLink = document.getElementById("result-link");
    const resultPin = document.getElementById("result-pin");
    const qrCodeImg = document.getElementById("qr-code");
    
    const cardTroubleshooting = document.getElementById("card-troubleshooting");
    const errorPhaseTitle = document.getElementById("error-phase-title");
    const errorTypeTitle = document.getElementById("error-type-title");
    const errorFriendlyMessage = document.getElementById("error-friendly-message");
    const errorActionsList = document.getElementById("error-actions-list");
    const errorTechnicalText = document.getElementById("error-technical-text");
    const btnToggleTechnical = document.getElementById("btn-toggle-technical");
    const technicalTraceback = document.getElementById("technical-traceback");
    
    const cardComparison = document.getElementById("card-comparison");
    const textOriginal = document.getElementById("text-original");
    const textHumanized = document.getElementById("text-humanized");
    
    const terminalLogs = document.getElementById("terminal-logs");
    const cardConsole = document.getElementById("card-console");
    
    // State
    let reportFile = null;
    let imageFile = null;
    let progressInterval = null;

    // --- Drag and Drop Setup ---
    setupDragAndDrop(filesDropzone, filesInput, handleFilesSelected);

    function setupDragAndDrop(dropzone, input, onFilesSelect) {
        dropzone.addEventListener("click", (e) => {
            // Only trigger input click if clicking on the dropzone text/icon, 
            // not when clicking clear buttons inside the preview list
            if (e.target.closest(".btn-clear") || e.target.closest(".files-list")) {
                return;
            }
            input.click();
        });
        
        input.addEventListener("change", () => {
            if (input.files.length > 0) {
                onFilesSelect(input.files);
            }
        });

        ["dragenter", "dragover"].forEach(eventName => {
            dropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropzone.classList.add("dragover");
            }, false);
        });

        ["dragleave", "drop"].forEach(eventName => {
            dropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropzone.classList.remove("dragover");
            }, false);
        });

        dropzone.addEventListener("drop", (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files.length > 0) {
                onFilesSelect(files);
            }
        }, false);
    }

    // --- Files Classification Heuristics ---
    function handleFilesSelected(filesList) {
        const files = Array.from(filesList);
        if (files.length === 0) return;

        // Classify files
        const pdfOrDocx = files.filter(f => f.name.match(/\.(pdf|docx?)$/i));
        const images = files.filter(f => f.name.match(/\.(png|jpe?g|webp|gif)$/i));

        if (pdfOrDocx.length > 0) {
            // We have a document
            reportFile = pdfOrDocx[0];
            // If we have an image as well, set it as the study image
            if (images.length > 0) {
                imageFile = images[0];
            } else if (files.length > 1) {
                // If there are other files, check if the second is an image
                const second = files.find(f => f !== reportFile);
                if (second && second.name.match(/\.(png|jpe?g|webp)$/i)) {
                    imageFile = second;
                }
            }
        } else {
            // No PDF/DOCX. Only images or other files
            if (images.length === 1) {
                // Only one image -> treat as report image (e.g. scanned image report)
                reportFile = images[0];
                imageFile = null;
            } else if (images.length >= 2) {
                // Two or more images -> first is report image, second is study image
                reportFile = images[0];
                imageFile = images[1];
            } else {
                // Fallback for other file types
                reportFile = files[0];
                if (files.length > 1) imageFile = files[1];
            }
        }

        updateFilesUI();
    }

    // --- Update Files UI List ---
    function updateFilesUI() {
        const dropText = filesDropzone.querySelector(".drop-text");
        const dropHelp = filesDropzone.querySelector(".drop-help");
        const dropIcon = filesDropzone.querySelector(".drop-icon");

        // Clear list
        filesListContainer.innerHTML = "";

        if (!reportFile && !imageFile) {
            // Show original dropzone texts
            if (dropText) dropText.style.display = "block";
            if (dropHelp) dropHelp.style.display = "block";
            if (dropIcon) dropIcon.style.display = "inline-block";
            filesListContainer.style.display = "none";
            filesInput.value = "";
            return;
        }

        // Hide original dropzone texts
        if (dropText) dropText.style.display = "none";
        if (dropHelp) dropHelp.style.display = "none";
        if (dropIcon) dropIcon.style.display = "none";
        filesListContainer.style.display = "flex";

        // Render Report File
        if (reportFile) {
            const isPDF = reportFile.name.match(/\.(pdf|docx?)$/i);
            const iconClass = isPDF ? "fa-solid fa-file-pdf" : "fa-solid fa-file-image";
            createFileRow(reportFile.name, iconClass, "Informe Médico", "report", () => {
                reportFile = null;
                updateFilesUI();
            });
        }

        // Render Study Image File
        if (imageFile) {
            createFileRow(imageFile.name, "fa-solid fa-file-image", "Imagen de Estudio (Opcional)", "image", () => {
                imageFile = null;
                updateFilesUI();
            });
        }
    }

    function createFileRow(name, iconClass, roleLabel, roleClass, onClear) {
        const row = document.createElement("div");
        row.className = "file-row";
        
        row.innerHTML = `
            <i class="${iconClass} file-icon"></i>
            <div class="file-info">
                <span class="file-name" title="${name}">${name}</span>
                <span class="file-role-badge ${roleClass}">${roleLabel}</span>
            </div>
            <button type="button" class="btn-clear"><i class="fa-solid fa-xmark"></i></button>
        `;

        row.querySelector(".btn-clear").addEventListener("click", (e) => {
            e.preventDefault();
            e.stopPropagation();
            onClear();
        });

        filesListContainer.appendChild(row);
    }

    // --- Tab Switching ---
    const tabButtons = document.querySelectorAll(".tab-btn");
    const tabPanes = document.querySelectorAll(".tab-pane");

    tabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const target = btn.getAttribute("data-tab");
            
            tabButtons.forEach(b => b.classList.remove("active"));
            tabPanes.forEach(p => p.classList.remove("active"));
            
            btn.classList.add("active");
            document.getElementById(target).classList.add("active");
        });
    });

    // --- Accordion Toggle ---
    btnToggleTechnical.addEventListener("click", () => {
        const isHidden = technicalTraceback.style.display === "none";
        technicalTraceback.style.display = isHidden ? "block" : "none";
        btnToggleTechnical.querySelector("i").className = isHidden 
            ? "fa-solid fa-chevron-up" 
            : "fa-solid fa-chevron-down";
    });

    // --- Copy Clipboard ---
    document.getElementById("btn-copy-link").addEventListener("click", () => {
        copyToClipboard(resultLink.href, "btn-copy-link");
    });

    document.getElementById("btn-copy-pin").addEventListener("click", () => {
        copyToClipboard(resultPin.textContent, "btn-copy-pin");
    });

    function copyToClipboard(text, btnId) {
        navigator.clipboard.writeText(text).then(() => {
            const btn = document.getElementById(btnId);
            const icon = btn.querySelector("i");
            icon.className = "fa-solid fa-check";
            btn.style.color = "var(--success-color)";
            setTimeout(() => {
                icon.className = "fa-solid fa-copy";
                btn.style.color = "";
            }, 2000);
        });
    }

    // --- Log Terminal Functions ---
    function clearTerminal() {
        terminalLogs.innerHTML = "";
    }

    function appendLog(message, type = "info") {
        const line = document.createElement("div");
        line.className = `log-line ${type}`;
        line.textContent = message;
        terminalLogs.appendChild(line);
        terminalLogs.scrollTop = terminalLogs.scrollHeight;
    }

    function renderLogs(logs) {
        clearTerminal();
        if (!logs || logs.length === 0) {
            appendLog("Sin registros de log en esta ejecución.", "system");
            return;
        }
        logs.forEach(log => {
            let type = "info";
            if (log.includes("| ERROR    |")) type = "error";
            else if (log.includes("| WARNING  |")) type = "warn";
            else if (log.includes("| SUCCESS  |") || log.includes("[OK]")) type = "success";
            
            appendLog(log, type);
        });
    }

    // --- Process Action ---
    btnProcess.addEventListener("click", async () => {
        if (!reportFile) {
            alert("Por favor, selecciona al menos un informe médico (PDF o Imagen) para continuar.");
            return;
        }

        // Reset UI States
        btnProcess.disabled = true;
        btnText.style.display = "none";
        btnLoader.style.display = "flex";
        
        cardResults.style.display = "none";
        cardTroubleshooting.style.display = "none";
        cardComparison.style.display = "none";
        cardConsole.style.display = "none";
        
        cardProgress.style.display = "block";
        cardConsole.style.display = "block";
        resetProgressSteps();
        
        clearTerminal();
        appendLog("Iniciando procesamiento de informe médico...", "info");
        appendLog(`Informe clasificado: ${reportFile.name}`, "system");
        if (imageFile) appendLog(`Imagen de estudio clasificada: ${imageFile.name}`, "system");
        
        // Animate fake progress steps
        animateFakeProgress();

        // Build form data
        const formData = new FormData();
        formData.append("file", reportFile);
        if (imageFile) {
            formData.append("study_image", imageFile);
        }
        formData.append("language", languageSelect.value);
        formData.append("describe_image", describeImageToggle.checked);
        if (simulateSelect.value) {
            formData.append("simulate_error", simulateSelect.value);
        }
        formData.append("auto_fix", true);

        try {
            const response = await fetch("/api/process", {
                method: "POST",
                body: formData
            });

            if (!response.ok) {
                throw new Error(`HTTP Error: ${response.status}`);
            }

            const data = await response.json();
            clearInterval(progressInterval);
            
            // Render execution logs
            renderLogs(data.logs);

            if (data.success) {
                // Update Progress UI
                progressBar.style.width = "100%";
                setStepState(step1, "completed");
                setStepState(step2, "completed");
                setStepState(step3, "completed");
                
                // Show Success
                resultLink.href = data.magic_link_url;
                resultLink.textContent = data.magic_link_url;
                resultPin.textContent = data.pin;
                qrCodeImg.src = `https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=${encodeURIComponent(data.magic_link_url)}`;
                cardResults.style.display = "block";
                
                // Show Comparison
                textOriginal.textContent = data.original_text || "No disponible.";
                textHumanized.textContent = data.humanized_text || "No disponible.";
                cardComparison.style.display = "block";
                
                // Switch default tab to humanized
                document.querySelector('[data-tab="tab-humanized"]').click();
                
                appendLog("¡Proceso completado con éxito!", "success");
            } else {
                // Show Troubleshooting
                progressBar.style.width = "100%";
                progressBar.style.background = "var(--error-color)";
                progressBar.style.boxShadow = "0 0 10px rgba(239, 68, 68, 0.5)";
                
                const err = data.error || {};
                errorPhaseTitle.textContent = err.phase || "Proceso";
                errorTypeTitle.textContent = err.type || "Error";
                errorFriendlyMessage.textContent = err.message || "Ha ocurrido un error inesperado al procesar la solicitud.";
                
                // Render Actions
                errorActionsList.innerHTML = "";
                if (err.actions && err.actions.length > 0) {
                    err.actions.forEach(action => {
                        const li = document.createElement("li");
                        li.textContent = action;
                        errorActionsList.appendChild(li);
                    });
                } else {
                    const li = document.createElement("li");
                    li.textContent = "Revisa los logs de ejecución para encontrar pistas.";
                    errorActionsList.appendChild(li);
                }

                // Tech details
                errorTechnicalText.textContent = err.technical || "Sin traceback técnico.";
                cardTroubleshooting.style.display = "block";
                
                appendLog(`Error durante la ejecución en ${err.phase || 'fase desconocida'}`, "error");
            }

        } catch (error) {
            clearInterval(progressInterval);
            appendLog(`Error de conexión con el servidor API: ${error.message}`, "error");
            
            // Show Troubleshooting
            errorPhaseTitle.textContent = "Conexión API";
            errorTypeTitle.textContent = "NetworkError";
            errorFriendlyMessage.textContent = "No se pudo conectar con el servidor backend. Por favor, asegúrate de que el servidor FastAPI está en funcionamiento.";
            errorActionsList.innerHTML = "<li>Inicia el servidor uvicorn en tu consola de WSL.</li><li>Verifica el puerto configurado (8000 por defecto).</li>";
            errorTechnicalText.textContent = error.stack;
            cardTroubleshooting.style.display = "block";
        } finally {
            btnProcess.disabled = false;
            btnText.style.display = "flex";
            btnLoader.style.display = "none";
        }
    });

    function resetProgressSteps() {
        progressBar.style.width = "0%";
        progressBar.style.background = "";
        progressBar.style.boxShadow = "";
        
        step1.className = "step-node";
        step2.className = "step-node";
        step3.className = "step-node";
    }

    function setStepState(stepNode, state) {
        stepNode.className = "step-node";
        if (state === "active") stepNode.classList.add("active");
        if (state === "completed") stepNode.classList.add("completed");
    }

    function animateFakeProgress() {
        let percent = 0;
        progressBar.style.width = `${percent}%`;
        setStepState(step1, "active");

        progressInterval = setInterval(() => {
            if (percent < 30) {
                percent += 1;
                progressBar.style.width = `${percent}%`;
            } else if (percent === 30) {
                setStepState(step1, "completed");
                setStepState(step2, "active");
                percent += 1;
            } else if (percent < 70) {
                percent += 0.5;
                progressBar.style.width = `${percent}%`;
            } else if (percent === 70) {
                setStepState(step2, "completed");
                setStepState(step3, "active");
                percent += 1;
            } else if (percent < 92) {
                percent += 0.2;
                progressBar.style.width = `${percent}%`;
            }
        }, 150);
    }
});
