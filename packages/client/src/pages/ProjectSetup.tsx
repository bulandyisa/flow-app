import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useProject } from '@/api/hooks';
import { useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import { Upload, Users, FileText, ArrowRight, CheckCircle, Loader2 } from 'lucide-react';
import { ScreenplayUpload } from '@/components/project/ScreenplayUpload';
import { ReferencesStep } from '@/components/project/ReferencesStep';
import { GAS, botsForGa, gaForBot } from '@flow-app/shared';

interface ProjectData {
  id: string;
  nameRu: string;
  phase: string;
  screenplayFile: string | null;
  flowProjectId?: string;
  flowProjectIdByGA?: { 1?: string; 2?: string };
  flowProjectIdByBot?: { [bot: number]: string };
  flowAccountEmailByGA?: { 1?: string; 2?: string };
  characters: Array<{
    id: string;
    name: string;
    nameRu: string;
    clothing: string;
    description: string;
    baseImage: string | null;
    angles: Array<{ id: string; file: string; description: string; status: string }>;
    status: string;
  }>;
  locations: Array<{
    id: string;
    name: string;
    nameRu: string;
    description: string;
    baseImage: string | null;
    angles: Array<{ id: string; file: string; description: string; status: string }>;
    status: string;
  }>;
}

const STEPS = [
  { id: 'screenplay', label: 'Сценарий', icon: Upload },
  { id: 'prompts', label: 'Промпты', icon: FileText },
  { id: 'references', label: 'Референсы', icon: Users },
] as const;

export function ProjectSetup() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: project, isLoading } = useProject(id!);
  const [isGeneratingPrompts, setIsGeneratingPrompts] = useState(false);
  const [promptError, setPromptError] = useState<string | null>(null);
  const [activeStep, setActiveStep] = useState<string | null>(null);

  const refreshProject = () => {
    queryClient.invalidateQueries({ queryKey: ['project', id] });
  };

  if (isLoading) return <div className="text-gray-400">Загрузка...</div>;
  if (!project) return <div className="text-danger">Проект не найден</div>;

  const proj = project as ProjectData;
  const currentStepIdx = STEPS.findIndex((s) => s.id === proj.phase);

  const canAdvance = () => {
    switch (proj.phase) {
      case 'screenplay':
        return !!proj.screenplayFile;
      case 'prompts':
        return false; // промпты загружаются файлом, не через "Далее"
      case 'references':
        return proj.characters.length > 0 || proj.locations.length > 0;
      default:
        return false;
    }
  };

  const handleAdvance = async () => {
    await api.advancePhase(proj.id);
    refreshProject();
  };

  // handleGeneratePrompts removed — промпты загружаются файлом

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">{proj.nameRu}</h1>

      {/* Привязка к проектам Google Flow — по одному UUID на каждого бота */}
      <FlowProjectBinding
        projectId={proj.id}
        flowProjectId={proj.flowProjectId}
        flowProjectIdByGA={proj.flowProjectIdByGA}
        flowProjectIdByBot={proj.flowProjectIdByBot}
        flowAccountEmailByGA={proj.flowAccountEmailByGA}
        onSaved={refreshProject}
      />

      {/* Stepper — кликабельный */}
      <div className="flex items-center gap-2 mb-8">
        {STEPS.map((step, idx) => {
          const isPhaseActive = idx === currentStepIdx;
          const isDone = idx < currentStepIdx;
          const isViewing = (activeStep || proj.phase) === step.id;
          const Icon = step.icon;

          return (
            <div key={step.id} className="flex items-center gap-2">
              <button
                onClick={() => setActiveStep(step.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors ${
                  isViewing
                    ? 'border-accent bg-accent/10 text-accent'
                    : isDone
                      ? 'border-green-700/30 bg-green-900/10 text-green-400 hover:border-green-600/50'
                      : 'border-surface-lighter text-gray-500 hover:border-gray-500'
                }`}
              >
                {isDone ? <CheckCircle size={16} /> : <Icon size={16} />}
                <span className="text-sm font-medium">{step.label}</span>
              </button>
              {idx < STEPS.length - 1 && (
                <div className={`w-8 h-px ${isDone ? 'bg-green-700' : 'bg-surface-lighter'}`} />
              )}
            </div>
          );
        })}
      </div>

      {/* Контент выбранного шага */}
      {(() => { const viewingStep = activeStep || proj.phase; return (
      <div className="bg-surface-light rounded-lg border border-surface-lighter p-6">
        {/* Шаг 1: Сценарий */}
        {viewingStep === 'screenplay' && (
          <ScreenplayUpload
            projectId={proj.id}
            hasScreenplay={!!proj.screenplayFile}
            onUploaded={refreshProject}
          />
        )}

        {/* Шаг 2: Промпты */}
        {viewingStep === 'prompts' && (proj.screenplayFile ? (
          <div className="py-8">
            <div className="text-center mb-6">
              <FileText size={48} className="mx-auto text-gray-500 mb-4" />
              <h2 className="text-xl font-medium mb-2">Загрузите промпты</h2>
              <p className="text-gray-400">
                Загрузите готовый файл all_prompts.json с промптами для всех клипов
              </p>
            </div>
            {promptError && (
              <div className="mb-4 px-4 py-2 bg-red-900/20 border border-red-900/30 rounded-lg text-sm text-red-400">
                {promptError}
              </div>
            )}
            <div className="flex justify-center">
              <label className="inline-flex items-center gap-2 px-6 py-3 bg-accent hover:bg-accent-hover rounded-lg cursor-pointer transition-colors">
                <Upload size={18} />
                <span>{isGeneratingPrompts ? 'Загрузка...' : 'Выбрать all_prompts.json'}</span>
                <input
                  type="file"
                  accept=".json"
                  className="hidden"
                  onChange={async (e) => {
                    const file = e.target.files?.[0];
                    if (!file) return;
                    setIsGeneratingPrompts(true);
                    setPromptError(null);
                    try {
                      await api.uploadPrompts(proj.id, file);
                      setActiveStep(null);
                      refreshProject();
                    } catch (err) {
                      setPromptError(err instanceof Error ? err.message : String(err));
                    } finally {
                      setIsGeneratingPrompts(false);
                    }
                  }}
                />
              </label>
            </div>
          </div>
        ) : (
          <div className="text-center py-12">
            <FileText size={48} className="mx-auto text-gray-500 mb-4" />
            <h2 className="text-xl font-medium mb-2">Промпты</h2>
            <p className="text-gray-400">
              Сначала загрузите сценарий на первом шаге.
            </p>
          </div>
        ))}

        {/* Шаг 3: Референсы (персонажи + локации) */}
        {viewingStep === 'references' && (
          <ReferencesStep
            projectId={proj.id}
            characters={proj.characters}
            locations={proj.locations}
            hasScreenplay={!!proj.screenplayFile}
            onUpdate={refreshProject}
          />
        )}

      </div>
      ); })()}

      {/* Кнопка "Далее" */}
      {canAdvance() && (
        <div className="mt-4 flex justify-end">
          <button
            onClick={handleAdvance}
            className="flex items-center gap-2 px-6 py-2.5 bg-accent hover:bg-accent-hover rounded-lg transition-colors"
          >
            <span>Далее</span>
            <ArrowRight size={16} />
          </button>
        </div>
      )}
    </div>
  );
}

/** Привязка flow-app проекта к проектам Google Flow — по одному UUID на каждого бота. */
function FlowProjectBinding({
  projectId,
  flowProjectId,
  flowProjectIdByGA,
  flowProjectIdByBot,
  flowAccountEmailByGA,
  onSaved,
}: {
  projectId: string;
  flowProjectId?: string;
  flowProjectIdByGA?: { 1?: string; 2?: string };
  flowProjectIdByBot?: { [bot: number]: string };
  flowAccountEmailByGA?: { 1?: string; 2?: string };
  onSaved: () => void;
}) {
  return (
    <div className="mb-6 p-4 bg-surface-light rounded-lg border border-surface-lighter">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-medium">Проекты Google Flow</h3>
      </div>
      <p className="text-xs text-gray-500 mb-3">
        Каждый бот работает в своём Flow-проекте, чтобы не конкурировать за одну сессию.
        Если у бота не задан URL — при первом запуске он сам запомнит текущий проект своего
        аккаунта.
      </p>
      <div className="space-y-4">
        {GAS.map((ga) => {
          const bots = botsForGa(ga);
          const email = flowAccountEmailByGA?.[ga];
          return (
            <div key={ga} className="p-3 bg-surface rounded border border-surface-lighter">
              <div className="text-sm font-medium mb-2">
                Google-аккаунт {ga}
                {email ? (
                  <span className="text-gray-400 font-normal"> — {email}</span>
                ) : (
                  <span className="text-gray-600 font-normal italic"> — email появится после первого запуска</span>
                )}
              </div>
              <div className="space-y-1.5">
                {bots.map((bot) => (
                  <BotRow
                    key={bot}
                    projectId={projectId}
                    bot={bot}
                    ownUuid={flowProjectIdByBot?.[bot]}
                    fallbackUuid={
                      flowProjectIdByGA?.[gaForBot(bot)] ||
                      (gaForBot(bot) === 1 ? flowProjectId : undefined)
                    }
                    existingMap={flowProjectIdByBot}
                    onSaved={onSaved}
                  />
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/** Одна строка: бот N — UUID, [Сменить] [Отвязать]. */
function BotRow({
  projectId,
  bot,
  ownUuid,
  fallbackUuid,
  existingMap,
  onSaved,
}: {
  projectId: string;
  bot: number;
  ownUuid?: string;
  fallbackUuid?: string;
  existingMap?: { [bot: number]: string };
  onSaved: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState('');
  const [saving, setSaving] = useState(false);
  const [detaching, setDetaching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const extractUuid = (input: string): string | null => {
    const match = input.trim().match(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i);
    return match ? match[0].toLowerCase() : null;
  };

  const handleSave = async () => {
    const uuid = extractUuid(value);
    if (!uuid) {
      setError('Вставьте URL проекта Google Flow или его UUID');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const merged = { ...(existingMap || {}), [bot]: uuid };
      await api.updateProject(projectId, { flowProjectIdByBot: merged });
      setEditing(false);
      setValue('');
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  };

  const handleDetach = async () => {
    if (!ownUuid) return;
    if (!window.confirm(`Отвязать бота ${bot} от собственного Flow-проекта? Бот вернётся к общему проекту аккаунта.`)) {
      return;
    }
    setDetaching(true);
    setError(null);
    try {
      const { [bot]: _omit, ...rest } = existingMap || {};
      await api.updateProject(projectId, { flowProjectIdByBot: rest });
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setDetaching(false);
    }
  };

  const shortUuid = (u: string) => `${u.slice(0, 8)}…${u.slice(-4)}`;
  const hasOwn = !!ownUuid;
  const hasFallback = !!fallbackUuid;

  return (
    <div className="pl-3 border-l border-surface-lighter">
      <div className="flex items-center justify-between gap-3 py-1">
        <div className="min-w-0 flex items-center gap-3">
          <span className="text-xs text-gray-400 w-14 shrink-0">Бот {bot}</span>
          {hasOwn ? (
            <span className="text-xs text-green-400 font-mono" title={ownUuid}>
              {shortUuid(ownUuid!)}
            </span>
          ) : hasFallback ? (
            <span
              className="text-xs text-gray-500 font-mono"
              title={`${fallbackUuid} — наследуется от аккаунта, нажмите «Сменить», чтобы задать свой`}
            >
              {shortUuid(fallbackUuid!)} <span className="text-gray-600 italic">(общий)</span>
            </span>
          ) : (
            <span className="text-xs text-gray-600">—</span>
          )}
        </div>
        {!editing && (
          <div className="flex items-center gap-3 shrink-0">
            <button
              onClick={() => setEditing(true)}
              className="text-xs text-gray-400 hover:text-accent underline-offset-2 hover:underline"
            >
              Сменить
            </button>
            <button
              onClick={handleDetach}
              disabled={!hasOwn || detaching}
              className="text-xs text-gray-500 hover:text-red-400 underline-offset-2 hover:underline disabled:opacity-30 disabled:hover:no-underline"
              title={hasOwn ? 'Удалить собственный UUID этого бота' : 'Собственный UUID не задан'}
            >
              {detaching ? 'Отвязка…' : 'Отвязать'}
            </button>
          </div>
        )}
      </div>
      {editing && (
        <div className="mt-2 mb-1 flex items-center gap-2">
          <input
            type="text"
            autoFocus
            placeholder="https://labs.google/fx/ru/tools/flow/project/..."
            value={value}
            onChange={(e) => { setValue(e.target.value); setError(null); }}
            className="flex-1 px-3 py-1.5 bg-surface-light rounded border border-surface-lighter focus:border-accent outline-none text-xs font-mono"
          />
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-3 py-1.5 bg-accent hover:bg-accent-hover rounded text-xs transition-colors disabled:opacity-50"
          >
            {saving ? 'Сохранение…' : 'Сохранить'}
          </button>
          <button
            onClick={() => { setEditing(false); setValue(''); setError(null); }}
            className="px-2 py-1.5 text-gray-400 hover:text-white text-xs"
          >
            Отмена
          </button>
        </div>
      )}
      {error && <p className="mt-1 text-xs text-red-400">{error}</p>}
    </div>
  );
}
