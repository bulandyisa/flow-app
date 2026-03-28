import { useState, useMemo, useCallback, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useReview, useSubmitReview } from '@/api/hooks';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';
import { Image, Video, CheckCircle, Clock, Filter, Send, Loader2, Search, AlertTriangle, Lock } from 'lucide-react';
import { SceneHeader } from '@/components/review/SceneHeader';
import { ClipCard } from '@/components/review/ClipCard';
import { useGenerationStore } from '@/store/generation';

type ViewMode = 'review_photos' | 'review_videos' | 'review_all' | 'all_photos' | 'all_videos' | 'all' | 'accepted' | 'blocked';

const VIEW_MODES: { id: ViewMode; label: string; icon: typeof Image }[] = [
  { id: 'review_photos', label: 'Ревью фото', icon: Image },
  { id: 'review_videos', label: 'Ревью видео', icon: Video },
  { id: 'review_all', label: 'Ожидает ревью', icon: Clock },
  { id: 'all_photos', label: 'Все фото', icon: Image },
  { id: 'all_videos', label: 'Все видео', icon: Video },
  { id: 'all', label: 'Все клипы', icon: Filter },
  { id: 'accepted', label: 'Принятые', icon: CheckCircle },
  { id: 'blocked', label: 'Заблокированные', icon: Lock },
];

const CLIPS_PER_PAGE = 40;
const LS_KEY_SELECTIONS = 'flow-review-selections';
const LS_KEY_FEEDBACKS = 'flow-review-feedbacks';

interface ReviewClip {
  clip_id: string;
  scene_id: string;
  scene_description_ru: string;
}

interface ReviewManifest {
  clip_id: string;
  components: Record<string, {
    status: string;
    attempts: Array<{
      attempt: number;
      variants: Array<{ file: string }>;
    }>;
  }>;
}

/** Проверяет, заблокирован ли клип по chain (VEO ждёт, а first не accepted) */
function isChainBlocked(manifest: ReviewManifest | undefined): boolean {
  if (!manifest) return true; // нет манифеста = нечего генерировать, chain-blocked
  const firstStatus = manifest.components?.nb_first?.status || 'pending';
  const veoStatus = manifest.components?.veo?.status || 'pending';
  // VEO заблокирован, если first не accepted
  return veoStatus === 'pending' && firstStatus !== 'accepted' && firstStatus !== 'generated';
}

export function Review() {
  const { id: projectId } = useParams<{ id: string }>();
  const { data, isLoading } = useReview(projectId!);
  const submitMutation = useSubmitReview(projectId!);
  const { data: botStatus } = useQuery({
    queryKey: ['bot-status'],
    queryFn: api.getBotStatus,
    refetchInterval: 10000,
  });
  const isGenerating = (botStatus?.bots || []).some((b: { isRunning: boolean }) => b.isRunning);
  const { isFixingPrompts } = useGenerationStore();
  const canSubmit = !submitMutation.isPending && !isGenerating && !isFixingPrompts;

  const [viewMode, setViewMode] = useState<ViewMode>('review_photos');
  const [page, setPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [bulkFeedback, setBulkFeedback] = useState('');

  // Состояние решений: { clipId: { component: variantIndex } }
  // Восстанавливаем из localStorage
  const [selections, setSelections] = useState<Record<string, Record<string, number | null>>>(() => {
    try {
      const saved = localStorage.getItem(LS_KEY_SELECTIONS);
      return saved ? JSON.parse(saved) : {};
    } catch {
      return {};
    }
  });
  const [feedbacks, setFeedbacks] = useState<Record<string, Record<string, string>>>(() => {
    try {
      const saved = localStorage.getItem(LS_KEY_FEEDBACKS);
      return saved ? JSON.parse(saved) : {};
    } catch {
      return {};
    }
  });
  const [submitResult, setSubmitResult] = useState<string | null>(null);
  const [model, setModel] = useState<'sonnet' | 'opus'>('sonnet');

  // Сохраняем в localStorage при изменениях
  useEffect(() => {
    try {
      localStorage.setItem(LS_KEY_SELECTIONS, JSON.stringify(selections));
    } catch { /* ignore */ }
  }, [selections]);

  useEffect(() => {
    try {
      localStorage.setItem(LS_KEY_FEEDBACKS, JSON.stringify(feedbacks));
    } catch { /* ignore */ }
  }, [feedbacks]);

  // beforeunload предупреждение если есть несохранённые решения
  const hasUnsavedDecisions = useMemo(() => {
    return Object.keys(selections).length > 0 || Object.keys(feedbacks).length > 0;
  }, [selections, feedbacks]);

  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (hasUnsavedDecisions) {
        e.preventDefault();
      }
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [hasUnsavedDecisions]);

  const reviewData = data as { clips: ReviewClip[]; manifests: Record<string, ReviewManifest> } | undefined;
  const clips = reviewData?.clips || [];
  const manifests = reviewData?.manifests || {};

  // Подсчёт chain-blocked клипов
  const chainBlockedCount = useMemo(() => {
    return clips.filter((clip) => isChainBlocked(manifests[clip.clip_id])).length;
  }, [clips, manifests]);

  // Поиск
  const searchedClips = useMemo(() => {
    if (!searchQuery.trim()) return clips;
    const q = searchQuery.toLowerCase().trim();
    return clips.filter((clip) =>
      clip.clip_id.toLowerCase().includes(q) ||
      clip.scene_id.toLowerCase().includes(q) ||
      clip.scene_description_ru.toLowerCase().includes(q)
    );
  }, [clips, searchQuery]);

  // Фильтрация клипов по view mode
  const filteredClips = useMemo(() => {
    return searchedClips.filter((clip) => {
      const manifest = manifests[clip.clip_id];

      switch (viewMode) {
        case 'review_photos': {
          if (!manifest) return false;
          const firstStatus = manifest.components?.nb_first?.status || 'pending';
          return firstStatus === 'generated';
        }
        case 'review_videos': {
          if (!manifest) return false;
          const veoStatus = manifest.components?.veo?.status || 'pending';
          return veoStatus === 'generated';
        }
        case 'review_all': {
          if (!manifest) return false;
          const firstStatus = manifest.components?.nb_first?.status || 'pending';
          const veoStatus = manifest.components?.veo?.status || 'pending';
          return firstStatus === 'generated' || veoStatus === 'generated';
        }
        case 'all_photos':
          return true; // покажем все, но только фото-компоненты
        case 'all_videos': {
          if (!manifest) return false;
          const veoStatus = manifest.components?.veo?.status || 'pending';
          return veoStatus !== 'pending'; // есть хотя бы попытка VEO
        }
        case 'accepted': {
          if (!manifest) return false;
          const firstStatus = manifest.components?.nb_first?.status || 'pending';
          return firstStatus === 'accepted';
        }
        case 'blocked':
          return isChainBlocked(manifest);
        case 'all':
        default:
          return true;
      }
    });
  }, [searchedClips, manifests, viewMode]);

  // Пагинация
  const totalPages = Math.max(1, Math.ceil(filteredClips.length / CLIPS_PER_PAGE));
  const pageClips = filteredClips.slice((page - 1) * CLIPS_PER_PAGE, page * CLIPS_PER_PAGE);

  // Группировка по сценам
  const sceneGroups = useMemo(() => {
    const groups: Array<{ sceneId: string; clips: typeof pageClips }> = [];
    let currentScene = '';
    for (const clip of pageClips) {
      if (clip.scene_id !== currentScene) {
        currentScene = clip.scene_id;
        groups.push({ sceneId: currentScene, clips: [] });
      }
      groups[groups.length - 1].clips.push(clip);
    }
    return groups;
  }, [pageClips]);

  // Статистика
  const stats = useMemo(() => {
    let firstAccepted = 0;
    let veoAccepted = 0;
    let needsReview = 0;
    let pendingPhotos = 0;
    let pendingVideos = 0;
    for (const clip of clips) {
      const m = manifests[clip.clip_id];
      if (!m) continue;
      const firstSt = m.components?.nb_first?.status || 'pending';
      const veoSt = m.components?.veo?.status || 'pending';
      if (firstSt === 'accepted') firstAccepted++;
      if (veoSt === 'accepted') veoAccepted++;
      if (firstSt === 'generated' || veoSt === 'generated') needsReview++;
      if (firstSt === 'pending') pendingPhotos++;
      if (veoSt === 'pending' && firstSt === 'accepted') pendingVideos++;
    }
    return { total: clips.length, firstAccepted, veoAccepted, needsReview, pendingPhotos, pendingVideos };
  }, [clips, manifests]);

  // Обновляем store для панели генерации в sidebar
  const setPending = useGenerationStore((s) => s.setPending);
  useEffect(() => {
    setPending(stats.pendingPhotos, stats.pendingVideos);
  }, [stats.pendingPhotos, stats.pendingVideos, setPending]);

  // Хелпер: получить компоненты клипа для отображения
  const getClipComponents = useCallback((clip: ReviewClip) => {
    const manifest = manifests[clip.clip_id];
    if (!manifest) return [];

    const componentNames = ['nb_first', 'veo'];
    return componentNames.map((name) => {
      const comp = manifest.components?.[name];
      const latestAttempt = comp?.attempts?.[comp.attempts.length - 1];
      const variants = (latestAttempt?.variants || []).map((v, i) => ({
        index: i,
        src: api.mediaUrl(projectId!, `review/${clip.clip_id}/${name}/attempt_${latestAttempt?.attempt || 1}/${v.file}`),
        isVideo: name === 'veo',
      }));

      return {
        name,
        status: comp?.status || 'pending',
        attemptNum: latestAttempt?.attempt || 0,
        variants,
      };
    });
  }, [manifests, projectId]);

  // Хелпер: принятые кадры
  const getAcceptedFrames = useCallback((clip: ReviewClip) => {
    const frames: Array<{ src: string; label: string; component: string }> = [];
    const manifest = manifests[clip.clip_id];
    if (!manifest) return frames;

    if (manifest.components?.nb_first?.status === 'accepted') {
      frames.push({
        src: api.mediaUrl(projectId!, `frames/${clip.clip_id}_first.png`),
        label: 'First (принято)',
        component: 'nb_first',
      });
    }
    return frames;
  }, [manifests, projectId]);

  // Обработчики
  const handleSelect = (clipId: string, component: string, variantIndex: number) => {
    setSelections((prev) => ({
      ...prev,
      [clipId]: {
        ...prev[clipId],
        [component]: prev[clipId]?.[component] === variantIndex ? null : variantIndex,
      },
    }));
  };

  const handleFeedback = (clipId: string, component: string, value: string) => {
    setFeedbacks((prev) => ({
      ...prev,
      [clipId]: { ...prev[clipId], [component]: value },
    }));
  };

  // Отправка решений
  const handleSubmit = async () => {
    const decisions: Array<{
      clipId: string;
      component: string;
      action: 'accept' | 'reject';
      attempt?: number;
      variant?: number;
      feedback?: string;
    }> = [];

    for (const [clipId, compSelections] of Object.entries(selections)) {
      for (const [comp, variantIdx] of Object.entries(compSelections)) {
        // Индивидуальный фидбек приоритетнее
        const individualFeedback = feedbacks[clipId]?.[comp]?.trim();
        // Bulk feedback как fallback для клипов без индивидуального фидбека
        const effectiveFeedback = individualFeedback || (bulkFeedback.trim() && variantIdx == null ? bulkFeedback.trim() : '');

        if (individualFeedback) {
          decisions.push({ clipId, component: comp, action: 'reject', feedback: individualFeedback });
        } else if (variantIdx != null) {
          const manifest = manifests[clipId];
          const compData = manifest?.components?.[comp];
          const latestAttempt = compData?.attempts?.[compData.attempts.length - 1];
          decisions.push({
            clipId,
            component: comp,
            action: 'accept',
            attempt: latestAttempt?.attempt || 1,
            variant: variantIdx,
          });
        } else if (effectiveFeedback) {
          decisions.push({ clipId, component: comp, action: 'reject', feedback: effectiveFeedback });
        }
      }
    }

    // Применяем bulk feedback к клипам с выбранными вариантами но без индивидуального фидбека
    // (для случая когда пользователь хочет отклонить все с одним фидбеком)
    if (bulkFeedback.trim()) {
      for (const [clipId, compFeedbacks] of Object.entries(feedbacks)) {
        for (const [comp, fb] of Object.entries(compFeedbacks)) {
          if (!fb.trim() && !selections[clipId]?.[comp]) {
            // Нет ни выбора, ни фидбека — пропускаем
          }
        }
      }
    }

    if (decisions.length === 0) {
      setSubmitResult('Нет решений для отправки');
      setTimeout(() => setSubmitResult(null), 3000);
      return;
    }

    try {
      await submitMutation.mutateAsync({ decisions, model });
      const accepted = decisions.filter((d) => d.action === 'accept').length;
      const rejected = decisions.filter((d) => d.action === 'reject').length;
      setSubmitResult(`Принято: ${accepted} | Отклонено: ${rejected}`);
      setSelections({});
      setFeedbacks({});
      setBulkFeedback('');
      // Очищаем localStorage
      try {
        localStorage.removeItem(LS_KEY_SELECTIONS);
        localStorage.removeItem(LS_KEY_FEEDBACKS);
      } catch { /* ignore */ }
      setTimeout(() => setSubmitResult(null), 5000);
    } catch (err) {
      setSubmitResult(`Ошибка: ${err}`);
    }
  };

  // Обработчик revoke из ClipCard
  const handleRevoke = useCallback(async (clipId: string, component: string, feedback?: string) => {
    if (!projectId) return;
    try {
      await api.revokeAccepted(projectId, clipId, component, feedback);
      // Перезапросить данные ревью
      submitMutation.reset();
    } catch (err) {
      alert(`Ошибка: ${err instanceof Error ? err.message : String(err)}`);
    }
  }, [projectId, submitMutation]);

  if (isLoading) return <div className="text-gray-400">Загрузка...</div>;

  return (
    <div>
      {/* Шапка */}
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">Ревью</h1>
        <div className="flex items-center gap-3">
          {isGenerating && (
            <span className="flex items-center gap-1.5 text-xs text-amber-400">
              <Loader2 size={12} className="animate-spin" />
              Идёт генерация
            </span>
          )}
          {isFixingPrompts && (
            <span className="flex items-center gap-1.5 text-xs text-amber-400">
              <Loader2 size={12} className="animate-spin" />
              Исправление промптов
            </span>
          )}
          {/* Выбор модели */}
          <div className="flex items-center bg-surface rounded-lg border border-surface-lighter overflow-hidden text-xs">
            <button
              onClick={() => setModel('sonnet')}
              className={`px-3 py-2 transition-colors ${
                model === 'sonnet' ? 'bg-accent text-white' : 'text-gray-400 hover:text-white'
              }`}
            >
              Sonnet
            </button>
            <button
              onClick={() => setModel('opus')}
              className={`px-3 py-2 transition-colors ${
                model === 'opus' ? 'bg-accent text-white' : 'text-gray-400 hover:text-white'
              }`}
            >
              Opus
            </button>
          </div>
          <button
            onClick={handleSubmit}
            disabled={!canSubmit}
            className="flex items-center gap-2 px-5 py-2.5 bg-accent hover:bg-accent-hover rounded-lg transition-colors disabled:opacity-40"
          >
            <Send size={16} />
            <span>{submitMutation.isPending ? 'Отправка...' : 'Отправить решения'}</span>
          </button>
        </div>
      </div>

      {/* Уведомление */}
      {submitResult && (
        <div className="mb-4 px-4 py-2 bg-surface-light border border-surface-lighter rounded-lg text-sm">
          {submitResult}
        </div>
      )}

      {/* Chain-blocking баннер */}
      {chainBlockedCount > 0 && (
        <div className="mb-4 px-4 py-3 bg-amber-900/10 border border-amber-900/30 rounded-lg flex items-start gap-3">
          <AlertTriangle size={18} className="text-amber-400 mt-0.5 shrink-0" />
          <div>
            <p className="text-sm text-amber-300 font-medium">
              {chainBlockedCount} клипов заблокированы по chain
            </p>
            <p className="text-xs text-gray-400 mt-1">
              VEO-видео не может быть сгенерировано, пока не принят first-кадр.
              Примите first-кадры, чтобы разблокировать генерацию видео.
            </p>
          </div>
        </div>
      )}

      {/* Статистика */}
      <div className="grid grid-cols-5 gap-3 mb-4">
        {[
          { label: 'Всего клипов', value: stats.total },
          { label: 'First принято', value: stats.firstAccepted },
          { label: 'VEO принято', value: stats.veoAccepted },
          { label: 'На ревью', value: stats.needsReview },
          { label: 'На странице', value: pageClips.length },
        ].map((stat) => (
          <div key={stat.label} className="px-3 py-2 bg-surface-light rounded-lg text-center">
            <div className="text-lg font-bold text-white">{stat.value}</div>
            <div className="text-xs text-gray-500">{stat.label}</div>
          </div>
        ))}
      </div>

      {/* Прогресс */}
      {stats.total > 0 && (
        <div className="mb-4">
          <div className="h-2 bg-surface-lighter rounded-full overflow-hidden">
            <div
              className="h-full bg-green-500 rounded-full transition-all"
              style={{ width: `${(stats.firstAccepted / stats.total) * 100}%` }}
            />
          </div>
          <div className="text-xs text-gray-500 mt-1">
            {stats.firstAccepted} / {stats.total} first кадров принято
          </div>
        </div>
      )}

      {/* Поиск */}
      <div className="relative mb-4">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => { setSearchQuery(e.target.value); setPage(1); }}
          placeholder="Поиск по clip_id, scene_id, описанию..."
          className="w-full pl-10 pr-4 py-2 bg-surface-light border border-surface-lighter rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-accent"
        />
      </div>

      {/* Фильтры */}
      <div className="flex flex-wrap gap-2 mb-4">
        {VIEW_MODES.map((mode) => {
          const Icon = mode.icon;
          const isActive = viewMode === mode.id;
          return (
            <button
              key={mode.id}
              onClick={() => { setViewMode(mode.id); setPage(1); }}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors ${
                isActive
                  ? 'bg-accent text-white'
                  : 'bg-surface-light border border-surface-lighter text-gray-400 hover:border-gray-500'
              }`}
            >
              <Icon size={14} />
              {mode.label}
            </button>
          );
        })}
      </div>

      {/* Bulk feedback */}
      <div className="mb-4">
        <label className="text-xs text-gray-500 block mb-1">
          Фидбек для всех отклонённых:
        </label>
        <input
          type="text"
          value={bulkFeedback}
          onChange={(e) => setBulkFeedback(e.target.value)}
          placeholder="Общий фидбек, который применится к клипам без индивидуального фидбека"
          className="w-full px-3 py-2 bg-surface-light border border-surface-lighter rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-accent"
        />
      </div>

      {/* Пагинация */}
      {totalPages > 1 && (
        <div className="flex items-center gap-3 mb-4">
          <button
            onClick={() => setPage(Math.max(1, page - 1))}
            disabled={page === 1}
            className="px-3 py-1 bg-surface-light rounded text-sm disabled:opacity-30"
          >
            ←
          </button>
          <span className="text-sm text-gray-400">
            Страница {page} из {totalPages} ({filteredClips.length} клипов)
          </span>
          <button
            onClick={() => setPage(Math.min(totalPages, page + 1))}
            disabled={page === totalPages}
            className="px-3 py-1 bg-surface-light rounded text-sm disabled:opacity-30"
          >
            →
          </button>
        </div>
      )}

      {/* Клипы */}
      {pageClips.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <Image size={48} className="mx-auto mb-4 opacity-50" />
          <p>Нет клипов для отображения.</p>
        </div>
      ) : (
        sceneGroups.map((group) => (
          <div key={group.sceneId}>
            <SceneHeader
              sceneId={group.sceneId}
              clipCount={group.clips.length}
            />
            {group.clips.map((clip) => {
              const manifest = manifests[clip.clip_id];
              const blocked = isChainBlocked(manifest);
              return (
                <ClipCard
                  key={clip.clip_id}
                  clipId={clip.clip_id}
                  sceneId={clip.scene_id}
                  description={clip.scene_description_ru}
                  components={getClipComponents(clip)}
                  acceptedFrames={getAcceptedFrames(clip)}
                  selections={selections[clip.clip_id] || {}}
                  feedbacks={feedbacks[clip.clip_id] || {}}
                  onSelect={(comp, vi) => handleSelect(clip.clip_id, comp, vi)}
                  onFeedbackChange={(comp, val) => handleFeedback(clip.clip_id, comp, val)}
                  chainBlocked={blocked}
                  onRevoke={(component, feedback) => handleRevoke(clip.clip_id, component, feedback)}
                />
              );
            })}
          </div>
        ))
      )}
    </div>
  );
}
