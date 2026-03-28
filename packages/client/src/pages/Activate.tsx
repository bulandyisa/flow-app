import { useState } from 'react';
import { KeyRound, Loader2 } from 'lucide-react';
import { useActivate } from '@/api/hooks';

export function Activate() {
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const activate = useActivate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!code.trim()) {
      setError('Введите код активации');
      return;
    }

    try {
      await activate.mutateAsync(code.trim());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка активации');
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-surface">
      <div className="w-full max-w-md p-8">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-accent/20 mb-4">
            <KeyRound size={32} className="text-accent" />
          </div>
          <h1 className="text-2xl font-bold text-white">Flow App</h1>
          <p className="text-gray-500 mt-1">Производство мультфильмов</p>
        </div>

        {/* Activation form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="p-6 bg-surface-light rounded-xl border border-surface-lighter">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Код активации
            </label>
            <input
              type="text"
              value={code}
              onChange={(e) => { setCode(e.target.value); setError(''); }}
              placeholder="Введите код..."
              autoFocus
              className="w-full px-4 py-3 bg-surface rounded-lg border border-surface-lighter focus:border-accent outline-none font-mono text-lg tracking-wider text-center text-white placeholder:text-gray-600"
            />
            {error && (
              <p className="mt-3 text-sm text-red-400">{error}</p>
            )}
          </div>

          <button
            type="submit"
            disabled={activate.isPending || !code.trim()}
            className="w-full flex items-center justify-center gap-2 px-6 py-3 rounded-lg bg-accent hover:bg-accent-hover disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium transition-colors"
          >
            {activate.isPending ? (
              <>
                <Loader2 size={18} className="animate-spin" />
                <span>Проверка...</span>
              </>
            ) : (
              <span>Активировать</span>
            )}
          </button>
        </form>

        <p className="text-center text-xs text-gray-600 mt-6">
          Нет кода? Обратитесь к администратору.
        </p>
      </div>
    </div>
  );
}
