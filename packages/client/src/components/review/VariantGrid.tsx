import { useState } from 'react';
import { Download } from 'lucide-react';
import { Lightbox } from './Lightbox';

interface Variant {
  index: number;
  src: string;       // URL к медиа
  isVideo: boolean;
}

interface VariantGridProps {
  clipId: string;
  component: string;
  attemptNum: number;
  variants: Variant[];
  selectedIndex: number | null;
  onSelect: (index: number) => void;
}

export function VariantGrid({
  clipId,
  component,
  attemptNum,
  variants,
  selectedIndex,
  onSelect,
}: VariantGridProps) {
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

  const componentLabels: Record<string, string> = {
    nb_first: 'Первый кадр',
    veo: 'Видео',
  };

  const lightboxImages = variants
    .filter((v) => !v.isVideo)
    .map((v) => ({ src: v.src, caption: `${clipId} — ${componentLabels[component] || component} — Вариант ${v.index + 1}` }));

  return (
    <div className="mt-3">
      {/* Заголовок компонента */}
      <div className="flex items-center gap-2 mb-2">
        <span className="text-sm font-medium text-amber-400 uppercase tracking-wider">
          {componentLabels[component] || component}
        </span>
        <span className="text-xs text-gray-500">
          попытка {attemptNum} ({variants.length} вариантов)
        </span>
      </div>

      {/* Сетка 2 колонки */}
      <div className="grid grid-cols-2 gap-3">
        {variants.map((variant) => {
          const isSelected = selectedIndex === variant.index;

          return (
            <div
              key={variant.index}
              className={`rounded-lg border-2 overflow-hidden transition-colors ${
                isSelected
                  ? 'border-accent bg-accent/5'
                  : 'border-surface-lighter hover:border-gray-500'
              }`}
            >
              {/* Медиа */}
              {variant.isVideo ? (
                <div>
                  <video
                    src={variant.src}
                    controls
                    className="w-full aspect-video bg-black"
                    preload="metadata"
                  />
                  <a
                    href={variant.src}
                    download
                    className="flex items-center justify-center gap-1 py-1.5 text-xs text-gray-400 hover:text-white transition-colors bg-surface-light"
                  >
                    <Download size={12} />
                    Скачать
                  </a>
                </div>
              ) : (
                <img
                  src={variant.src}
                  alt={`Вариант ${variant.index + 1}`}
                  className="w-full cursor-pointer"
                  loading="lazy"
                  onClick={() => {
                    const lbIdx = lightboxImages.findIndex((img) => img.src === variant.src);
                    if (lbIdx >= 0) setLightboxIndex(lbIdx);
                  }}
                />
              )}

              {/* Checkbox выбора */}
              <label
                className={`flex items-center gap-2 px-3 py-2 cursor-pointer transition-colors ${
                  isSelected ? 'bg-accent/10' : 'bg-surface-light hover:bg-surface-lighter'
                }`}
              >
                <input
                  type="checkbox"
                  checked={isSelected}
                  onChange={() => onSelect(variant.index)}
                  className="accent-accent"
                />
                <span className="text-sm">Вариант {variant.index + 1}</span>
              </label>
            </div>
          );
        })}
      </div>

      {/* Lightbox */}
      {lightboxIndex !== null && (
        <Lightbox
          images={lightboxImages}
          currentIndex={lightboxIndex}
          onClose={() => setLightboxIndex(null)}
          onNavigate={setLightboxIndex}
        />
      )}
    </div>
  );
}
