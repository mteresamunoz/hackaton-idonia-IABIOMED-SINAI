import React, { useState } from 'react';
import { Shield, Brain, Heart, Eye } from 'lucide-react';
import PatientForm from './components/PatientForm';
import PipelineProgress from './components/PipelineProgress';
import SuccessScreen from './components/SuccessScreen';
import ErrorAgentMascot from './components/ErrorAgentMascot';
import { processReport, describeImageApi } from './services/api';

export default function App() {
  const [step, setStep] = useState('form');
  const [files, setFiles] = useState({ report: null, studyImage: null });
  const [language, setLanguage] = useState('es');
  const [describeImage, setDescribeImage] = useState(false);
  const [anonymize, setAnonymize] = useState(true);
  const [loading, setLoading] = useState(false);

  // Idonia folder fields (can override .env defaults)
  const [patientId, setPatientId] = useState('');
  const [accessionNum, setAccessionNum] = useState('');
  const [studyDesc, setStudyDesc] = useState('');

  const [pipelineLogs, setPipelineLogs] = useState([]);
  const [imageDescription, setImageDescription] = useState('');
  const [isDescribing, setIsDescribing] = useState(false);
  const [isWaitingForApproval, setIsWaitingForApproval] = useState(false);
  const [activeStep, setActiveStep] = useState(1);

  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    if (!files.report) return;

    setLoading(true);
    setStep('progress');
    setError(null);
    setResult(null);
    setActiveStep(1);
    setImageDescription('');
    setIsDescribing(false);
    setIsWaitingForApproval(false);

    const logs = [
      '[FASE 1] Iniciando Pipeline IABiomed...',
      '[FASE 1] Autenticando actor con Idonia Connect Cloud...',
      '[FASE 1] Subiendo informe médico original PDF...'
    ];
    setPipelineLogs(logs);

    try {
      const imageToDescribe = files.studyImage || (files.report && files.report.type.startsWith('image/') ? files.report : null);

      if (describeImage && imageToDescribe) {
        setPipelineLogs(prev => [
          ...prev,
          '[FASE 1] OK - Archivos subidos a Idonia Connect.',
          '[IA MULTIMODAL] Analizando imagen de alta tecnología...',
          '[IA MULTIMODAL] Solicitando descripción del estudio médico al modelo multimodal...'
        ]);
        setIsDescribing(true);
        setActiveStep(2);

        const descData = await describeImageApi(imageToDescribe);

        setIsDescribing(false);
        setImageDescription(descData.description || 'No se pudo generar descripción.');
        setIsWaitingForApproval(true);
        setPipelineLogs(prev => [
          ...prev,
          '[IA MULTIMODAL] Descripción generada con éxito.',
          '[SOPORTE] Esperando que el médico revise y acepte la descripción para continuar.'
        ]);
      } else {
        await executeFullPipeline(null);
      }
    } catch (err) {
      handlePipelineError(err);
    }
  };

  const executeFullPipeline = async (finalDesc) => {
    setLoading(true);
    setIsWaitingForApproval(false);
    setActiveStep(2);
    setPipelineLogs(prev => [
      ...prev,
      '[FASE 2] Enviando informe médico para anonimización...',
      '[RGPD] Eliminando información personal identificable (GDPR / canal B)...',
      finalDesc
        ? '[FASE 2] Integrando descripción de imagen médica validada por el médico...'
        : '[FASE 2] Omitiendo descripción de imagen médica.',
      '[FASE 2] Llamando API Recog para humanización del informe...',
    ]);

    try {
      const data = await processReport(
        files.report,
        files.studyImage,
        language,
        describeImage,
        anonymize,
        finalDesc,
        patientId,
        accessionNum,
        studyDesc
      );

      if (data.success) {
        setPipelineLogs(prev => [
          ...prev,
          ...data.logs.map(log => `[FASTAPI] ${log}`),
          '[FASE 3] Generando enlace seguro y PIN de acceso (Magic Link)...',
          '[OK] Pipeline completado correctamente.'
        ]);
        setActiveStep(3);
        setResult(data);

        setTimeout(() => {
          setStep('success');
        }, 1200);
      } else {
        setError(data.error || { phase: 'Error del Servidor', message: 'No se pudo completar el proceso.' });
        setStep('form');
      }
    } catch (err) {
      handlePipelineError(err);
    } finally {
      setLoading(false);
    }
  };

  const handlePipelineError = (err) => {
    console.error(err);
    setError({
      phase: 'Error de Red / Conexión',
      message: 'No se pudo comunicar con el servidor backend FastAPI. Asegúrate de que está ejecutándose en el puerto 8000.',
      actions: ['Inicia el backend usando: python -m uvicorn background.main:app --reload --port 8000'],
      technical: err.toString() + '\n' + err.stack
    });
    setStep('form');
    setLoading(false);
  };

  const handleReset = () => {
    setFiles({ report: null, studyImage: null });
    setLanguage('es');
    setDescribeImage(false);
    setAnonymize(true);
    setPatientId('');
    setAccessionNum('');
    setStudyDesc('');
    setResult(null);
    setError(null);
    setStep('form');
  };

  const isProgress = step === 'progress';

  const footer = (
    <footer className="bg-white border-t border-slate-100 px-6 py-10 text-center text-xs text-slate-400 shrink-0">
      <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="flex flex-col items-center md:items-start gap-1">
          <p className="font-bold text-slate-700 text-sm">© 2026 Hackathon IABiomed</p>
          <p className="text-slate-400">Desarrollado por el equipo SINAI-UJA.</p>
        </div>
        <div className="flex items-center gap-6">
          <a href="https://sinai.ujaen.es/" target="_blank" rel="noopener noreferrer">
            <img src="/sinai_logo.png" alt="SINAI Logo" className="h-10 object-contain hover:scale-105 transition-transform duration-300" />
          </a>
          <a href="https://www.ujaen.es/" target="_blank" rel="noopener noreferrer">
            <img src="/uja_logo.png" alt="UJA Logo" className="h-10 object-contain hover:scale-105 transition-transform duration-300" />
          </a>
          <a href="https://www.iabiomed.es/" target="_blank" rel="noopener noreferrer">
            <img src="/biomed_logo.png" alt="BIOMED Logo" className="h-10 object-contain hover:scale-105 transition-transform duration-300" />
          </a>
        </div>
      </div>
    </footer>
  );

  // Modo progress: pantalla completa con footer visible al final
  if (isProgress) {
    return (
      <div className="min-h-screen flex flex-col bg-slate-50">
        <header className="shrink-0 z-30 bg-gradient-to-r from-brand-700 via-brand-600 to-brand-500 border-b border-brand-600 px-6 py-4 shadow-md shadow-brand-700/30">
          <div className="max-w-6xl mx-auto flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-white/20 backdrop-blur-sm text-white flex items-center justify-center shadow-md ring-1 ring-white/25">
                <Brain size={22} />
              </div>
              <div>
                <h1 className="text-base font-bold text-white tracking-tight leading-none">Portal IABiomed — Reto Idonia</h1>
                <span className="text-[10px] text-blue-100 font-medium tracking-wide uppercase mt-1 block">SINAI-UJA 2026</span>
              </div>
            </div>
          </div>
        </header>
        <main className="flex-1 min-h-0 overflow-hidden">
          <PipelineProgress
            reportFile={files.report}
            studyImageFile={files.studyImage}
            describeImageActive={describeImage}
            isWaitingForApproval={isWaitingForApproval}
            isDescribing={isDescribing}
            descriptionText={imageDescription}
            setDescriptionText={setImageDescription}
            onApproveDescription={() => executeFullPipeline(imageDescription)}
            activeStep={activeStep}
            logs={pipelineLogs}
            loading={loading}
          />
        </main>
        <ErrorAgentMascot error={error} clearError={() => setError(null)} />
        {footer}
      </div>
    );
  }

  // Modo form / success: layout normal con scroll y footer al final
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <header className="sticky top-0 z-30 bg-gradient-to-r from-brand-700 via-brand-600 to-brand-500 border-b border-brand-600 px-6 py-4 shadow-md shadow-brand-700/30">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-white/20 backdrop-blur-sm text-white flex items-center justify-center shadow-md ring-1 ring-white/25">
              <Brain size={22} />
            </div>
            <div>
              <h1 className="text-base font-bold text-white tracking-tight leading-none">Portal IABiomed — Reto Idonia</h1>
              <span className="text-[10px] text-blue-100 font-medium tracking-wide uppercase mt-1 block">SINAI-UJA 2026</span>
            </div>
          </div>
        </div>
      </header>

      <main className="flex-1 w-full max-w-4xl mx-auto px-6 py-10">
        {step === 'form' && (
          <div className="space-y-6">
            <div className="text-center max-w-2xl mx-auto mb-10 group">
              <h2 className="text-3xl font-black text-slate-900 tracking-tight sm:text-4xl transition-all duration-300 transform group-hover:scale-105 bg-gradient-to-r from-slate-900 via-brand-600 to-indigo-600 bg-[size:200%] bg-left group-hover:bg-right bg-clip-text group-hover:text-transparent cursor-pointer select-none">
                Humanización de Informes Médicos
              </h2>
              <p className="text-sm text-slate-500 mt-3">
                Interoperabilidad regional segura y traducción en lenguaje claro para el paciente a través de inteligencia artificial médica.
              </p>
            </div>
            <PatientForm
              files={files}
              setFiles={setFiles}
              language={language}
              setLanguage={setLanguage}
              describeImage={describeImage}
              setDescribeImage={setDescribeImage}
              anonymize={anonymize}
              setAnonymize={setAnonymize}
              patientId={patientId}
              setPatientId={setPatientId}
              accessionNum={accessionNum}
              setAccessionNum={setAccessionNum}
              studyDesc={studyDesc}
              setStudyDesc={setStudyDesc}
              onSubmit={handleSubmit}
              loading={loading}
            />
          </div>
        )}

        {step === 'success' && result && (
          <SuccessScreen result={result} onReset={handleReset} />
        )}
      </main>

      {footer}

      <ErrorAgentMascot error={error} clearError={() => setError(null)} />
    </div>
  );
}