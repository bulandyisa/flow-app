import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';
import { Play, Square, Minus, Plus, AlertTriangle, Image, Video, Loader2 } from 'lucide-react';

interface BotStatus {
  id: number;
  isRunning: boolean;
  currentClip: string | null;
  currentAction: string | null;
  completedCount: number;
  errorCount: number;
}

interface Props {
  projectId: string;
  pendingPhotos: number;
  pendingVideos: number;
  isFixingPrompts: boolean;
  fixProgress: [number, number];
}

export function GenerationPanel({ projectId, pendingPhotos, pendingVideos, isFixingPrompts, fixProgress }: Props) {
  const [botCount, setBotCount] = useState(6);

  const { data: status, refetch } = useQuery({
    queryKey: ['bot-status'],
    queryFn: api.getBotStatus,
    refetchInterval: 10000,
  });

  const bots = (status?.bots || []) as BotStatus[];
  const runningCount = bots.filter((b) => b.isRunning).length;
  const totalCompleted = bots.reduce((s, b) => s + b.completedCount, 0);
  const totalErrors = bots.reduce((s, b) => s + b.errorCount, 0);
  const isRunning = runningCount > 0;
  const hasIssue = status && (!status.pythonFound || !status.botScriptFound);
  const canStart = !hasIssue && !isFixingPrompts && (pendingPhotos > 0 || pendingVideos > 0);

  const handleStart = async () => {
    try {
      for (let i = 1; i <= botCount; i++) {
        await api.startBot(projectId, i, i);
      }
      refetch();
    } catch (err) {
      alert(String(err));
    }
  };

  const handleStop = async () => {
    try {
      await api.stopBot();
      refetch();
    } catch (err) {
      alert(String(err));
    }
  };

  // Оставшиеся в текущем проходе (pending минус уже сгенерированные ботами)
  const remainingPhotos = Math.max(0, pendingPhotos - totalCompleted);
  const remainingVideos = pendingVideos;

  return (
    <div className="border-t border-surface-lighter pt-3 mt-3">
      <span className="text-xs font-medium text-gray-500 uppercase tracking-wider px-1">
        Генерация
      </span>

      {hasIssue && (
        <div className="mt-2 px-2 py-1.5 bg-amber-900/20 rounded text-xs text-amber-400 flex items-center gap-1.5">
          <AlertTriangle size={12} />
          {!status.pythonFound ? 'Python не найден' : 'Бот не найден'}
        </div>
      )}

      <div className="mt-2 space-y-2">

        {/* Ожидают генерации — всегда видно */}
        <div className="px-2 py-2 bg-surface rounded-lg space-y-1">
          <span className="text-[10px] text-gray-500 uppercase">
            {isRunning ? 'Осталось' : 'Ожидают генерации'}
          </span>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <Image size={12} className="text-blue-400" />
              <span className="text-sm font-medium">{isRunning ? remainingPhotos : pendingPhotos}</span>
              <span className="text-[11px] text-gray-500">фото</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Video size={12} className="text-purple-400" />
              <span className="text-sm font-medium">{isRunning ? remainingVideos : pendingVideos}</span>
              <span className="text-[11px] text-gray-500">видео</span>
            </div>
          </div>
        </div>

        {/* Исправление промптов */}
        {isFixingPrompts && (
          <div className="px-2 py-2 bg-amber-900/10 border border-amber-900/20 rounded-lg">
            <div className="flex items-center gap-1.5 mb-1">
              <Loader2 size={12} className="text-amber-400 animate-spin" />
              <span className="text-xs text-amber-300">Исправление промптов</span>
            </div>
            <div className="h-1.5 bg-surface-lighter rounded-full overflow-hidden">
              <div
                className="h-full bg-amber-400 rounded-full transition-all"
                style={{ width: fixProgress[1] > 0 ? `${(fixProgress[0] / fixProgress[1]) * 100}%` : '0%' }}
              />
            </div>
            <span className="text-[10px] text-gray-500 mt-0.5 block">
              {fixProgress[0]} / {fixProgress[1]}
            </span>
          </div>
        )}

        {!isRunning ? (
          <>
            {/* Количество ботов */}
            <div className="flex items-center justify-between px-1">
              <span className="text-xs text-gray-400">Ботов:</span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setBotCount(Math.max(1, botCount - 1))}
                  className="w-6 h-6 flex items-center justify-center bg-surface rounded border border-surface-lighter hover:border-accent transition-colors"
                >
                  <Minus size={10} />
                </button>
                <span className="text-sm font-bold w-5 text-center">{botCount}</span>
                <button
                  onClick={() => setBotCount(botCount + 1)}
                  className="w-6 h-6 flex items-center justify-center bg-surface rounded border border-surface-lighter hover:border-accent transition-colors"
                >
                  <Plus size={10} />
                </button>
              </div>
            </div>

            {/* Кнопка запуска + подпись */}
            <button
              onClick={handleStart}
              disabled={!canStart}
              className="w-full py-2 bg-accent hover:bg-accent-hover rounded-lg text-sm font-medium transition-colors disabled:opacity-40 flex items-center justify-center gap-2"
            >
              <Play size={14} />
              Запустить генерацию
            </button>
            {isFixingPrompts && (
              <p className="text-[10px] text-amber-400 text-center">
                Идёт составление промптов...
              </p>
            )}
            {!isFixingPrompts && pendingPhotos === 0 && pendingVideos === 0 && (
              <p className="text-[10px] text-gray-500 text-center">
                Нет кадров для генерации
              </p>
            )}
          </>
        ) : (
          <>
            {/* Статус генерации */}
            <div className="px-2 py-2 bg-green-900/10 border border-green-900/20 rounded-lg">
              <div className="flex items-center gap-1.5 mb-1.5">
                <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                <span className="text-xs text-green-300">Идёт генерация кадров</span>
              </div>
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="text-gray-400">{runningCount} ботов</span>
                <span className="text-green-400">{totalCompleted} готово</span>
              </div>
              {/* Прогресс-бар */}
              {(pendingPhotos + pendingVideos) > 0 && (
                <div className="h-1.5 bg-surface-lighter rounded-full overflow-hidden">
                  <div
                    className="h-full bg-green-400 rounded-full transition-all"
                    style={{ width: `${(totalCompleted / (pendingPhotos + pendingVideos)) * 100}%` }}
                  />
                </div>
              )}
              {totalErrors > 0 && (
                <span className="text-[10px] text-red-400 mt-1 block">{totalErrors} ошибок</span>
              )}
            </div>

            {/* Кнопка остановки */}
            <button
              onClick={handleStop}
              className="w-full py-2 bg-red-900/30 text-red-400 hover:bg-red-900/50 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2"
            >
              <Square size={14} />
              Остановить генерацию
            </button>
          </>
        )}
      </div>
    </div>
  );
}
