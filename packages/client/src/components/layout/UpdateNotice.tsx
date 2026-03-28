import { useEffect, useState } from 'react';
import { ArrowDownCircle, X } from 'lucide-react';
import { api } from '@/api/client';

interface UpdateInfo {
  currentVersion: string;
  latestVersion: string;
  releaseName?: string;
  releaseNotes?: string;
}

export function UpdateNotice() {
  const [update, setUpdate] = useState<UpdateInfo | null>(null);
  const [dismissed, setDismissed] = useState(false);
  const [version, setVersion] = useState<string>('');

  useEffect(() => {
    // Показываем текущую версию
    api.getVersion().then(v => setVersion(v.version)).catch(() => {});

    // Проверяем обновления раз в 30 минут
    const check = () => {
      api.checkUpdate().then(data => {
        if (data.updateAvailable && data.latestVersion) {
          setUpdate({
            currentVersion: data.currentVersion,
            latestVersion: data.latestVersion,
            releaseName: data.releaseName,
            releaseNotes: data.releaseNotes,
          });
        }
      }).catch(() => {});
    };

    check();
    const interval = setInterval(check, 30 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  if (dismissed || !update) {
    return (
      <div className="px-4 py-2 text-xs text-gray-600">
        {version && `v${version}`}
      </div>
    );
  }

  return (
    <div className="mx-3 mb-2 p-3 bg-accent/10 border border-accent/30 rounded-lg">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 text-accent">
          <ArrowDownCircle size={16} />
          <span className="text-sm font-medium">Обновление</span>
        </div>
        <button
          onClick={() => setDismissed(true)}
          className="text-gray-500 hover:text-gray-300 p-0.5"
        >
          <X size={14} />
        </button>
      </div>
      <p className="text-xs text-gray-400 mt-1.5">
        Доступна версия {update.latestVersion}
        {update.releaseName && ` — ${update.releaseName}`}
      </p>
      <p className="text-xs text-gray-500 mt-1">
        Перезапустите приложение для обновления
      </p>
    </div>
  );
}
