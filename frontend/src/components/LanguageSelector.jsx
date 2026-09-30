import React, { useState, useRef, useEffect } from 'react';

const LANGUAGES = [
  { code: 'es', label: 'Español', name: 'Español' },
  { code: 'ca', label: 'Català', name: 'Català' },
  { code: 'va', label: 'Valencià', name: 'Valencià' },
  { code: 'gl', label: 'Galego', name: 'Galego' },
  { code: 'eu', label: 'Euskara', name: 'Euskara' }
];

export default function LanguageSelector({ selected, onChange }) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  const selectedLang = LANGUAGES.find(lang => lang.code === selected) || LANGUAGES[0];

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Dropdown Toggle Button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between gap-2 bg-slate-50 border border-slate-200 hover:border-slate-300 rounded-xl py-2 px-3 text-xs font-semibold text-slate-700 transition-all duration-200 shadow-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20"
      >
        <div className="flex items-center gap-2">
          <span>{selectedLang.label}</span>
        </div>
        <svg
          className={`w-4 h-4 text-slate-500 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Dropdown Options Menu */}
      {isOpen && (
        <div className="absolute left-0 right-0 mt-1.5 bg-white border border-slate-200 rounded-xl shadow-lg z-50 py-1 overflow-hidden animate-fade-in">
          {LANGUAGES.map((lang) => {
            const isSelected = selected === lang.code;
            return (
              <button
                key={lang.code}
                type="button"
                onClick={() => {
                  onChange(lang.code);
                  setIsOpen(false);
                }}
                className={`w-full flex items-center gap-2 px-3 py-2 text-left text-xs transition-colors duration-150 ${
                  isSelected
                    ? 'bg-slate-50 font-bold text-slate-800'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-800'
                }`}
              >
                <span className="flex-1">{lang.label}</span>
                {isSelected && (
                  <svg className="w-3.5 h-3.5 text-brand-600 font-bold" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                  </svg>
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

