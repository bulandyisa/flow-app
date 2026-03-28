import { useState, useEffect } from 'react';
import { useSettings } from '@/api/hooks';
import { api } from '@/api/client';
import { Save, Key, Github } from 'lucide-react';

export function Settings() {
  const { data: settings, isLoading } = useSettings();
  const [claudeApiKey, setClaudeApiKey] = useState('');
  const [githubToken, setGithubToken] = useState('');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (settings) {
      const s = settings as { claudeApiKey: string; githubToken: string };
      setClaudeApiKey(s.claudeApiKey || '');
      setGithubToken(s.githubToken || '');
    }
  }, [settings]);

  const handleSave = async () => {
    const updates: Record<string, string> = {};
    if (!claudeApiKey.startsWith('***')) updates.claudeApiKey = claudeApiKey;
    if (!githubToken.startsWith('***')) updates.githubToken = githubToken;
    await api.updateSettings(updates);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  if (isLoading) return <div className="text-gray-400">Загрузка...</div>;

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold mb-6">Настройки</h1>

      <div className="space-y-6">
        {/* Claude API */}
        <div className="p-4 bg-surface-light rounded-lg border border-surface-lighter">
          <div className="flex items-center gap-2 mb-3">
            <Key size={18} className="text-accent" />
            <h3 className="font-medium">Claude API</h3>
          </div>
          <input
            type="password"
            placeholder="sk-ant-..."
            value={claudeApiKey}
            onChange={(e) => setClaudeApiKey(e.target.value)}
            className="w-full px-3 py-2 bg-surface rounded-lg border border-surface-lighter focus:border-accent outline-none font-mono text-sm"
          />
          <p className="text-xs text-gray-500 mt-1">
            Ключ для Claude Opus 4.6. Получить на console.anthropic.com
          </p>
        </div>

        {/* GitHub */}
        <div className="p-4 bg-surface-light rounded-lg border border-surface-lighter">
          <div className="flex items-center gap-2 mb-3">
            <Github size={18} className="text-accent" />
            <h3 className="font-medium">GitHub</h3>
          </div>
          <input
            type="password"
            placeholder="ghp_..."
            value={githubToken}
            onChange={(e) => setGithubToken(e.target.value)}
            className="w-full px-3 py-2 bg-surface rounded-lg border border-surface-lighter focus:border-accent outline-none font-mono text-sm"
          />
          <p className="text-xs text-gray-500 mt-1">
            Personal access token для обновлений и библиотеки референсов
          </p>
        </div>

        {/* Сохранить */}
        <button
          onClick={handleSave}
          className={`flex items-center gap-2 px-6 py-2.5 rounded-lg transition-colors ${
            saved
              ? 'bg-success text-white'
              : 'bg-accent hover:bg-accent-hover text-white'
          }`}
        >
          <Save size={18} />
          <span>{saved ? 'Сохранено!' : 'Сохранить'}</span>
        </button>
      </div>
    </div>
  );
}
