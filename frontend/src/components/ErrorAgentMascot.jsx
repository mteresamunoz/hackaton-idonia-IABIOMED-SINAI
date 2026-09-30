import React, { useState, useEffect } from 'react';
import { X, Sparkles, AlertCircle, ChevronDown, ChevronUp, Copy, Check } from 'lucide-react';

function CopyableCommand({ command }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = (e) => {
    e.stopPropagation();
    navigator.clipboard.writeText(command);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-slate-950 border border-slate-800 rounded-xl p-3 font-mono text-xs text-slate-300 flex justify-between items-center gap-3">
      <code className="text-slate-200 select-all break-all overflow-x-auto">{command}</code>
      <button
        type="button"
        onClick={handleCopy}
        className="shrink-0 p-1.5 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-white transition border border-transparent hover:border-slate-700"
        title="Copiar comando"
      >
        {copied ? <Check size={14} className="text-green-500" /> : <Copy size={14} />}
      </button>
    </div>
  );
}

export default function ErrorAgentMascot({ error, clearError }) {
  const hasError = !!error;
  const [isOpen, setIsOpen] = useState(false);
  const [animState, setAnimState] = useState('idle'); // 'idle', 'jumping', 'flying', 'center', 'flying-back'
  const [showTechnical, setShowTechnical] = useState(false);
  const [copiedTechnical, setCopiedTechnical] = useState(false);

  // Auto-open tooltip when an error occurs or trigger the animations
  useEffect(() => {
    if (hasError) {
      setIsOpen(false); // Close normal tooltip if it was open
      setShowTechnical(false);
      setAnimState('jumping');
      
      const timer1 = setTimeout(() => {
        setAnimState('flying');
      }, 800); // Wait for the jump animation (0.8s) to complete
      
      const timer2 = setTimeout(() => {
        setAnimState('center');
      }, 2000); // 800ms jump + 1200ms flying = 2000ms total
      
      return () => {
        clearTimeout(timer1);
        clearTimeout(timer2);
      };
    } else {
      if (animState !== 'idle') {
        setAnimState('flying-back');
        const timer = setTimeout(() => {
          setAnimState('idle');
        }, 1200); // Wait for flight-back to finish
        return () => clearTimeout(timer);
      }
    }
  }, [hasError]);

  const handleDismiss = () => {
    if (clearError) {
      clearError();
    }
  };

  const copyTechnicalDetails = (e) => {
    e.stopPropagation();
    if (error?.technical) {
      navigator.clipboard.writeText(error.technical);
      setCopiedTechnical(true);
      setTimeout(() => setCopiedTechnical(false), 2000);
    }
  };

  let mascotClass = "";
  if (animState === 'jumping') {
    mascotClass = "mascot-jumping";
  } else if (animState === 'flying' || animState === 'center') {
    mascotClass = "mascot-center";
  } else if (animState === 'flying-back') {
    mascotClass = "mascot-back";
  }

  return (
    <>
      <style>{`
        @keyframes bandAidFloat {
          0%, 100% { transform: translateY(0px) rotate(-1deg); }
          50% { transform: translateY(-3px) rotate(1deg); }
        }
        
        @keyframes mascot-bounce-up {
          0% {
            transform: scale(1) translateY(0);
          }
          15% {
            transform: scale(1.3, 0.7) translateY(0);
          }
          30% {
            transform: scale(0.8, 1.25) translateY(-35px);
          }
          45% {
            transform: scale(1.1, 0.95) translateY(0);
          }
          60% {
            transform: scale(0.95, 1.05) translateY(-10px);
          }
          75% {
            transform: scale(1.02, 0.98) translateY(0);
          }
          100% {
            transform: scale(2.2) translateY(0);
          }
        }

        @keyframes leg-swing-left {
          0%, 100% { transform: rotate(-25deg); }
          50% { transform: rotate(25deg); }
        }
        
        @keyframes leg-swing-right {
          0%, 100% { transform: rotate(25deg); }
          50% { transform: rotate(-25deg); }
        }

        .left-leg {
          transform-origin: 52px 108px;
          animation: leg-swing-left 0.15s infinite ease-in-out;
        }

        .right-leg {
          transform-origin: 68px 108px;
          animation: leg-swing-right 0.15s infinite ease-in-out;
        }

        .mascot-jumping {
          animation: mascot-bounce-up 0.8s cubic-bezier(0.25, 1, 0.5, 1) forwards;
          transform-origin: bottom center;
        }

        .mascot-center {
          transform: translate(calc(-50vw + 350px), calc(-50vh + 56px)) scale(1.4);
          transition: transform 1.2s cubic-bezier(0.25, 1, 0.5, 1);
          transform-origin: bottom center;
        }

        @media (max-width: 768px) {
          .mascot-center {
            transform: translate(calc(-50vw + 56px), calc(-50vh + 56px - 220px)) scale(1.2);
          }
        }

        .mascot-back {
          transform: translate(0, 0) scale(1);
          transition: transform 1.2s cubic-bezier(0.25, 1, 0.5, 1);
          transform-origin: bottom center;
        }

        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }

        .animate-fade-in {
          animation: fadeIn 0.3s ease-out forwards;
        }

        @keyframes scaleUp {
          from { transform: scale(0.95); opacity: 0; }
          to { transform: scale(1); opacity: 1; }
        }

        .animate-scale-up {
          animation: scaleUp 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
        }
      `}</style>

      {/* Mascot Button in Fixed Corner */}
      <div 
        className={`fixed bottom-6 right-6 z-50 flex flex-col items-end gap-3 select-none ${mascotClass}`}
        style={{ pointerEvents: animState === 'flying' || animState === 'center' ? 'none' : 'auto' }}
      >
        {/* Dialogue Box (Only for user-initiated clicks when there's no error) */}
        {isOpen && !hasError && (
          <div className="relative w-72 max-w-[calc(100vw-2rem)] rounded-2xl border border-slate-100 bg-white p-3.5 shadow-md animate-fade-in">
            <button
              type="button"
              onClick={() => setIsOpen(false)}
              className="absolute right-2.5 top-2.5 rounded-lg p-0.5 text-slate-400 transition hover:bg-slate-50 hover:text-slate-600"
              aria-label="Cerrar"
            >
              <X size={13} />
            </button>

            <div className="flex gap-2.5 pr-4">
              <div className="shrink-0 pt-0.5">
                <BandAidIcon hasError={false} size="sm" />
              </div>

              <div>
                <div className="mb-0.5 flex items-center gap-1">
                  <Sparkles className="h-3.5 w-3.5 text-slate-400" />
                  <h4 className="text-[11px] font-bold text-slate-800">
                    Soporte de Tirita
                  </h4>
                </div>

                <p className="text-[10px] leading-relaxed text-slate-500">
                  Si algún paso falla, estaré aquí para ayudarte a sanar el error.
                </p>
              </div>
            </div>

            <div className="absolute bottom-[-5px] right-7 h-2 w-2 rotate-45 border-b border-r border-slate-100 bg-white" />
          </div>
        )}

        {/* Mascot Button */}
        <button
          type="button"
          onClick={() => !hasError && setIsOpen(!isOpen)}
          className="group relative flex h-16 w-16 items-center justify-center transition-all duration-300 hover:scale-110 active:scale-95"
          title={hasError ? "Detalles del Error" : "Asistente de Soporte"}
          disabled={hasError}
        >
          <BandAidIcon hasError={hasError} size="lg" />
        </button>
      </div>

      {/* Explanatory Error Modal */}
      {animState === 'center' && error && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-950/75 backdrop-blur-md animate-fade-in">
          {/* Clickable backdrop area to dismiss error */}
          <div className="absolute inset-0 cursor-default" onClick={handleDismiss} />
          
          {/* Modal Card */}
          <div className="relative w-full max-w-lg mx-4 bg-slate-900 border border-slate-800/80 rounded-3xl shadow-[0_0_50px_rgba(239,68,68,0.22)] overflow-hidden animate-scale-up z-50 flex flex-col">
            {/* Premium Red Glow Top Border */}
            <div className="h-1.5 w-full bg-gradient-to-r from-amber-500 via-rose-500 to-red-600" />
            
            {/* Close Button Top Right */}
            <button
              type="button"
              onClick={handleDismiss}
              className="absolute right-4 top-4 rounded-xl p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 transition"
              aria-label="Cerrar modal de error"
            >
              <X size={18} />
            </button>
            
            <div className="p-6 md:p-8 flex flex-col gap-5">
              {/* Title and Icon */}
              <div className="flex items-center gap-3 mt-4">
                <div className="p-2.5 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-500">
                  <AlertCircle size={24} />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-bold tracking-wider uppercase bg-red-500/10 text-red-400 px-2.5 py-0.5 rounded-full border border-red-500/20">
                      {error.phase || 'Error'}
                    </span>
                  </div>
                  <h3 className="text-xl font-extrabold text-white mt-1">
                    Se ha detectado una anomalía
                  </h3>
                </div>
              </div>

              {/* User-Friendly Error Message */}
              <div className="bg-slate-950/45 border border-slate-800/50 rounded-2xl p-4">
                <p className="text-sm text-slate-300 leading-relaxed font-medium">
                  {error.message || 'Ha ocurrido un error inesperado al procesar el informe médico.'}
                </p>
              </div>

              {/* Suggested Actions */}
              {error.actions && error.actions.length > 0 && (
                <div className="flex flex-col gap-2">
                  <h4 className="text-[10px] font-extrabold uppercase tracking-widest text-amber-400/90">
                    Acciones sugeridas
                  </h4>
                  <div className="flex flex-col gap-2">
                    {error.actions.map((action, idx) => {
                      const isCommand = action.includes('python') || action.includes('uvicorn') || action.includes('npm') || action.includes('run');
                      if (isCommand) {
                        return (
                          <div key={idx} className="flex flex-col gap-1.5">
                            <p className="text-xs text-slate-400">Ejecuta el siguiente comando en la terminal:</p>
                            <CopyableCommand command={action} />
                          </div>
                        );
                      }
                      return (
                        <div key={idx} className="flex items-start gap-2 text-xs text-slate-300">
                          <span className="mt-1.5 flex h-1.5 w-1.5 shrink-0 rounded-full bg-amber-400" />
                          <span>{action}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Technical Details Accordion */}
              {error.technical && (
                <div className="border border-slate-800 rounded-2xl overflow-hidden mt-1">
                  <button
                    type="button"
                    onClick={() => setShowTechnical(!showTechnical)}
                    className="w-full px-4 py-3 bg-slate-950/40 hover:bg-slate-950/60 flex items-center justify-between text-xs text-slate-400 font-semibold transition"
                  >
                    <span>Detalles técnicos del error</span>
                    {showTechnical ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                  </button>
                  {showTechnical && (
                    <div className="p-4 bg-slate-950 border-t border-slate-800 relative">
                      <button
                        type="button"
                        onClick={copyTechnicalDetails}
                        className="absolute right-3 top-3 text-slate-400 hover:text-white transition bg-slate-900 border border-slate-800 hover:border-slate-700 p-1.5 rounded-lg"
                        title="Copiar traza técnica"
                      >
                        {copiedTechnical ? <Check size={14} className="text-green-500" /> : <Copy size={14} />}
                      </button>
                      <pre className="text-[10px] font-mono text-rose-300/80 overflow-x-auto whitespace-pre-wrap max-h-36 pr-8">
                        {error.technical}
                      </pre>
                    </div>
                  )}
                </div>
              )}

              {/* Action Button */}
              <button
                type="button"
                onClick={handleDismiss}
                className="w-full mt-2 py-3.5 bg-gradient-to-r from-rose-500 to-red-600 hover:from-rose-600 hover:to-red-700 text-white font-bold rounded-xl text-sm shadow-lg shadow-rose-900/35 hover:shadow-rose-900/50 hover:scale-[1.01] active:scale-[0.99] transition-all duration-200"
              >
                Entendido, cerrar
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function BandAidIcon({ hasError, size = 'lg' }) {
  const isSmall = size === 'sm';
  const width = isSmall ? '36' : '56';
  const height = isSmall ? '36' : (hasError ? '62' : '56');

  return (
    <div className={!hasError ? 'animate-[bandAidFloat_3s_ease-in-out_infinite]' : 'animate-bounce'}>
      <svg
        width={width}
        height={height}
        viewBox={hasError ? "0 0 120 130" : "0 0 120 120"}
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="drop-shadow-md"
      >
        {hasError && (
          <>
            {/* Left Leg */}
            <path
              d="M52 108 C50 118, 46 122, 42 122"
              stroke="#C79558"
              strokeWidth="4"
              strokeLinecap="round"
              fill="none"
              className="left-leg"
            />
            {/* Right Leg */}
            <path
              d="M68 108 C70 118, 74 122, 78 122"
              stroke="#C79558"
              strokeWidth="4"
              strokeLinecap="round"
              fill="none"
              className="right-leg"
            />
          </>
        )}
        {/* 1. Vertical Band-aid */}
        <rect
          x="46"
          y="10"
          width="28"
          height="100"
          rx="14"
          fill="#FCEFD9"
          stroke="#C79558"
          strokeWidth="3.2"
        />

        {/* 2. Horizontal Band-aid */}
        <rect
          x="10"
          y="46"
          width="100"
          height="28"
          rx="14"
          fill="#FCEFD9"
          stroke="#C79558"
          strokeWidth="3.2"
        />

        {/* Dots - Left Side */}
        <circle cx="20" cy="53" r="1.8" fill="#E4C097" />
        <circle cx="28" cy="53" r="1.8" fill="#E4C097" />
        <circle cx="20" cy="67" r="1.8" fill="#E4C097" />
        <circle cx="28" cy="67" r="1.8" fill="#E4C097" />

        {/* Dots - Right Side */}
        <circle cx="92" cy="53" r="1.8" fill="#E4C097" />
        <circle cx="100" cy="53" r="1.8" fill="#E4C097" />
        <circle cx="92" cy="67" r="1.8" fill="#E4C097" />
        <circle cx="100" cy="67" r="1.8" fill="#E4C097" />

        {/* Dots - Face Area */}
        <circle cx="51" cy="27" r="1.8" fill="#E4C097" />
        <circle cx="51" cy="37" r="1.8" fill="#E4C097" />
        <circle cx="69" cy="27" r="1.8" fill="#E4C097" />
        <circle cx="69" cy="37" r="1.8" fill="#E4C097" />

        {/* Minimalist Face (Slightly larger details) */}
        {/* Left Eye */}
        <circle cx="53.5" cy="30" r="2.8" fill="#3A2312" />

        {/* Right Eye */}
        <circle cx="66.5" cy="30" r="2.8" fill="#3A2312" />

        {/* Rosy Cheeks (Larger & Softer) */}
        <ellipse cx="49" cy="34.5" rx="3.5" ry="2" fill="#FFB3B3" opacity="0.85" />
        <ellipse cx="71" cy="34.5" rx="3.5" ry="2" fill="#FFB3B3" opacity="0.85" />

        {/* Mouth */}
        {hasError ? (
          // Slightly larger circle for concern
          <circle cx="60" cy="38" r="1.8" fill="#3A2312" />
        ) : (
          // Slightly larger smile
          <path
            d="M56 35.8C57.2 38.2 62.8 38.2 64 35.8"
            stroke="#3A2312"
            strokeWidth="2.2"
            strokeLinecap="round"
          />
        )}

        {/* 3. Center White Pad */}
        <rect
          x="44"
          y="44"
          width="32"
          height="32"
          rx="7"
          fill="#FFFFFF"
          stroke="#C79558"
          strokeWidth="3.2"
        />

        {/* Red Medical Cross */}
        <rect
          x="57.5"
          y="50.5"
          width="5"
          height="19"
          rx="1.2"
          fill="#EB4861"
        />
        <rect
          x="50.5"
          y="57.5"
          width="19"
          height="5"
          rx="1.2"
          fill="#EB4861"
        />
      </svg>
    </div>
  );
}