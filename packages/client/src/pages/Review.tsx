import { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { useSubmitReview } from '@/api/hooks';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';
import { Image, Video, CheckCircle, Clock, Filter, Send, Loader2, Search, AlertTriangle, Lock, Terminal, ChevronDown } from 'lucide-react';
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
  const [viewMode, setViewMode] = useState<ViewMode>('review_photos');
  const [page, setPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');

  // Fetch with server-side filter/search/pagination
  const { data, isLoading } = useQuery({
    queryKey: ['review', projectId, viewMode, page, searchQuery],
    queryFn: () => api.getReview(projectId!, page, 40, viewMode, searchQuery),
    refetchInterval: 30_000,
  });
  const submitMutation = useSubmitReview(projectId!);
  const { data: botStatus } = useQuery({
    queryKey: ['bot-status'],
    queryFn: api.getBotStatus,
    refetchInterval: 10000,
  });
  const isGenerating = (botStatus?.bots || []).some((b: { isRunning: boolean }) => b.isRunning);
  const { isFixingPrompts } = useGenerationStore();
  const canSubmit = !submitMutation.isPending && !isGenerating && !isFixingPrompts;

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
  const [model, setModel] = useState<'sonnet' | 'opus'>('opus');

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

  const reviewData = data as {
    clips: ReviewClip[];
    manifests: Record<string, ReviewManifest>;
    total: number;
    totalAll: number;
    page: number;
    limit: number;
    stats: { total: number; firstAccepted: number; veoAccepted: number; needsReview: number; pendingPhotos: number; pendingVideos: number; chainBlocked: number };
  } | undefined;
  const pageClips = reviewData?.clips || [];
  const manifests = reviewData?.manifests || {};
  const totalFiltered = reviewData?.total || 0;
  const totalPages = Math.max(1, Math.ceil(totalFiltered / CLIPS_PER_PAGE));
  const chainBlockedCount = reviewData?.stats?.chainBlocked || 0;

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

  const stats = reviewData?.stats || { total: 0, firstAccepted: 0, veoAccepted: 0, needsReview: 0, pendingPhotos: 0, pendingVideos: 0, chainBlocked: 0 };

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

    const added = new Set<string>();

    // 1. Selections: принятые варианты
    for (const [clipId, compSelections] of Object.entries(selections)) {
      for (const [comp, variantIdx] of Object.entries(compSelections)) {
        if (variantIdx != null) {
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
          added.add(`${clipId}:${comp}`);
        }
      }
    }

    // 2. Feedbacks: отклонения (с индивидуальным фидбеком или bulk)
    for (const [clipId, compFeedbacks] of Object.entries(feedbacks)) {
      for (const [comp, fb] of Object.entries(compFeedbacks)) {
        const key = `${clipId}:${comp}`;
        if (added.has(key)) continue; // уже принят — не отклоняем
        const text = fb?.trim() || '';
        if (text) {
          decisions.push({ clipId, component: comp, action: 'reject', feedback: text });
          added.add(key);
        }
      }
    }

    // 3. Bulk feedback для клипов без индивидуального решения
    if (bulkFeedback.trim()) {
      for (const clip of pageClips) {
        const cid = clip.clip_id;
        for (const comp of ['nb_first', 'veo'] as const) {
          const key = `${cid}:${comp}`;
          if (added.has(key)) continue;
          const manifest = manifests[cid];
          const compData = manifest?.components?.[comp];
          if (compData?.status === 'generated') {
            decisions.push({ clipId: cid, component: comp, action: 'reject', feedback: bulkFeedback.trim() });
            added.add(key);
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
      const message = err instanceof TypeError && err.message === 'Failed to fetch'
        ? 'Сервер недоступен. Проверьте что приложение запущено и попробуйте снова.'
        : err instanceof Error ? err.message : String(err);
      setSubmitResult(`Ошибка: ${message}`);
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

  // Ручная загрузка first-кадра
  const handleUploadFirst = useCallback(async (clipId: string, file: File) => {
    if (!projectId) return;
    try {
      await api.uploadFirstFrame(projectId, clipId, file);
      submitMutation.reset();
    } catch (err) {
      alert(`Ошибка загрузки: ${err instanceof Error ? err.message : String(err)}`);
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
          {/* Сброс */}
          <button
            onClick={async () => {
              if (!projectId) return;
              if (!confirm('Сбросить ВСЕ nb_first с фидбеками на pending?\nБоты перегенерируют их заново.')) return;
              try {
                const result = await api.resetFirst(projectId);
                setFeedbacks({});
                setSelections({});
                try { localStorage.removeItem(LS_KEY_FEEDBACKS); localStorage.removeItem(LS_KEY_SELECTIONS); } catch {}
                setSubmitResult(result.message);
                setTimeout(() => { setSubmitResult(null); window.location.reload(); }, 2000);
              } catch (err) {
                setSubmitResult(`Ошибка: ${err instanceof Error ? err.message : String(err)}`);
              }
            }}
            className="px-3 py-2 text-xs bg-surface rounded-lg border border-surface-lighter text-yellow-400 hover:text-yellow-300 hover:border-yellow-400/30 transition-colors"
            title="Сбросить все nb_first с фидбеками (→ pending) для перегенерации"
          >
            Сбросить фото
          </button>
          <button
            onClick={async () => {
              if (!projectId) return;
              if (!confirm('Сбросить ВСЕ VEO со статусом "generated" на pending?\nБоты перегенерируют их заново.')) return;
              try {
                const result = await api.resetVeo(projectId);
                setSubmitResult(result.message);
                setTimeout(() => { setSubmitResult(null); window.location.reload(); }, 2000);
              } catch (err) {
                setSubmitResult(`Ошибка: ${err instanceof Error ? err.message : String(err)}`);
              }
            }}
            className="px-3 py-2 text-xs bg-surface rounded-lg border border-surface-lighter text-yellow-400 hover:text-yellow-300 hover:border-yellow-400/30 transition-colors"
            title="Сбросить все VEO (generated → pending) для перегенерации"
          >
            Сбросить видео
          </button>
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

      {/* Логи ботов */}
      <BotLogPanel />

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
            Страница {page} из {totalPages} ({totalFiltered} клипов)
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
                  onUploadFirst={(file) => handleUploadFirst(clip.clip_id, file)}
                />
              );
            })}
          </div>
        ))
      )}
    </div>
  );
}


function BotLogPanel() {
  const [open, setOpen] = useState(false);
  const [selectedBot, setSelectedBot] = useState(1);
  const logRef = useRef<HTMLPreElement>(null);

  const { data: status } = useQuery({
    queryKey: ['bot-status'],
    queryFn: api.getBotStatus,
    refetchInterval: 5000,
  });

  const bots = status?.bots || [];
  // Default bot tabs 1-6 even when status is empty
  const botTabs = bots.length > 0 ? bots : [1, 2, 3, 4, 5, 6].map((id) => ({ id, isRunning: false, exitCode: null as number | null }));
  const hasError = bots.some((b) => b.exitCode != null && b.exitCode !== 0);

  const { data: logData } = useQuery({
    queryKey: ['bot-log', selectedBot],
    queryFn: () => api.getBotLog(selectedBot, 500),
    refetchInterval: open ? 3000 : false,
    enabled: open,
  });

  const lines = logData?.log || [];

  useEffect(() => {
    if (open && logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [lines, open]);

  return (
    <div className="mb-4">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 text-xs text-gray-400 hover:text-gray-200 transition-colors"
      >
        <Terminal size={14} />
        <span>Логи ботов</span>
        <ChevronDown size={12} className={`transition-transform ${open ? 'rotate-180' : ''}`} />
        {hasError && (
          <span className="px-1.5 py-0.5 bg-red-900/30 text-red-400 rounded text-[10px]">ошибка</span>
        )}
      </button>

      {open && (
        <div className="mt-2">
          <div className="flex gap-1 mb-2">
            {botTabs.map((bot) => (
              <button
                key={bot.id}
                onClick={() => setSelectedBot(bot.id)}
                className={`px-2 py-1 text-xs rounded transition-colors flex items-center gap-1.5 ${
                  selectedBot === bot.id
                    ? 'bg-accent text-white'
                    : 'bg-surface-light text-gray-400 hover:text-gray-200'
                }`}
              >
                {bot.isRunning && <div className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse" />}
                {!bot.isRunning && bot.exitCode != null && bot.exitCode !== 0 && (
                  <div className="w-1.5 h-1.5 bg-red-400 rounded-full" />
                )}
                Bot {bot.id}
              </button>
            ))}
          </div>
          <pre
            ref={logRef}
            className="bg-black/70 border border-surface-lighter rounded-lg p-3 text-[11px] font-mono leading-relaxed overflow-auto max-h-64"
          >
            {lines.length === 0 ? (
              <span className="text-gray-600">Нет логов. Запустите генерацию.</span>
            ) : (
              lines.map((line: { timestamp: string; stream: string; text: string }, i: number) => (
                <div key={i} className={line.stream === 'stderr' ? 'text-red-400' : 'text-gray-300'}>
                  <span className="text-gray-600 select-none">
                    {new Date(line.timestamp).toLocaleTimeString()}{' '}
                  </span>
                  {line.text}
                </div>
              ))
            )}
          </pre>
        </div>
      )}
    </div>
  );
}
