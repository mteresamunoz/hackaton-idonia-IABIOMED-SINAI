import React, { useState } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import { Check, Copy, ExternalLink, FileText } from 'lucide-react';

export default function SuccessScreen({ result }) {
  const [copied, setCopied] = useState(false);
  const [copiedPin, setCopiedPin] = useState(false);

  const magicLink = result.magic_link_url;
  const pin = result.pin;

  const copyToClipboard = () => {
    navigator.clipboard.writeText(`Magic Link: ${magicLink}\nPIN: ${pin}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const copyPin = () => {
    navigator.clipboard.writeText(pin || '');
    setCopiedPin(true);
    setTimeout(() => setCopiedPin(false), 2000);
  };

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Magic Link & Access Details */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 bg-white p-6 rounded-3xl border border-slate-100">
        <div className="md:col-span-2 space-y-4">
          <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2">
            <FileText size={18} className="text-brand-600" />
            Acceso directo
          </h3>
          <p className="text-xs text-slate-500">
            Comparte este enlace y código PIN de acceso. Permite acceder de forma segura a los informes e imágenes médicas sin necesidad de registro previo.
          </p>

          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-600">Magic Link URL</label>
            <div className="flex gap-2">
              <input
                type="text"
                readOnly
                value={magicLink}
                className="w-full bg-slate-50 border border-slate-100 rounded-xl px-4 py-2.5 text-xs text-slate-600 focus:outline-none"
              />
              <button
                type="button"
                onClick={copyToClipboard}
                className="px-4 bg-slate-50 hover:bg-slate-100 border border-slate-100 rounded-xl text-slate-500 hover:text-slate-700 transition-all flex items-center justify-center shrink-0"
              >
                {copied ? <Check size={16} className="text-emerald-500" /> : <Copy size={16} />}
              </button>
              <a
                href={magicLink}
                target="_blank"
                rel="noreferrer"
                className="px-4 bg-brand-600 hover:bg-brand-700 text-white rounded-xl flex items-center justify-center shrink-0 transition-all shadow-sm"
              >
                <ExternalLink size={16} />
              </a>
            </div>
          </div>

          <div className="flex gap-6 pt-2">
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-400">Código PIN</span>
              <div className="mt-1 flex items-center gap-2">
                <p className="text-xl font-bold text-slate-900 tracking-wider">{pin || 'N/A'}</p>
                <button
                  type="button"
                  onClick={copyPin}
                  className="px-2.5 py-1 text-xs bg-slate-50 hover:bg-slate-100 border border-slate-100 rounded-lg flex items-center gap-1.5 transition-all"
                  aria-label="Copiar código PIN"
                >
                  {copiedPin ? <Check size={14} className="text-emerald-500" /> : <Copy size={14} />}
                  <span>{copiedPin ? 'Copiado' : 'Copiar'}</span>
                </button>
              </div>
            </div>
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-400">Idioma Generado</span>
              <p className="text-sm font-semibold text-slate-700 mt-1 capitalize">{result.language === 'es' ? 'Español' : result.language}</p>
            </div>
          </div>
        </div>

        {/* QR Code */}
        <div className="flex flex-col items-center justify-center p-4 border border-slate-100 rounded-2xl bg-slate-50/50">
          <div className="p-3 bg-white rounded-xl shadow-sm border border-slate-100/70 mb-2">
            {magicLink ? (
              <QRCodeSVG value={magicLink} size={110} level="M" includeMargin={false} />
            ) : (
              <div className="w-[110px] h-[110px] bg-slate-100 rounded-lg flex items-center justify-center text-xs text-slate-400">QR Code</div>
            )}
          </div>
          <span className="text-[10px] font-semibold text-slate-500">Escanea para acceder</span>
        </div>
      </div>
    </div>
  );
}
