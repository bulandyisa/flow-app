import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';
import { Play, Square, Minus, Plus, AlertTriangle, ChevronDown, Terminal } from 'lucide-react';

interface BotStatus {
  id: number;
  account: number;
  isRunning: boolean;
  currentClip: string | null;
  currentAction: string | null;
  completedCount: number;
  errorCount: number;
  startedAt: string | null;
  exitCode: number | null;
}

interface SystemStatus {
  bots: BotStatus[];
  pythonFound: boolean;
  botScriptFound: boolean;
}

export function BotControl() {
  const { id: projectId } = useParams<{ id: string }>();
  const [botCount, setBotCount] = useState(6);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const { data: status, refetch } = useQuery({
    queryKey: ['bot-status'],
    queryFn: api.getBotStatus,
    refetchInterval: 3000,
  });

  const sys = status as SystemStatus | undefined;
  const bots = sys?.bots || [];
  const runningCount = bots.filter((b) => b.isRunning).length;
  const totalCompleted = bots.reduce((s, b) => s + b.completedCount, 0);
  const totalErrors = bots.reduce((s, b) => s + b.errorCount, 0);
  const isRunning = runningCount > 0;

  // Системные проблемы
  const hasSystemIssue = sys && (!sys.pythonFound || !sys.botScriptFound);

  const handleStart = async () => {
    if (!projectId) return;
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

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Генерация</h1>

      {/* Системные проблемы */}
      {hasSystemIssue && (
        <div className="mb-6 p-4 bg-amber-900/20 border border-amber-800/30 rounded-lg flex items-start gap-3">
          <AlertTriangle size={18} className="text-amber-400 mt-0.5 flex-shrink-0" />
          <div className="text-sm">
            {!sys.pythonFound && <p className="text-amber-300">Python не найден. Установите Python 3 и Playwright.</p>}
            {!sys.botScriptFound && <p className="text-amber-300">Скрипт бота не найден.</p>}
          </div>
        </div>
      )}

      {/* Основной блок */}
      <div className="bg-surface-light rounded-lg border border-surface-lighter p-6">

        {!isRunning ? (
          <>
            {/* Выбор количества ботов */}
            <div className="flex items-center justify-center gap-6 mb-6">
              <span className="text-gray-400">Количество ботов:</span>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setBotCount(Math.max(1, botCount - 1))}
                  className="w-8 h-8 flex items-center justify-center bg-surface rounded-lg border border-surface-lighter hover:border-accent transition-colors"
                >
                  <Minus size={14} />
                </button>
                <span className="text-2xl font-bold w-10 text-center">{botCount}</span>
                <button
                  onClick={() => setBotCount(botCount + 1)}
                  className="w-8 h-8 flex items-center justify-center bg-surface rounded-lg border border-surface-lighter hover:border-accent transition-colors"
                >
                  <Plus size={14} />
                </button>
              </div>
            </div>

            <p className="text-center text-xs text-gray-500 mb-6">
              Каждый бот использует ~500-800 МБ оперативной памяти
            </p>

            {/* Кнопка запуска */}
            <button
              onClick={handleStart}
              disabled={!!hasSystemIssue}
              className="w-full py-4 bg-accent hover:bg-accent-hover rounded-lg text-lg font-medium transition-colors disabled:opacity-40 flex items-center justify-center gap-3"
            >
              <Play size={22} />
              Запустить генерацию
            </button>
          </>
        ) : (
          <>
            {/* Прогресс */}
            <div className="text-center mb-6">
              <div className="flex items-center justify-center gap-2 mb-2">
                <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse" />
                <span className="text-lg font-medium">Генерация идёт</span>
              </div>
              <p className="text-gray-400">
                {runningCount} {runningCount === 1 ? 'бот работает' : 'ботов работают'}
              </p>
            </div>

            {/* Счётчики */}
            <div className="grid grid-cols-2 gap-3 mb-6">
              <div className="text-center p-3 bg-surface rounded-lg">
                <div className="text-2xl font-bold text-green-400">{totalCompleted}</div>
                <div className="text-xs text-gray-500">Клипов готово</div>
              </div>
              <div className="text-center p-3 bg-surface rounded-lg">
                <div className="text-2xl font-bold text-red-400">{totalErrors}</div>
                <div className="text-xs text-gray-500">Ошибок</div>
              </div>
            </div>

            {/* Текущие задания */}
            <div className="mb-6 space-y-1.5">
              {bots.filter((b) => b.isRunning).map((bot) => (
                <div key={bot.id} className="flex items-center gap-3 px-3 py-2 bg-surface rounded-lg text-sm">
                  <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                  <span className="text-gray-500">Bot {bot.id}</span>
                  <span className="text-gray-300">
                    {bot.currentClip || 'Запускается...'}
                  </span>
                  {bot.currentAction && (
                    <span className="text-xs text-gray-500 ml-auto">{bot.currentAction}</span>
                  )}
                </div>
              ))}
            </div>

            {/* Кнопка остановки */}
            <button
              onClick={handleStop}
              className="w-full py-3 bg-red-900/30 text-red-400 hover:bg-red-900/50 rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
            >
              <Square size={18} />
              Остановить генерацию
            </button>
          </>
        )}
      </div>

      {/* Расширенные настройки (для отладки) */}
      <div className="mt-4">
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="flex items-center gap-2 text-xs text-gray-500 hover:text-gray-300 transition-colors"
        >
          <ChevronDown size={12} className={`transition-transform ${showAdvanced ? 'rotate-180' : ''}`} />
          Расширенные настройки
        </button>

        {showAdvanced && (
          <div className="mt-2 p-4 bg-surface rounded-lg border border-surface-lighter text-xs text-gray-500 space-y-1">
            <p>Python: {(sys as SystemStatus & { pythonPath?: string })?.pythonPath || 'не найден'}</p>
            <p>Скрипт: {(sys as SystemStatus & { botScriptPath?: string })?.botScriptPath || 'не найден'}</p>
            <p>Ботов запущено: {runningCount}</p>
            {bots.map((bot) => (
              <p key={bot.id}>
                Bot {bot.id}: {bot.isRunning ? 'работает' : bot.exitCode != null ? `завершён (${bot.exitCode})` : 'остановлен'}
                {bot.completedCount > 0 && ` — ${bot.completedCount} клипов`}
              </p>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
