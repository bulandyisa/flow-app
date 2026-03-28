import { useState, useRef } from 'react';
import { Upload, FileText, CheckCircle, ChevronDown, ChevronRight } from 'lucide-react';
import { api } from '@/api/client';

interface ScreenplayUploadProps {
  projectId: string;
  hasScreenplay: boolean;
  onUploaded: () => void;
}

export function ScreenplayUpload({ projectId, hasScreenplay, onUploaded }: ScreenplayUploadProps) {
  const [uploading, setUploading] = useState(false);
  const [preview, setPreview] = useState<string[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleUpload = async (file: File) => {
    if (!file.name.endsWith('.docx')) {
      setError('Только .docx файлы');
      return;
    }

    setUploading(true);
    setError(null);
    try {
      const result = await api.uploadScreenplay(projectId, file);
      setPreview(result.paragraphs || []);
      onUploaded();
    } catch (err) {
      setError(String(err));
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file);
  };

  // Загрузка существующего сценария для превью
  const loadPreview = async () => {
    try {
      const result = await api.getScreenplay(projectId);
      setPreview(result.paragraphs || []);
    } catch { /* нет сценария */ }
  };

  // Если сценарий уже загружен и превью нет — подгрузить
  if (hasScreenplay && !preview) {
    loadPreview();
  }

  return (
    <div>
      {/* Зона загрузки */}
      {!hasScreenplay ? (
        <div
          onDrop={handleDrop}
          onDragOver={(e) => e.preventDefault()}
          className="border-2 border-dashed border-surface-lighter rounded-lg p-12 text-center hover:border-accent transition-colors"
        >
          <Upload size={48} className="mx-auto text-gray-500 mb-4" />
          <h2 className="text-xl font-medium mb-2">Загрузите сценарий</h2>
          <p className="text-gray-400 mb-6">
            Перетащите .docx файл сюда или нажмите кнопку
          </p>
          <label className="inline-flex items-center gap-2 px-6 py-3 bg-accent hover:bg-accent-hover rounded-lg cursor-pointer transition-colors">
            <Upload size={18} />
            <span>{uploading ? 'Загрузка...' : 'Выбрать файл'}</span>
            <input
              ref={fileRef}
              type="file"
              accept=".docx"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleUpload(file);
              }}
            />
          </label>
        </div>
      ) : (
        <div className="flex items-center gap-3 p-4 bg-green-900/20 border border-green-800/30 rounded-lg mb-4">
          <CheckCircle size={20} className="text-green-400" />
          <span className="text-green-300">Сценарий загружен</span>
          <label className="ml-auto text-sm text-gray-400 hover:text-white cursor-pointer transition-colors">
            Заменить
            <input
              type="file"
              accept=".docx"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleUpload(file);
              }}
            />
          </label>
        </div>
      )}

      {error && (
        <p className="mt-2 text-sm text-red-400">{error}</p>
      )}

      {/* Полный текст сценария */}
      {preview && preview.length > 0 && (
        <ScreenplayViewer paragraphs={preview} />
      )}
    </div>
  );
}

/** Разбивает абзацы на части и показывает в выпадающих блоках */
function ScreenplayViewer({ paragraphs }: { paragraphs: string[] }) {
  const CHUNK_SIZE = Math.ceil(paragraphs.length / 10);
  const chunks: string[][] = [];
  for (let i = 0; i < paragraphs.length; i += CHUNK_SIZE) {
    chunks.push(paragraphs.slice(i, i + CHUNK_SIZE));
  }

  const [openChunks, setOpenChunks] = useState<Set<number>>(new Set([0]));

  const toggle = (idx: number) => {
    setOpenChunks((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  return (
    <div className="mt-4">
      <h3 className="flex items-center gap-2 text-sm font-medium text-gray-400 mb-2">
        <FileText size={14} />
        Сценарий ({paragraphs.length} абзацев)
      </h3>
      <div className="space-y-1">
        {chunks.map((chunk, idx) => {
          const isOpen = openChunks.has(idx);
          const startP = idx * CHUNK_SIZE + 1;
          const endP = Math.min((idx + 1) * CHUNK_SIZE, paragraphs.length);

          return (
            <div key={idx} className="bg-surface rounded-lg border border-surface-lighter overflow-hidden">
              <button
                onClick={() => toggle(idx)}
                className="w-full flex items-center gap-2 px-4 py-2 text-sm text-gray-400 hover:text-gray-200 transition-colors"
              >
                {isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                <span>Часть {idx + 1} — абзацы {startP}–{endP}</span>
              </button>
              {isOpen && (
                <div className="px-4 pb-3 text-sm text-gray-300 space-y-2">
                  {chunk.map((p, i) => (
                    <p key={i}>{p}</p>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
