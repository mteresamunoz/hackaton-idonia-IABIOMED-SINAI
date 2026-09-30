import React, { useEffect, useState } from 'react';
import { Database, Brain, Link, Loader2, CheckCircle, FileText, Eye, Edit3, Check } from 'lucide-react';

function MarkdownRenderer({ content }) {
  if (!content) return null;

  const lines = content.split('\n');
  let inList = false;
  const renderedElements = [];

  const parseInline = (text) => {
    let html = text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>');
    return <span dangerouslySetInnerHTML={{ __html: html }} />;
  };

  lines.forEach((line, index) => {
    const trimmed = line.trim();

    if (trimmed.startsWith('###')) {
      if (inList) inList = false;
      renderedElements.push(
        <h4 key={index} className="text-xs font-bold text-slate-800 mt-3 mb-1">
          {parseInline(trimmed.substring(3).trim())}
        </h4>
      );
    } else if (trimmed.startsWith('##')) {
      if (inList) inList = false;
      renderedElements.push(
        <h3 key={index} className="text-sm font-bold text-slate-900 mt-4 mb-2">
          {parseInline(trimmed.substring(2).trim())}
        </h3>
      );
    } else if (trimmed.startsWith('#')) {
      if (inList) inList = false;
      renderedElements.push(
        <h2 key={index} className="text-base font-extrabold text-slate-950 mt-5 mb-2">
          {parseInline(trimmed.substring(1).trim())}
        </h2>
      );
    }
    else if (trimmed.startsWith('-') || trimmed.startsWith('*')) {
      inList = true;
      renderedElements.push(
        <li key={index} className="ml-4 list-disc text-xs text-slate-650 my-1 leading-relaxed">
          {parseInline(trimmed.substring(1).trim())}
        </li>
      );
    }
    else if (trimmed === '') {
      if (inList) inList = false;
      renderedElements.push(<div key={index} className="h-2" />);
    }
    else {
      if (inList) inList = false;
      renderedElements.push(
        <p key={index} className="text-xs text-slate-600 my-1.5 leading-relaxed">
          {parseInline(trimmed)}
        </p>
      );
    }
  });

  return <div className="space-y-1">{renderedElements}</div>;
}

export default function PipelineProgress({
  reportFile,
  studyImageFile,
  describeImageActive,
  isWaitingForApproval,
  isDescribing,
  descriptionText,
  setDescriptionText,
  onApproveDescription,
  activeStep,
  logs = [],
  loading
}) {
  const [reportUrl, setReportUrl] = useState('');
  const [imageUrl, setImageUrl] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [activeTab, setActiveTab] = useState('report');

  useEffect(() => {
    if (reportFile) {
      const url = URL.createObjectURL(reportFile);
      setReportUrl(url);
      return () => URL.revokeObjectURL(url);
    }
  }, [reportFile]);

  useEffect(() => {
    if (studyImageFile) {
      const url = URL.createObjectURL(studyImageFile);
      setImageUrl(url);
      return () => URL.revokeObjectURL(url);
    }
  }, [studyImageFile]);

  const isPdf = reportFile && (reportFile.type === 'application/pdf' || reportFile.name.endsWith('.pdf'));

  return (
    // FIX: added overflow-hidden to prevent inner content from pushing layout and creating grey band
    <div className="flex flex-col lg:flex-row w-full h-[calc(100vh-4.5rem)] overflow-hidden">
      
      {/* LEFT HALF: Document / Image Viewer */}
      <div className="w-full lg:w-1/2 h-full bg-slate-100 flex flex-col overflow-hidden">
        {studyImageFile && (
          <div className="bg-slate-100 border-b border-slate-200 flex items-center shrink-0">
            <button
              type="button"
              onClick={() => setActiveTab('report')}
              className={`px-6 py-3 text-xs font-semibold transition-all border-b-2 ${
                activeTab === 'report'
                  ? 'bg-white text-brand-600 border-brand-600'
                  : 'bg-transparent text-slate-500 border-transparent hover:bg-slate-50/50 hover:text-slate-700'
              }`}
            >
              Informe Médico
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('image')}
              className={`px-6 py-3 text-xs font-semibold transition-all border-b-2 ${
                activeTab === 'image'
                  ? 'bg-white text-brand-600 border-brand-600'
                  : 'bg-transparent text-slate-500 border-transparent hover:bg-slate-50/50 hover:text-slate-700'
              }`}
            >
              Imagen del Estudio
            </button>
          </div>
        )}

        <div className="flex-1 overflow-hidden relative bg-slate-200">
          {activeTab === 'report' ? (
            isPdf ? (
              <iframe
                src={`${reportUrl}#toolbar=0&zoom=60`}
                className="w-full h-full border-0 bg-white"
                title="Visor de Informe PDF"
              />
            ) : reportFile ? (
              <div className="w-full h-full flex items-center justify-center bg-slate-100">
                <img
                  src={reportUrl}
                  alt="Informe médico original"
                  className="max-w-full max-h-full object-contain"
                />
              </div>
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <p className="text-xs text-slate-400">Cargando vista previa...</p>
              </div>
            )
          ) : (
            studyImageFile ? (
              <div className="w-full h-full flex items-center justify-center bg-slate-900 p-4">
                <img
                  src={imageUrl}
                  alt="Imagen de estudio médico"
                  className="max-w-full max-h-full object-contain rounded-lg shadow-lg"
                />
              </div>
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <p className="text-xs text-slate-400">No hay imagen cargada</p>
              </div>
            )
          )}
        </div>
      </div>

      {/* RIGHT HALF: Pipeline Process & Interactive Approval */}
      <div className="w-full lg:w-1/2 h-full bg-white border-l border-slate-200 flex flex-col overflow-hidden">
        <div className="bg-slate-50 border-b border-slate-100 px-4 py-3 flex items-center justify-between shrink-0">
          <span className="text-xs font-bold text-slate-700">Consola del Pipeline IABiomed</span>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 bg-brand-500 rounded-full animate-ping" />
            <span className="text-[10px] text-brand-600 font-bold uppercase tracking-wider">Procesando</span>
          </div>
        </div>

        {/* Inner Column */}
        <div className="flex-1 flex flex-col overflow-hidden relative">
          {loading && !isWaitingForApproval ? (
            <div className="flex-1 flex flex-col items-center justify-center p-8 bg-white transition-all duration-300">
              <div className="relative mb-6">
                <Loader2 className="animate-spin text-brand-600 w-14 h-14 stroke-[1.5]" />
              </div>
              <h3 className="text-sm font-bold text-slate-800 animate-pulse text-center">
                Procesando Pipeline IABiomed
              </h3>
              {logs.length > 0 && (
                <p className="text-[11px] text-slate-500 mt-3 text-center max-w-xs font-mono bg-slate-50 border border-slate-100 px-3 py-2 rounded-xl" key={logs.length}>
                  {logs[logs.length - 1]}
                </p>
              )}
            </div>
          ) : descriptionText ? (
            <div className="flex-1 overflow-hidden p-6 flex flex-col justify-between bg-white animate-fade-in">
              <div className="flex-1 flex flex-col min-h-0 space-y-4">
                <div className="flex items-center gap-2 pb-3 border-b border-slate-100 shrink-0">
                  <h3 className="text-sm font-bold text-slate-800">Descripción Multimodal</h3>
                </div>
                
                <div className="flex-1 min-h-0 overflow-y-auto">
                  {isEditing ? (
                    <textarea
                      value={descriptionText}
                      onChange={(e) => setDescriptionText(e.target.value)}
                      className="w-full h-full bg-slate-50/50 border border-slate-200 rounded-xl p-3.5 text-xs text-slate-700 focus:outline-none focus:ring-1 focus:ring-brand-500 leading-relaxed font-mono resize-none"
                    />
                  ) : (
                    <div className="h-full bg-white p-1 rounded-xl">
                      <MarkdownRenderer content={descriptionText} />
                    </div>
                  )}
                </div>
              </div>

              {isWaitingForApproval && (
                <div className="flex items-center gap-3 pt-4 border-t border-slate-100 mt-4 bg-white shrink-0">
                  <button
                    type="button"
                    onClick={() => setIsEditing(!isEditing)}
                    className="flex-1 py-2.5 px-3 border border-slate-200 hover:bg-slate-50 text-slate-700 font-semibold text-xs rounded-xl flex items-center justify-center gap-1.5 transition-colors"
                  >
                    <Edit3 size={13} />
                    {isEditing ? 'Vista Previa' : 'Editar Descripción'}
                  </button>
                  <button
                    type="button"
                    onClick={onApproveDescription}
                    className="flex-1 py-2.5 px-3 bg-brand-600 hover:bg-brand-700 text-white font-bold text-xs rounded-xl flex items-center justify-center gap-1.5 shadow-sm transition-colors"
                  >
                    <Check size={13} />
                    Aceptar y Continuar
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto p-5 space-y-6">
              {/* Phase status tags */}
              <div className="grid grid-cols-3 gap-2">
                <div className={`p-2.5 rounded-xl border text-center transition-all ${
                  activeStep > 1 
                    ? 'bg-emerald-50/50 border-emerald-100 text-emerald-700' 
                    : activeStep === 1 
                      ? 'bg-brand-50/50 border-brand-100 text-brand-700 font-bold' 
                      : 'bg-slate-50 border-slate-100 text-slate-400'
                }`}>
                  <div className="text-[10px] uppercase tracking-wider font-semibold">Fase I</div>
                  <div className="text-xs mt-0.5">Ingesta</div>
                </div>
                
                <div className={`p-2.5 rounded-xl border text-center transition-all ${
                  activeStep > 2 
                    ? 'bg-emerald-50/50 border-emerald-100 text-emerald-700' 
                    : activeStep === 2 
                      ? 'bg-brand-50/50 border-brand-100 text-brand-700 font-bold' 
                      : 'bg-slate-50 border-slate-100 text-slate-400'
                }`}>
                  <div className="text-[10px] uppercase tracking-wider font-semibold">Fase II</div>
                  <div className="text-xs mt-0.5">Humanización</div>
                </div>

                <div className={`p-2.5 rounded-xl border text-center transition-all ${
                  activeStep > 3 
                    ? 'bg-emerald-50/50 border-emerald-100 text-emerald-700' 
                    : activeStep === 3 
                      ? 'bg-brand-50/50 border-brand-100 text-brand-700 font-bold' 
                      : 'bg-slate-50 border-slate-100 text-slate-400'
                }`}>
                  <div className="text-[10px] uppercase tracking-wider font-semibold">Fase III</div>
                  <div className="text-xs mt-0.5">Magic Link</div>
                </div>
              </div>

              {/* Real-time process logs */}
              <div className="space-y-2.5">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Progreso del Proceso</span>
                <div className="bg-slate-900 rounded-xl p-4 h-56 overflow-y-auto font-mono text-[10px] text-slate-300 space-y-1.5 scrollbar-thin">
                  {logs.map((log, idx) => {
                    let color = 'text-slate-300';
                    if (log.includes('[ERROR]')) color = 'text-rose-400';
                    else if (log.includes('[OK]') || log.includes('completada')) color = 'text-emerald-400';
                    else if (log.includes('[IA') || log.includes('[MULTILINGÜE]')) color = 'text-cyan-400';
                    else if (log.includes('[RGPD]')) color = 'text-indigo-300';

                    return (
                      <div key={idx} className={`${color} leading-relaxed break-words`}>
                        {log}
                      </div>
                    );
                  })}
                  {loading && !isWaitingForApproval && (
                    <div className="flex items-center gap-1.5 text-slate-500 italic pt-1 animate-pulse">
                      <Loader2 className="animate-spin" size={10} />
                      <span>Procesando siguiente fase...</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}