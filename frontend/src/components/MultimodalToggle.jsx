import React from 'react';

export default function MultimodalToggle({ enabled, setEnabled, disabled }) {
  return (
    <div className={`flex items-center justify-between p-4 rounded-xl transition-all ${
      disabled 
        ? 'bg-slate-50 opacity-60 cursor-not-allowed' 
        : 'bg-slate-50'
    }`}>
      <div className="flex flex-col min-w-0 mr-4">
        <span className="text-sm font-semibold text-slate-800">Descripción IA</span>
        <span className="text-xs text-slate-400 truncate">Requiere imagen del estudio</span>
      </div>
      <button
        type="button"
        disabled={disabled}
        onClick={() => setEnabled(!enabled)}
        className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
          disabled 
            ? 'bg-slate-200 cursor-not-allowed' 
            : enabled 
              ? 'bg-brand-600' 
              : 'bg-slate-300'
        }`}
      >
        <span className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
          enabled && !disabled ? 'translate-x-5' : 'translate-x-0'
        }`} />
      </button>
    </div>
  );
}
