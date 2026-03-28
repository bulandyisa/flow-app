import { useState } from 'react';
import { StatusBadge } from './StatusBadge';
import { VariantGrid } from './VariantGrid';
import { FeedbackForm } from './FeedbackForm';
import { Lock, RotateCcw } from 'lucide-react';

interface ComponentData {
  name: string;
  status: string;
  attemptNum: number;
  variants: Array<{
    index: number;
    src: string;
    isVideo: boolean;
  }>;
}

interface AcceptedFrame {
  src: string;
  label: string;
  component: string;
}

interface ClipCardProps {
  clipId: string;
  sceneId: string;
  description: string;
  components: ComponentData[];
  acceptedFrames: AcceptedFrame[];
  selections: Record<string, number | null>;   // component -> selected variant index
  feedbacks: Record<string, string>;            // component -> feedback text
  onSelect: (component: string, variantIndex: number) => void;
  onFeedbackChange: (component: string, value: string) => void;
  chainBlocked?: boolean;
  onRevoke?: (component: string, feedback?: string) => void;
}

export function ClipCard({
  clipId,
  sceneId,
  description,
  components,
  acceptedFrames,
  selections,
  feedbacks,
  onSelect,
  onFeedbackChange,
  chainBlocked,
  onRevoke,
}: ClipCardProps) {
  const [revokeComponent, setRevokeComponent] = useState<string | null>(null);
  const [revokeFeedback, setRevokeFeedback] = useState('');
  const [isRevoking, setIsRevoking] = useState(false);

  // Компоненты, которые на ревью (generated)
  const reviewComponents = components.filter((c) => c.status === 'generated' && c.variants.length > 0);

  const handleRevoke = async (component: string) => {
    if (!onRevoke) return;
    setIsRevoking(true);
    try {
      await onRevoke(component, revokeFeedback.trim() || undefined);
      setRevokeComponent(null);
      setRevokeFeedback('');
    } finally {
      setIsRevoking(false);
    }
  };

  return (
    <div className="py-4 border-b border-surface-lighter last:border-b-0">
      {/* Заголовок клипа */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-3">
          <span className="font-mono font-bold text-white">{clipId}</span>
          <span className="text-sm text-gray-500 truncate max-w-md">{description}</span>
        </div>
        {chainBlocked && (
          <span className="flex items-center gap-1.5 text-xs text-amber-400 bg-amber-900/10 px-2 py-1 rounded">
            <Lock size={12} />
            Chain-заблокирован
          </span>
        )}
      </div>

      {/* Статусы компонентов */}
      <div className="flex items-center gap-3 mb-3">
        {components.map((comp) => (
          <div key={comp.name} className="flex items-center gap-1.5">
            <span className="text-xs text-gray-500">
              {comp.name === 'nb_first' ? 'first' : comp.name}:
            </span>
            <StatusBadge status={comp.status} />
          </div>
        ))}
      </div>

      {/* Принятые кадры (если есть) */}
      {acceptedFrames.length > 0 && (
        <div className="flex gap-3 mb-3">
          {acceptedFrames.map((frame) => (
            <div key={frame.label} className="flex flex-col items-center">
              <img
                src={frame.src}
                alt={frame.label}
                className="w-[250px] rounded-lg border border-surface-lighter"
                loading="lazy"
              />
              <span className="text-xs text-gray-500 mt-1">{frame.label}</span>
              {/* Кнопка "Переделать" */}
              {onRevoke && (
                <div className="mt-1">
                  {revokeComponent === frame.component ? (
                    <div className="flex flex-col gap-1 w-[250px]">
                      <input
                        type="text"
                        value={revokeFeedback}
                        onChange={(e) => setRevokeFeedback(e.target.value)}
                        placeholder="Фидбек (необязательно)"
                        className="px-2 py-1 bg-surface border border-surface-lighter rounded text-xs text-white placeholder-gray-500 focus:outline-none focus:border-accent"
                      />
                      <div className="flex gap-1">
                        <button
                          onClick={() => handleRevoke(frame.component)}
                          disabled={isRevoking}
                          className="flex-1 px-2 py-1 bg-red-900/30 text-red-400 hover:bg-red-900/50 rounded text-xs transition-colors disabled:opacity-40"
                        >
                          {isRevoking ? 'Отзыв...' : 'Подтвердить'}
                        </button>
                        <button
                          onClick={() => { setRevokeComponent(null); setRevokeFeedback(''); }}
                          className="px-2 py-1 bg-surface-light text-gray-400 hover:text-white rounded text-xs transition-colors"
                        >
                          Отмена
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      onClick={() => setRevokeComponent(frame.component)}
                      className="flex items-center gap-1 px-2 py-1 text-xs text-gray-500 hover:text-amber-400 transition-colors"
                    >
                      <RotateCcw size={10} />
                      Переделать
                    </button>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Варианты на ревью */}
      {reviewComponents.map((comp) => (
        <div key={comp.name}>
          <VariantGrid
            clipId={clipId}
            component={comp.name}
            attemptNum={comp.attemptNum}
            variants={comp.variants}
            selectedIndex={selections[comp.name] ?? null}
            onSelect={(vi) => onSelect(comp.name, vi)}
          />
          <FeedbackForm
            clipId={clipId}
            component={comp.name}
            value={feedbacks[comp.name] || ''}
            onChange={(val) => onFeedbackChange(comp.name, val)}
          />
        </div>
      ))}
    </div>
  );
}
