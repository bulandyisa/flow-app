import { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import { FileText, ChevronDown, ChevronRight, Send, Loader2, Search, X, Image as ImageIcon, Replace } from 'lucide-react';

interface Clip {
  clip_id: string;
  scene_id: string;
  scene_description_ru: string;
  nano_banana_ingredients: string[];
  nano_banana_prompt_first: string;
  veo_prompt: string;
}

interface Angle {
  id: string;
  file: string;
  description: string;
  status: string;
}

interface Character {
  id: string;
  name: string;
  nameRu: string;
  baseImage: string | null;
  angles: Angle[];
}

interface Location {
  id: string;
  name: string;
  nameRu: string;
  baseImage: string | null;
  angles: Angle[];
}

interface ProjectData {
  id: string;
  characters: Character[];
  locations: Location[];
}

/** Один элемент библиотеки референсов проекта */
interface RefOption {
  path: string;
  label: string;
  group: string;
}

export function Clips() {
  const { id: projectId } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const { data: clips, isLoading } = useQuery({
    queryKey: ['clips', projectId],
    queryFn: () => api.getClips(projectId!),
    enabled: !!projectId,
  });

  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => api.getProject(projectId!) as Promise<ProjectData>,
    enabled: !!projectId,
  });

  const [expandedClip, setExpandedClip] = useState<string | null>(null);
  const [showRefs, setShowRefs] = useState<Record<string, boolean>>({});
  const [feedbacks, setFeedbacks] = useState<Record<string, Record<string, string>>>({});
  const [fixing, setFixing] = useState<string | null>(null); // clip_id currently fixing
  const [model, setModel] = useState<'sonnet' | 'opus'>('sonnet');
  const [search, setSearch] = useState('');
  const [translations, setTranslations] = useState<Record<string, Record<string, string>>>({});
  const [translating, setTranslating] = useState<string | null>(null);

  // Полный список доступных референсов проекта (персонажи + локации с ракурсами)
  const refLibrary = useMemo<RefOption[]>(() => {
    if (!project) return [];
    const opts: RefOption[] = [];
    for (const c of project.characters) {
      const who = c.nameRu || c.name;
      if (c.baseImage) opts.push({ path: c.baseImage, label: `${who} — базовый образ`, group: `Персонаж: ${who}` });
      for (const a of c.angles) {
        if (a.status === 'accepted' && a.file) {
          opts.push({ path: a.file, label: `${who} — ${a.description || a.id}`, group: `Персонаж: ${who}` });
        }
      }
    }
    for (const l of project.locations) {
      const where = l.nameRu || l.name;
      if (l.baseImage) opts.push({ path: l.baseImage, label: `${where} — базовый образ`, group: `Локация: ${where}` });
      for (const a of l.angles) {
        if (a.status === 'accepted' && a.file) {
          opts.push({ path: a.file, label: `${where} — ${a.description || a.id}`, group: `Локация: ${where}` });
        }
      }
    }
    return opts;
  }, [project]);

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

                          {/* Референсы (свёрнуты по умолчанию) */}
                          <div>
                            <button
                              onClick={() =>
                                setShowRefs((prev) => ({ ...prev, [clip.clip_id]: !prev[clip.clip_id] }))
                              }
                              className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-accent transition-colors mb-1.5"
                            >
                              {showRefs[clip.clip_id] ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                              <ImageIcon size={12} />
                              {showRefs[clip.clip_id] ? 'Скрыть референсы' : 'Показать референсы'}
                              <span className="text-gray-600">({clip.nano_banana_ingredients.length})</span>
                            </button>
                            {showRefs[clip.clip_id] && (
                              <IngredientThumbnails
                                clipId={clip.clip_id}
                                ingredients={clip.nano_banana_ingredients}
                                projectId={projectId!}
                                library={refLibrary}
                                onReplaced={() =>
                                  queryClient.invalidateQueries({ queryKey: ['clips', projectId] })
                                }
                              />
                            )}
                          </div>

                          {/* First */}
                          <PromptBlock
                            label="First"
                            prompt={clip.nano_banana_prompt_first}
                            translation={trans?.first}
                            feedback={feedbacks[clip.clip_id]?.nb_first || ''}
                            onFeedbackChange={(v) => setFeedback(clip.clip_id, 'nb_first', v)}
                            onFix={() => handleFix(clip.clip_id, 'nb_first')}
                            onSave={async (p) => {
                              await api.updateClipPrompt(projectId!, clip.clip_id, 'nb_first', p);
                              queryClient.invalidateQueries({ queryKey: ['clips', projectId] });
                            }}
                            isFixing={fixing === `${clip.clip_id}_nb_first`}
                          />

                          {/* VEO */}
                          <PromptBlock
                            label="VEO"
                            prompt={clip.veo_prompt}
                            translation={trans?.veo}
                            feedback={feedbacks[clip.clip_id]?.veo || ''}
                            onFeedbackChange={(v) => setFeedback(clip.clip_id, 'veo', v)}
                            onFix={() => handleFix(clip.clip_id, 'veo')}
                            onSave={async (p) => {
                              await api.updateClipPrompt(projectId!, clip.clip_id, 'veo', p);
                              queryClient.invalidateQueries({ queryKey: ['clips', projectId] });
                            }}
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

/** Блок одного промпта с переводом, фидбеком и прямым редактированием */
function PromptBlock({
  label,
  prompt,
  translation,
  feedback,
  onFeedbackChange,
  onFix,
  onSave,
  isFixing,
  charCount,
}: {
  label: string;
  prompt: string;
  translation?: string;
  feedback: string;
  onFeedbackChange: (v: string) => void;
  onFix: () => void;
  onSave: (newPrompt: string) => void;
  isFixing: boolean;
  charCount?: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState('');
  const [saving, setSaving] = useState(false);

  const startEdit = () => {
    setEditText(prompt);
    setEditing(true);
  };

  const handleSave = async () => {
    if (editText.trim() === prompt) {
      setEditing(false);
      return;
    }
    setSaving(true);
    try {
      await onSave(editText.trim());
      setEditing(false);
    } finally {
      setSaving(false);
    }
  };

  const displayText = editing ? editText : prompt;

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-[10px] text-amber-400 uppercase font-bold">{label}</span>
        <div className="flex items-center gap-2">
          {charCount && (
            <span className={`text-[10px] ${displayText.length > 300 ? 'text-red-400' : 'text-gray-500'}`}>
              {displayText.length} символов
            </span>
          )}
        </div>
      </div>

      {/* Промпт — редактируемый или обычный */}
      {editing ? (
        <div>
          <textarea
            value={editText}
            onChange={(e) => setEditText(e.target.value)}
            rows={5}
            autoFocus
            className="w-full bg-surface rounded-lg border-l-2 border-green-400/50 px-3 py-2 text-sm text-gray-200 whitespace-pre-wrap outline-none resize-y focus:border-green-400"
          />
          <div className="flex justify-end gap-2 mt-1">
            <button
              onClick={() => setEditing(false)}
              className="px-3 py-1 text-xs text-gray-400 hover:text-white transition-colors"
            >
              Отмена
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-1 px-3 py-1 bg-green-600 hover:bg-green-500 rounded text-xs transition-colors disabled:opacity-40"
            >
              {saving ? <Loader2 size={10} className="animate-spin" /> : null}
              Сохранить
            </button>
          </div>
        </div>
      ) : (
        <div
          onClick={startEdit}
          className="bg-surface rounded-lg border-l-2 border-amber-400/30 px-3 py-2 text-sm text-gray-300 whitespace-pre-wrap cursor-pointer hover:border-amber-400/60 transition-colors group"
          title="Нажмите чтобы редактировать"
        >
          {prompt || <span className="text-gray-600 italic">Пусто</span>}
          <span className="invisible group-hover:visible text-[10px] text-gray-600 ml-2">✎</span>
        </div>
      )}

      {/* Перевод */}
      {translation && !editing && (
        <div className="mt-1 bg-surface rounded-lg border-l-2 border-blue-400/30 px-3 py-2 text-sm text-blue-300/70 whitespace-pre-wrap">
          {translation}
        </div>
      )}

      {/* Фидбек */}
      {!editing && (
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
      )}
    </div>
  );
}


/** Миниатюры ингредиентов с лайтбоксом и возможностью смены референса */
function IngredientThumbnails({
  clipId,
  ingredients,
  projectId,
  library,
  onReplaced,
}: {
  clipId: string;
  ingredients: string[];
  projectId: string;
  library: RefOption[];
  onReplaced: () => void;
}) {
  const [lightbox, setLightbox] = useState<string | null>(null);
  const [pickerFor, setPickerFor] = useState<number | null>(null);
  const [replacing, setReplacing] = useState<number | null>(null);

  if (!ingredients.length) return null;

  const handleReplace = async (index: number, newPath: string) => {
    setReplacing(index);
    setPickerFor(null);
    try {
      await api.updateClipIngredient(projectId, clipId, index, newPath);
      onReplaced();
    } catch (err) {
      alert(`Ошибка смены референса: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setReplacing(null);
    }
  };

  return (
    <>
      <div className="flex flex-wrap gap-3">
        {ingredients.map((ing, i) => {
          const url = api.mediaUrl(projectId, ing);
          const filename = ing.split('/').pop() || '';
          return (
            <div key={i} className="flex flex-col items-center gap-1 w-20">
              <div
                className="group relative cursor-pointer"
                onClick={() => setLightbox(url)}
              >
                <img
                  src={url}
                  alt={filename}
                  className="w-20 h-20 object-cover rounded border border-surface-lighter hover:border-accent transition-colors"
                  loading="lazy"
                  onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                />
                <span className="absolute -top-1 -left-1 bg-surface-lighter text-[9px] text-gray-400 rounded px-1">
                  {i + 1}
                </span>
                {replacing === i && (
                  <div className="absolute inset-0 bg-black/60 flex items-center justify-center rounded">
                    <Loader2 size={16} className="animate-spin text-white" />
                  </div>
                )}
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setPickerFor(pickerFor === i ? null : i);
                }}
                disabled={replacing != null}
                className="flex items-center gap-1 text-[10px] text-gray-500 hover:text-accent transition-colors disabled:opacity-40"
              >
                <Replace size={10} />
                Сменить
              </button>
            </div>
          );
        })}
      </div>

      {/* Модалка выбора референса */}
      {pickerFor != null && (
        <ReferencePicker
          currentPath={ingredients[pickerFor]}
          library={library}
          projectId={projectId}
          onPick={(path) => handleReplace(pickerFor, path)}
          onClose={() => setPickerFor(null)}
        />
      )}

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

/** Выпадающий список всех референсов проекта для смены ингредиента */
function ReferencePicker({
  currentPath,
  library,
  projectId,
  onPick,
  onClose,
}: {
  currentPath: string;
  library: RefOption[];
  projectId: string;
  onPick: (path: string) => void;
  onClose: () => void;
}) {
  const [query, setQuery] = useState('');
  const ref = useRef<HTMLDivElement>(null);

  // Закрытие по Escape и клику вне
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const filtered = useMemo(() => {
    if (!query.trim()) return library;
    const q = query.toLowerCase();
    return library.filter((o) => o.label.toLowerCase().includes(q) || o.group.toLowerCase().includes(q));
  }, [library, query]);

  const groups = useMemo(() => {
    const map = new Map<string, RefOption[]>();
    for (const o of filtered) {
      if (!map.has(o.group)) map.set(o.group, []);
      map.get(o.group)!.push(o);
    }
    return Array.from(map.entries());
  }, [filtered]);

  return (
    <div
      className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        ref={ref}
        className="bg-surface rounded-lg border border-surface-lighter w-full max-w-2xl max-h-[80vh] flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-surface-lighter">
          <h3 className="text-sm font-medium">Сменить референс</h3>
          <button onClick={onClose} className="text-gray-500 hover:text-white">
            <X size={16} />
          </button>
        </div>
        <div className="px-4 py-2 border-b border-surface-lighter">
          <div className="relative">
            <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-500" />
            <input
              type="text"
              autoFocus
              placeholder="Поиск по имени или ракурсу..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full pl-7 pr-3 py-1.5 bg-surface-light rounded border border-surface-lighter focus:border-accent outline-none text-xs"
            />
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-3 space-y-4">
          {groups.length === 0 ? (
            <p className="text-center text-gray-500 text-sm py-8">
              {library.length === 0 ? 'В проекте пока нет принятых референсов.' : 'Ничего не найдено.'}
            </p>
          ) : (
            groups.map(([groupName, items]) => (
              <div key={groupName}>
                <h4 className="text-[11px] uppercase text-gray-500 mb-1.5 font-medium">{groupName}</h4>
                <div className="grid grid-cols-4 gap-2">
                  {items.map((o) => {
                    const isCurrent = o.path === currentPath;
                    return (
                      <button
                        key={o.path}
                        onClick={() => onPick(o.path)}
                        className={`flex flex-col items-start gap-1 p-1.5 rounded border transition-colors text-left ${
                          isCurrent
                            ? 'border-accent bg-accent/10'
                            : 'border-surface-lighter hover:border-accent'
                        }`}
                      >
                        <img
                          src={api.mediaUrl(projectId, o.path)}
                          alt={o.label}
                          className="w-full h-20 object-cover rounded"
                          loading="lazy"
                          onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                        />
                        <span className="text-[10px] text-gray-300 line-clamp-2 leading-tight">
                          {o.label}
                        </span>
                        {isCurrent && (
                          <span className="text-[9px] text-accent">текущий</span>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
