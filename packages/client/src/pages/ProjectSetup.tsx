import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useProject } from '@/api/hooks';
import { useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import { Upload, Users, FileText, ArrowRight, CheckCircle, Loader2 } from 'lucide-react';
import { ScreenplayUpload } from '@/components/project/ScreenplayUpload';
import { ReferencesStep } from '@/components/project/ReferencesStep';

interface ProjectData {
  id: string;
  nameRu: string;
  phase: string;
  screenplayFile: string | null;
  flowProjectId?: string;
  flowProjectIdByGA?: { 1?: string; 2?: string };
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

      {/* Привязка к проекту Google Flow — по одному UUID на Google-аккаунт */}
      <FlowProjectBinding
        projectId={proj.id}
        flowProjectId={proj.flowProjectId}
        flowProjectIdByGA={proj.flowProjectIdByGA}
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

/** Привязка flow-app проекта к проектам Google Flow — по одному UUID на Google-аккаунт. */
function FlowProjectBinding({
  projectId,
  flowProjectId,
  flowProjectIdByGA,
  flowAccountEmailByGA,
  onSaved,
}: {
  projectId: string;
  flowProjectId?: string;
  flowProjectIdByGA?: { 1?: string; 2?: string };
  flowAccountEmailByGA?: { 1?: string; 2?: string };
  onSaved: () => void;
}) {
  // Legacy UUID показываем только если нет значения для GA1 (предыдущее поведение).
  const effective: { 1?: string; 2?: string } = {
    1: flowProjectIdByGA?.[1] || flowProjectId,
    2: flowProjectIdByGA?.[2],
  };

  const rows: Array<{ ga: 1 | 2; label: string; bots: string }> = [
    { ga: 1, label: 'Google-аккаунт 1', bots: 'Боты 1, 2, 5' },
    { ga: 2, label: 'Google-аккаунт 2', bots: 'Боты 3, 4, 6' },
  ];

  return (
    <div className="mb-6 p-4 bg-surface-light rounded-lg border border-surface-lighter">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-medium">Проекты Google Flow</h3>
      </div>
      <p className="text-xs text-gray-500 mb-3">
        Каждый Google-аккаунт хранит свои проекты Flow отдельно. Боты одного аккаунта работают
        только в своём UUID. При первом запуске бот сам запомнит проект и email.
      </p>
      <div className="space-y-2">
        {rows.map((row) => (
          <GAFlowRow
            key={row.ga}
            projectId={projectId}
            ga={row.ga}
            label={row.label}
            bots={row.bots}
            currentUuid={effective[row.ga]}
            currentEmail={flowAccountEmailByGA?.[row.ga]}
            existingMap={flowProjectIdByGA}
            onSaved={onSaved}
          />
        ))}
      </div>
    </div>
  );
}

function GAFlowRow({
  projectId,
  ga,
  label,
  bots,
  currentUuid,
  currentEmail,
  existingMap,
  onSaved,
}: {
  projectId: string;
  ga: 1 | 2;
  label: string;
  bots: string;
  currentUuid?: string;
  currentEmail?: string;
  existingMap?: { 1?: string; 2?: string };
  onSaved: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState('');
  const [saving, setSaving] = useState(false);
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
      // Мержим с существующей картой, чтобы не затереть другой GA-слот.
      const merged = { ...(existingMap || {}), [ga]: uuid };
      await api.updateProject(projectId, { flowProjectIdByGA: merged });
      setEditing(false);
      setValue('');
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  };

  const isBound = !!currentUuid;

  return (
    <div className="p-3 bg-surface rounded border border-surface-lighter">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="text-sm font-medium">
            {label} <span className="text-gray-500 font-normal">— {bots}</span>
          </div>
          <div className="text-xs mt-0.5 flex flex-wrap items-center gap-x-2">
            {isBound ? (
              <span className="text-green-400 font-mono" title={currentUuid}>
                {currentUuid!.slice(0, 8)}…{currentUuid!.slice(-4)}
              </span>
            ) : (
              <span className="text-gray-500">Будет выбран автоматически при первом запуске</span>
            )}
            {currentEmail ? (
              <span className="text-gray-400" title={currentEmail}>· {currentEmail}</span>
            ) : (
              <span className="text-gray-600 italic">· email будет определён при первом запуске</span>
            )}
          </div>
        </div>
        {!editing && (
          <button
            onClick={() => setEditing(true)}
            className="text-xs text-gray-400 hover:text-accent underline-offset-2 hover:underline shrink-0"
          >
            Сменить вручную
          </button>
        )}
      </div>
      {editing && (
        <div className="mt-3 flex items-center gap-2">
          <input
            type="text"
            autoFocus
            placeholder="https://labs.google/fx/ru/tools/flow/project/..."
            value={value}
            onChange={(e) => { setValue(e.target.value); setError(null); }}
            className="flex-1 px-3 py-2 bg-surface-light rounded border border-surface-lighter focus:border-accent outline-none text-sm font-mono"
          />
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 bg-accent hover:bg-accent-hover rounded text-sm transition-colors disabled:opacity-50"
          >
            {saving ? 'Сохранение…' : 'Сохранить'}
          </button>
          <button
            onClick={() => { setEditing(false); setValue(''); setError(null); }}
            className="px-3 py-2 text-gray-400 hover:text-white text-sm"
          >
            Отмена
          </button>
        </div>
      )}
      {error && <p className="mt-2 text-xs text-red-400">{error}</p>}
    </div>
  );
}
