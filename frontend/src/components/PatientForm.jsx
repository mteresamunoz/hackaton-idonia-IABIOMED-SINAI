import React, { useRef, useState } from 'react';
import { FileText, Image as ImageIcon, Eye, Shield, Upload, X, ChevronDown, ChevronUp, FolderOpen } from 'lucide-react';
import LanguageSelector from './LanguageSelector';

export default function PatientForm({
  files,
  setFiles,
  language,
  setLanguage,
  describeImage,
  setDescribeImage,
  anonymize,
  setAnonymize,
  patientId,
  setPatientId,
  accessionNum,
  setAccessionNum,
  studyDesc,
  setStudyDesc,
  onSubmit,
  loading
}) {
  const fileInputRef = useRef(null);
  const [dragActive, setDragActive] = useState(false);
  const [studyOpen, setStudyOpen] = useState(false);

  // Helper to check if a file is an image
  const isImageFile = (file) => {
    if (!file) return false;
    return file.type.startsWith('image/') || /\.(png|jpe?g|gif|dcm)$/i.test(file.name);
  };

  // Helper to check if any image has been uploaded
  const hasImage = isImageFile(files.report) || isImageFile(files.studyImage);

  // Manage dropped / selected files
  const handleFiles = (incomingFiles) => {
    const fileList = Array.from(incomingFiles);
    if (fileList.length === 0) return;

    let newReport = files.report;
    let newStudyImage = files.studyImage;

    // If two files are dropped at once
    if (fileList.length >= 2) {
      const pdfFile = fileList.find(f => f.type === 'application/pdf' || f.name.endsWith('.pdf'));
      const imgFile = fileList.find(f => isImageFile(f));
      
      if (pdfFile) newReport = pdfFile;
      if (imgFile) newStudyImage = imgFile;

      // Fallback if no PDF was found but we got two files
      if (!pdfFile) {
        newReport = fileList[0];
        newStudyImage = fileList[1];
      }
    } else {
      // Single file dropped/selected
      const singleFile = fileList[0];
      if (singleFile.type === 'application/pdf' || singleFile.name.endsWith('.pdf')) {
        newReport = singleFile;
      } else if (isImageFile(singleFile)) {
        // If it's an image
        if (newReport && !isImageFile(newReport)) {
          // If we already have a PDF report, set as study image
          newStudyImage = singleFile;
        } else {
          // Otherwise, it is the main report (OCR target)
          newReport = singleFile;
        }
      } else {
        // Fallback for other file types
        newReport = singleFile;
      }
    }

    setFiles({ report: newReport, studyImage: newStudyImage });
    
    // Automatically enable multimodal description if an image is detected
    const anyImage = isImageFile(newReport) || isImageFile(newStudyImage);
    if (anyImage) {
      setDescribeImage(true);
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(e.target.files);
    }
  };

  const removeFile = (type, e) => {
    e.stopPropagation();
    if (type === 'report') {
      if (files.studyImage) {
        setFiles({ report: files.studyImage, studyImage: null });
      } else {
        setFiles(prev => ({ ...prev, report: null }));
      }
    } else {
      setFiles(prev => ({ ...prev, studyImage: null }));
    }
  };

  const formatSize = (bytes) => {
    if (!bytes) return '';
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const isSubmitDisabled = !files.report || loading;

  return (
    <form onSubmit={onSubmit} className="max-w-2xl mx-auto">
      {/* Super Compact Unified Card */}
      <div className="bg-white p-5 sm:p-6 rounded-2xl border border-slate-100 shadow-lg shadow-slate-100/30 space-y-4">

        {/* Top row: Language selector on the left, anonymization control on the right */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex-1">
            <LanguageSelector selected={language} onChange={setLanguage} />
          </div>

          <div className="flex items-center gap-2 bg-slate-50 p-1 rounded-xl border border-slate-100/50 shrink-0 self-start sm:self-auto">
            <div className="flex items-center gap-1.5 px-2 py-1">
              <Shield size={12} className="text-emerald-600" />
              <div className="flex flex-col leading-none">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Anonimización</span>
              </div>
            </div>

            <div className="h-4 w-px bg-slate-200" />

            <button
              type="button"
              onClick={() => setAnonymize(!anonymize)}
              className={`relative inline-flex h-4 w-8 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${anonymize ? 'bg-brand-600' : 'bg-slate-300'}`}
              aria-label="Activar o desactivar anonimización"
            >
              <span className={`pointer-events-none inline-block h-3 w-3 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${anonymize ? 'translate-x-4' : 'translate-x-0'}`} />
            </button>
          </div>
        </div>

        {/* ── Datos del estudio (collapsible) ───────────────────────────── */}
        <div className="rounded-xl border border-slate-100 overflow-hidden">
          <button
            type="button"
            onClick={() => setStudyOpen(o => !o)}
            className="w-full flex items-center justify-between px-3.5 py-2.5 bg-slate-50 hover:bg-slate-100/70 transition-colors"
          >
            <div className="flex items-center gap-2">
              <FolderOpen size={13} className="text-brand-500" />
              <span className="text-[11px] font-bold text-slate-600 uppercase tracking-wider">Datos del estudio</span>
              {(patientId || accessionNum || studyDesc) && (
                <span className="inline-flex items-center justify-center w-1.5 h-1.5 rounded-full bg-brand-500" />
              )}
            </div>
            {studyOpen
              ? <ChevronUp size={13} className="text-slate-400" />
              : <ChevronDown size={13} className="text-slate-400" />}
          </button>

          {studyOpen && (
            <div className="px-3.5 py-3 grid grid-cols-1 sm:grid-cols-3 gap-3 bg-white border-t border-slate-100">
              {/* DNI / ID Paciente */}
              <div className="flex flex-col gap-1">
                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider" htmlFor="field-patient-id">
                  DNI paciente
                </label>
                <input
                  id="field-patient-id"
                  type="text"
                  value={patientId}
                  onChange={e => setPatientId(e.target.value)}
                  placeholder="ej. 12345678C"
                  className="text-xs px-2.5 py-2 rounded-lg border border-slate-200 bg-slate-50 focus:bg-white focus:border-brand-400 focus:ring-1 focus:ring-brand-200 outline-none transition placeholder:text-slate-300 font-mono"
                />
              </div>

              {/* Número de acceso / Destino */}
              <div className="flex flex-col gap-1">
                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider" htmlFor="field-accession-num">
                  Destino
                </label>
                <input
                  id="field-accession-num"
                  type="text"
                  value={accessionNum}
                  onChange={e => setAccessionNum(e.target.value)}
                  placeholder="ej. Traslados desde Asturias"
                  className="text-xs px-2.5 py-2 rounded-lg border border-slate-200 bg-slate-50 focus:bg-white focus:border-brand-400 focus:ring-1 focus:ring-brand-200 outline-none transition placeholder:text-slate-300"
                />
              </div>

              {/* Carpeta del estudio */}
              <div className="flex flex-col gap-1">
                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider" htmlFor="field-study-desc">
                  Carpeta del estudio
                </label>
                <input
                  id="field-study-desc"
                  type="text"
                  value={studyDesc}
                  onChange={e => setStudyDesc(e.target.value)}
                  placeholder="ej. RM-RODILLA-2026"
                  className="text-xs px-2.5 py-2 rounded-lg border border-slate-200 bg-slate-50 focus:bg-white focus:border-brand-400 focus:ring-1 focus:ring-brand-200 outline-none transition placeholder:text-slate-300"
                />
              </div>

            </div>
          )}
        </div>

        {/* Unified Upload Area (Always visible) */}
        <div
          onDragEnter={handleDrag}
          onDragOver={handleDrag}
          onDragLeave={handleDrag}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current.click()}
          className={`border-2 border-dashed rounded-xl p-5 flex flex-col items-center justify-center cursor-pointer transition-all duration-200 ${
            dragActive 
              ? 'border-brand-500 bg-brand-50/30 scale-[0.99]' 
              : 'border-slate-200 hover:border-brand-400 hover:bg-slate-50/50'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,image/*"
            multiple
            onChange={handleFileChange}
            className="hidden"
          />

          <div className="text-center py-2">
            <div className="mx-auto w-10 h-10 bg-slate-50 text-brand-500 rounded-full flex items-center justify-center mb-2 shadow-sm">
              <Upload size={18} />
            </div>
            <p className="text-xs font-semibold text-slate-700">Arrastra o selecciona el informe médico o estudio</p>
          </div>
        </div>

        {/* List of uploaded files displayed BELOW the upload area */}
        {(files.report || files.studyImage) && (
          <div className="w-full space-y-2.5 bg-slate-50/50 p-3.5 rounded-xl border border-slate-100 animate-fade-in">
            <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">Archivos Seleccionados</h4>
            
            {files.report && (
              <div className="flex items-center justify-between p-2.5 bg-white rounded-lg border border-slate-100 shadow-sm">
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className={`p-1.5 rounded ${isImageFile(files.report) ? 'bg-indigo-50 text-indigo-600' : 'bg-brand-50 text-brand-600'} shrink-0`}>
                    {isImageFile(files.report) ? <ImageIcon size={14} /> : <FileText size={14} />}
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-semibold text-slate-800 truncate leading-none mb-0.5">{files.report.name}</p>
                    <p className="text-[10px] text-slate-400 leading-none">{isImageFile(files.report) ? 'Informe / Imagen' : 'Informe PDF'} • {formatSize(files.report.size)}</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={(e) => removeFile('report', e)}
                  className="p-1 hover:bg-slate-100 rounded text-slate-400 hover:text-slate-650 transition-colors"
                >
                  <X size={14} />
                </button>
              </div>
            )}

            {files.studyImage && (
              <div className="flex items-center justify-between p-2.5 bg-white rounded-lg border border-slate-100 shadow-sm">
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="p-1.5 bg-indigo-50 text-indigo-600 rounded shrink-0">
                    <ImageIcon size={14} />
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-semibold text-slate-800 truncate leading-none mb-0.5">{files.studyImage.name}</p>
                    <p className="text-[10px] text-slate-400 leading-none">Imagen de estudio • {formatSize(files.studyImage.size)}</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={(e) => removeFile('studyImage', e)}
                  className="p-1 hover:bg-slate-100 rounded text-slate-400 hover:text-slate-650 transition-colors"
                >
                  <X size={14} />
                </button>
              </div>
            )}
            {/* Removed "Añadir o cambiar archivos" button */}
          </div>
        )}

        {/* Conditional Multimodal Vision Section */}
        {hasImage && (
          <div className="p-3 bg-indigo-50/50 border border-indigo-100/40 rounded-xl flex items-center justify-between animate-fade-in">
            <div className="flex items-center gap-2.5">
              <div className="p-1.5 bg-indigo-100/60 rounded-lg text-indigo-600">
                <Eye size={16} />
              </div>
              <div>
                <h4 className="text-xs font-bold text-indigo-950">Descripción Multimodal por IA</h4>
                <p className="text-[10px] text-indigo-600 mt-0.5">Hemos detectado una imagen médica. ¿Quieres describirla e incluirla?</p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setDescribeImage(!describeImage)}
              className={`relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${describeImage ? 'bg-indigo-600' : 'bg-slate-300'}`}
            >
              <span className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${describeImage ? 'translate-x-4' : 'translate-x-0'}`} />
            </button>
          </div>
        )}

        {/* Action Button */}
        <div className="pt-1">
          <button
            type="submit"
            disabled={isSubmitDisabled}
            className={`w-full py-3 rounded-xl text-white font-bold text-xs shadow-md transition-all uppercase tracking-wider ${
              isSubmitDisabled 
                ? 'bg-slate-300 cursor-not-allowed shadow-none' 
                : 'bg-brand-600 hover:bg-brand-700 hover:shadow-lg active:transform active:scale-[0.99]'
            }`}
          >
            {loading ? 'Procesando pipeline...' : 'Iniciar Pipeline IABiomed'}
          </button>
        </div>
      </div>
    </form>
  );
}
