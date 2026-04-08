import { useState, useMemo, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import { FileText, ChevronDown, ChevronRight, Send, Loader2, Search, X } from 'lucide-react';

interface Clip {
  clip_id: string;
  scene_id: string;
  scene_description_ru: string;
  nano_banana_ingredients: string[];
  nano_banana_prompt_first: string;
  veo_prompt: string;
}

export function Clips() {
  const { id: projectId } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const { data: clips, isLoading } = useQuery({
    queryKey: ['clips', projectId],
    queryFn: () => api.getClips(projectId!),
    enabled: !!projectId,
  });

  const [expandedClip, setExpandedClip] = useState<string | null>(null);
  const [feedbacks, setFeedbacks] = useState<Record<string, Record<string, string>>>({});
  const [fixing, setFixing] = useState<string | null>(null); // clip_id currently fixing
  const [model, setModel] = useState<'sonnet' | 'opus'>('sonnet');
  const [search, setSearch] = useState('');
  const [translations, setTranslations] = useState<Record<string, Record<string, string>>>({});
  const [translating, setTranslating] = useState<string | null>(null);

  const allClips = (clips || []) as Clip[];

  // Фильтрация по поиску
  const filteredClips = useMemo(() => {
    if (!search.trim()) return allClips;
    const q = search.toLowerCase();
    return allClips.filter((c) =>
      c.clip_id.toLowerCase().includes(q) ||
      c.scene_id.toLowerCase().includes(q) ||
      c.scene_description_ru.toLowerCase().includes(q) ||
      c.nano_banana_prompt_first.toLowerCase().includes(q) ||
      c.veo_prompt.toLowerCase().includes(q)
    );
  }, [allClips, search]);

  // Группировка по сценам
  const sceneGroups = useMemo(() => {
    const groups: Array<{ sceneId: string; clips: Clip[] }> = [];
    let current = '';
    for (const clip of filteredClips) {
      if (clip.scene_id !== current) {
        current = clip.scene_id;
        groups.push({ sceneId: current, clips: [] });
      }
      groups[groups.length - 1].clips.push(clip);
    }
    return groups;
  }, [filteredClips]);

  // Перевод промпта через Claude
  const handleTranslate = async (clipId: string) => {
    const clip = allClips.find((c) => c.clip_id === clipId);
    if (!clip) return;

    setTranslating(clipId);
    try {
      const result = await fetch('/api/clips/translate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          projectId,
          texts: {
            first: clip.nano_banana_prompt_first,
            veo: clip.veo_prompt,
          },
        }),
      });
      const data = await result.json();
      if (data.translations) {
        setTranslations((prev) => ({ ...prev, [clipId]: data.translations }));
      }
    } catch (err) {
      alert(String(err));
    } finally {
      setTranslating(null);
    }
  };

  // Исправление промпта по фидбеку
  const handleFix = async (clipId: string, component: string) => {
    const feedback = feedbacks[clipId]?.[component]?.trim();
    if (!feedback) return;

    setFixing(`${clipId}_${component}`);
    try {
      const result = await fetch('/api/clips/fix', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          projectId,
          clipId,
          component,
          feedback,
          model,
        }),
      });
      const data = await result.json();
      if (data.success) {
        // Очищаем фидбек и перевод
        setFeedbacks((prev) => {
          const copy = { ...prev };
          if (copy[clipId]) delete copy[clipId][component];
          return copy;
        });
        setTranslations((prev) => {
          const copy = { ...prev };
          delete copy[clipId];
          return copy;
        });
        // Обновляем список клипов
        queryClient.invalidateQueries({ queryKey: ['clips', projectId] });
      }
    } catch (err) {
      alert(String(err));
    } finally {
      setFixing(null);
    }
  };

  const setFeedback = (clipId: string, component: string, value: string) => {
    setFeedbacks((prev) => ({
      ...prev,
      [clipId]: { ...prev[clipId], [component]: value },
    }));
  };

  if (isLoading) return <div className="text-gray-400">Загрузка...</div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold">Промпты</h1>
          <p className="text-sm text-gray-500">{allClips.length} клипов</p>
        </div>
        {/* Выбор модели */}
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-500">Модель для исправлений:</span>
          <div className="flex items-center bg-surface-light rounded-lg border border-surface-lighter overflow-hidden text-xs">
            <button
              onClick={() => setModel('sonnet')}
              className={`px-3 py-1.5 transition-colors ${model === 'sonnet' ? 'bg-accent text-white' : 'text-gray-400 hover:text-white'}`}
            >
              Sonnet
            </button>
            <button
              onClick={() => setModel('opus')}
              className={`px-3 py-1.5 transition-colors ${model === 'opus' ? 'bg-accent text-white' : 'text-gray-400 hover:text-white'}`}
            >
              Opus
            </button>
          </div>
        </div>
      </div>

      {/* Поиск */}
      <div className="relative mb-4">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
        <input
          type="text"
          placeholder="Поиск по clip_id, сцене или тексту промпта..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-9 pr-3 py-2 bg-surface-light rounded-lg border border-surface-lighter focus:border-accent outline-none text-sm"
        />
      </div>

      {allClips.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <FileText size={48} className="mx-auto mb-4 opacity-50" />
          <p>Нет промптов. Сгенерируйте их на этапе настройки проекта.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {sceneGroups.map((group) => (
            <div key={group.sceneId}>
              {/* Заголовок сцены */}
              <h3 className="text-sm font-medium text-gray-400 mb-2 px-1">{group.sceneId}</h3>

              <div className="space-y-1">
                {group.clips.map((clip) => {
                  const isExpanded = expandedClip === clip.clip_id;
                  const trans = translations[clip.clip_id];
                  const isTranslating = translating === clip.clip_id;

                  return (
                    <div key={clip.clip_id} className="bg-surface-light rounded-lg border border-surface-lighter overflow-hidden">
                      {/* Строка клипа */}
                      <div
                        className="flex items-center gap-3 px-4 py-2.5 cursor-pointer hover:bg-surface-lighter/50 transition-colors"
                        onClick={() => setExpandedClip(isExpanded ? null : clip.clip_id)}
                      >
                        {isExpanded ? <ChevronDown size={14} className="text-gray-500" /> : <ChevronRight size={14} className="text-gray-500" />}
                        <span className="font-mono text-sm font-bold w-20">{clip.clip_id}</span>
                        <span className="text-sm text-gray-400 truncate flex-1">{clip.scene_description_ru}</span>
                        <span className="text-xs text-gray-600">{clip.nano_banana_ingredients.length} ингр.</span>
                      </div>

                      {/* Развёрнутый вид */}
                      {isExpanded && (
                        <div className="px-4 pb-4 border-t border-surface-lighter space-y-4">
                          {/* Кнопка перевода */}
                          <div className="flex justify-end pt-2">
                            <button
                              onClick={() => handleTranslate(clip.clip_id)}
                              disabled={isTranslating}
                              className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-accent transition-colors disabled:opacity-40"
                            >
                              {isTranslating ? <Loader2 size={12} className="animate-spin" /> : <FileText size={12} />}
                              {trans ? 'Обновить перевод' : 'Перевести на русский'}
                            </button>
                          </div>

                          {/* First */}
                          <PromptBlock
                            label="First"
                            prompt={clip.nano_banana_prompt_first}
                            translation={trans?.first}
                            feedback={feedbacks[clip.clip_id]?.nb_first || ''}
                            onFeedbackChange={(v) => setFeedback(clip.clip_id, 'nb_first', v)}
                            onFix={() => handleFix(clip.clip_id, 'nb_first')}
                            isFixing={fixing === `${clip.clip_id}_nb_first`}
                          />

                          {/* Ингредиенты — миниатюры */}
                          <IngredientThumbnails
                            ingredients={clip.nano_banana_ingredients}
                            projectId={projectId!}
                          />

                          {/* VEO */}
                          <PromptBlock
                            label="VEO"
                            prompt={clip.veo_prompt}
                            translation={trans?.veo}
                            feedback={feedbacks[clip.clip_id]?.veo || ''}
                            onFeedbackChange={(v) => setFeedback(clip.clip_id, 'veo', v)}
                            onFix={() => handleFix(clip.clip_id, 'veo')}
                            isFixing={fixing === `${clip.clip_id}_veo`}
                            charCount
                          />
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/** Блок одного промпта с переводом и фидбеком */
function PromptBlock({
  label,
  prompt,
  translation,
  feedback,
  onFeedbackChange,
  onFix,
  isFixing,
  charCount,
}: {
  label: string;
  prompt: string;
  translation?: string;
  feedback: string;
  onFeedbackChange: (v: string) => void;
  onFix: () => void;
  isFixing: boolean;
  charCount?: boolean;
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-[10px] text-amber-400 uppercase font-bold">{label}</span>
        {charCount && (
          <span className={`text-[10px] ${prompt.length > 300 ? 'text-red-400' : 'text-gray-500'}`}>
            {prompt.length} символов
          </span>
        )}
      </div>

      {/* Промпт на английском */}
      <div className="bg-surface rounded-lg border-l-2 border-amber-400/30 px-3 py-2 text-sm text-gray-300 whitespace-pre-wrap">
        {prompt || <span className="text-gray-600 italic">Пусто</span>}
      </div>

      {/* Перевод */}
      {translation && (
        <div className="mt-1 bg-surface rounded-lg border-l-2 border-blue-400/30 px-3 py-2 text-sm text-blue-300/70 whitespace-pre-wrap">
          {translation}
        </div>
      )}

      {/* Фидбек */}
      <div className="mt-1.5 flex gap-2">
        <input
          type="text"
          placeholder="Что исправить..."
          value={feedback}
          onChange={(e) => onFeedbackChange(e.target.value)}
          className="flex-1 px-3 py-1.5 bg-surface rounded border border-surface-lighter focus:border-accent outline-none text-xs"
        />
        <button
          onClick={onFix}
          disabled={!feedback.trim() || isFixing}
          className="flex items-center gap-1 px-3 py-1.5 bg-accent hover:bg-accent-hover rounded text-xs transition-colors disabled:opacity-40"
        >
          {isFixing ? <Loader2 size={12} className="animate-spin" /> : <Send size={12} />}
          Исправить
        </button>
      </div>
    </div>
  );
}


/** Миниатюры ингредиентов с лайтбоксом */
function IngredientThumbnails({ ingredients, projectId }: { ingredients: string[]; projectId: string }) {
  const [lightbox, setLightbox] = useState<string | null>(null);

  if (!ingredients.length) return null;

  return (
    <>
      <div className="flex flex-wrap gap-2 -mt-2">
        {ingredients.map((ing, i) => {
          const url = api.mediaUrl(projectId, ing);
          const filename = ing.split('/').pop() || '';
          return (
            <div
              key={i}
              className="group relative cursor-pointer"
              onClick={() => setLightbox(url)}
            >
              <img
                src={url}
                alt={filename}
                className="w-14 h-14 object-cover rounded border border-surface-lighter hover:border-accent transition-colors"
                loading="lazy"
                onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
              />
              <span className="absolute -top-1 -left-1 bg-surface-lighter text-[9px] text-gray-400 rounded px-1">
                {i + 1}
              </span>
            </div>
          );
        })}
      </div>

      {/* Лайтбокс */}
      {lightbox && (
        <div
          className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center cursor-pointer"
          onClick={() => setLightbox(null)}
        >
          <button
            className="absolute top-4 right-4 text-white/70 hover:text-white"
            onClick={() => setLightbox(null)}
          >
            <X size={24} />
          </button>
          <img
            src={lightbox}
            alt=""
            className="max-w-[90vw] max-h-[90vh] object-contain rounded-lg"
          />
        </div>
      )}
    </>
  );
}
