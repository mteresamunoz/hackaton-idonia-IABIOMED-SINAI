import React, { useRef, useState } from 'react';
import { Upload, File, X } from 'lucide-react';

export default function FileUploader({ id, accept, selectedFile, setSelectedFile, placeholder }) {
  const fileInputRef = useRef(null);
  const [dragActive, setDragActive] = useState(false);

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
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setSelectedFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const clearFile = (e) => {
    e.stopPropagation();
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const formatSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div
      onDragEnter={handleDrag}
      onDragOver={handleDrag}
      onDragLeave={handleDrag}
      onDrop={handleDrop}
      onClick={() => fileInputRef.current.click()}
      className={`border-2 border-dashed rounded-xl p-6 flex flex-col items-center justify-center cursor-pointer transition-all ${
        dragActive 
          ? 'border-brand-500 bg-brand-50/50 scale-[0.99]' 
          : selectedFile 
            ? 'border-emerald-300 bg-emerald-50/10' 
            : 'border-slate-200 hover:border-brand-300 hover:bg-slate-50/50'
      }`}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept={accept}
        onChange={handleFileChange}
        className="hidden"
      />

      {selectedFile ? (
        <div className="w-full flex items-center justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <div className="p-3 bg-emerald-50 text-emerald-600 rounded-lg shrink-0">
              <File size={20} />
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium text-slate-800 truncate">{selectedFile.name}</p>
              <p className="text-xs text-slate-400">{formatSize(selectedFile.size)}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={clearFile}
            className="p-1.5 hover:bg-slate-100 rounded-full text-slate-400 hover:text-slate-600 shrink-0"
          >
            <X size={16} />
          </button>
        </div>
      ) : (
        <div className="text-center">
          <div className="mx-auto w-10 h-10 bg-slate-50 text-slate-400 rounded-lg flex items-center justify-center mb-3">
            <Upload size={20} />
          </div>
          <p className="text-sm font-medium text-slate-700">{placeholder}</p>
          <p className="text-xs text-slate-400 mt-1">Soporta {accept.replace(/image\/\*/g, 'imágenes')}</p>
        </div>
      )}
    </div>
  );
}
