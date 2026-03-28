import { useState, useEffect, useCallback } from 'react';
import {
  Sparkles, CheckCircle, AlertCircle, Plus, Trash2,
  User, Users, MapPin, Image, ChevronDown, ChevronRight,
  Loader2, Camera, RefreshCw,
} from 'lucide-react';
import { api } from '@/api/client';
import { VariantGrid } from '@/components/review/VariantGrid';

interface Variant {
  file: string;
  scores: Record<string, number> | null;
  avg: number | null;
}

interface RefAttempt {
  attempt: number;
  prompt: string;
  variants: Variant[];
}

interface RefManifest {
  itemId: string;
  type: string;
  target: string;
  status: string;
  feedback: string;
  attempts: RefAttempt[];
  selected_variant: { attempt: number; variant: number } | null;
}

interface RefReviewItem {
  itemId: string;
  type: 'characters' | 'locations';
  name: string;
  nameRu: string;
  target: 'base' | 'angle';
  angleId?: string;
  angleDescription?: string;
  manifest: RefManifest;
  variantPaths: string[];
}

interface Character {
  id: string;
  name: string;
  nameRu: string;
  clothing: string;
  description: string;
  baseImage: string | null;
  angles: Array<{ id: string; file: string; description: string; status: string }>;
  status: string;
}

interface Location {
  id: string;
  name: string;
  nameRu: string;
  description: string;
  baseImage: string | null;
  angles: Array<{ id: string; file: string; description: string; status: string }>;
  status: string;
}

interface ReferencesStepProps {
  projectId: string;
  characters: Character[];
  locations: Location[];
  hasScreenplay: boolean;
  onUpdate: () => void;
}

/** Key for tracking selected variants per review item */
function reviewKey(item: RefReviewItem): string {
  return `${item.type}:${item.itemId}:${item.target}:${item.angleId || ''}`;
}

export function ReferencesStep({
  projectId,
  characters,
  locations,
  hasScreenplay,
  onUpdate,
}: ReferencesStepProps) {
  const [expandedChar, setExpandedChar] = useState<string | null>(null);
  const [expandedLoc, setExpandedLoc] = useState<string | null>(null);

  // Manual add forms
  const [showAddChar, setShowAddChar] = useState(false);
  const [showAddLoc, setShowAddLoc] = useState(false);
  const [charForm, setCharForm] = useState({ name: '', nameRu: '', clothing: '', description: '' });
  const [locForm, setLocForm] = useState({ name: '', nameRu: '', description: '' });

  // Reference review state
  const [reviewItems, setReviewItems] = useState<RefReviewItem[]>([]);
  const [selectedVariants, setSelectedVariants] = useState<Record<string, number | null>>({});
  const [feedbackTexts, setFeedbackTexts] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitMessage, setSubmitMessage] = useState<string | null>(null);

  // Generation state
  const [generating, setGenerating] = useState<Record<string, boolean>>({});
  const [genMessages, setGenMessages] = useState<Record<string, string>>({});

  // ─── Load review items ─────────────────────────
  const loadReviewItems = useCallback(async () => {
    try {
      const data = await api.getReferencesReview(projectId);
      setReviewItems(data.items);
    } catch {
      // Silently ignore — review items may not exist yet
    }
  }, [projectId]);

  useEffect(() => {
    loadReviewItems();
  }, [loadReviewItems]);

  // ─── CRUD characters ──────────────────────────
  const handleAddCharacter = async () => {
    if (!charForm.name.trim()) return;
    await api.addCharacter(projectId, charForm);
    setCharForm({ name: '', nameRu: '', clothing: '', description: '' });
    setShowAddChar(false);
    onUpdate();
  };

  const handleDeleteCharacter = async (charId: string) => {
    await api.deleteCharacter(projectId, charId);
    onUpdate();
  };

  const handleCharacterImage = async (charId: string, file: File) => {
    await api.uploadCharacterImage(projectId, charId, file);
    onUpdate();
  };

  // ─── CRUD locations ───────────────────────────
  const handleAddLocation = async () => {
    if (!locForm.name.trim()) return;
    await api.addLocation(projectId, locForm);
    setLocForm({ name: '', nameRu: '', description: '' });
    setShowAddLoc(false);
    onUpdate();
  };

  const handleDeleteLocation = async (locId: string) => {
    await api.deleteLocation(projectId, locId);
    onUpdate();
  };

  // ─── Generate references ──────────────────────
  const handleGenerate = async (
    type: 'characters' | 'locations',
    itemId: string,
    target: 'base' | 'angles',
  ) => {
    const key = `${type}:${itemId}:${target}`;
    setGenerating((prev) => ({ ...prev, [key]: true }));
    setGenMessages((prev) => ({ ...prev, [key]: '' }));

    try {
      const result = await api.generateReferences(projectId, type, itemId, target);
      setGenMessages((prev) => ({ ...prev, [key]: result.message }));
      onUpdate();
      await loadReviewItems();
    } catch (err) {
      setGenMessages((prev) => ({ ...prev, [key]: `Ошибка: ${err}` }));
    } finally {
      setGenerating((prev) => ({ ...prev, [key]: false }));
    }
  };

  const handleGenerateAllMissing = async () => {
    const pending = [
      ...characters.filter((c) => !c.baseImage).map((c) => ({ type: 'characters' as const, id: c.id })),
      ...locations.filter((l) => !l.baseImage).map((l) => ({ type: 'locations' as const, id: l.id })),
    ];

    for (const item of pending) {
      await handleGenerate(item.type, item.id, 'base');
    }
  };

  // ─── Review actions ───────────────────────────
  const handleSelectVariant = (item: RefReviewItem, variantIndex: number) => {
    const key = reviewKey(item);
    setSelectedVariants((prev) => ({
      ...prev,
      [key]: prev[key] === variantIndex ? null : variantIndex,
    }));
  };

  const handleAccept = async (item: RefReviewItem) => {
    const key = reviewKey(item);
    const variant = selectedVariants[key];
    if (variant == null) return;

    const lastAttempt = item.manifest.attempts[item.manifest.attempts.length - 1];
    if (!lastAttempt) return;

    setSubmitting(true);
    setSubmitMessage(null);

    try {
      const result = await api.submitReferencesReview(projectId, [
        {
          itemId: item.itemId,
          type: item.type,
          target: item.target,
          angleId: item.angleId,
          action: 'accept',
          attempt: lastAttempt.attempt,
          variant,
        },
      ]);

      if (result.allReady) {
        setSubmitMessage('Все референсы готовы!');
      } else {
        setSubmitMessage(`Принято. ${result.accepted} принято, ${result.rejected} отклонено.`);
      }

      // Clear selection
      setSelectedVariants((prev) => ({ ...prev, [key]: null }));
      onUpdate();
      await loadReviewItems();
    } catch (err) {
      setSubmitMessage(`Ошибка: ${err}`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleReject = async (item: RefReviewItem) => {
    const key = reviewKey(item);
    const feedback = feedbackTexts[key] || '';
    if (!feedback.trim()) return;

    setSubmitting(true);
    setSubmitMessage(null);

    try {
      await api.submitReferencesReview(projectId, [
        {
          itemId: item.itemId,
          type: item.type,
          target: item.target,
          angleId: item.angleId,
          action: 'reject',
          feedback,
        },
      ]);

      setFeedbackTexts((prev) => ({ ...prev, [key]: '' }));
      onUpdate();
      await loadReviewItems();
    } catch (err) {
      setSubmitMessage(`Ошибка: ${err}`);
    } finally {
      setSubmitting(false);
    }
  };

  // ─── Status helpers ───────────────────────────
  const statusBadge = (status: string, hasImage: boolean, anglesCount: number) => {
    if (status === 'ready') return <span className="text-xs px-2 py-0.5 rounded bg-green-900/40 text-green-400">Готов</span>;
    if (status === 'angles_review') return <span className="text-xs px-2 py-0.5 rounded bg-blue-900/40 text-blue-400">Ревью ракурсов</span>;
    if (status === 'base_review') return <span className="text-xs px-2 py-0.5 rounded bg-yellow-900/40 text-yellow-400">Ревью базы</span>;
    if (anglesCount >= 15) return <span className="text-xs px-2 py-0.5 rounded bg-blue-900/40 text-blue-400">Ракурсы готовы</span>;
    if (hasImage) return <span className="text-xs px-2 py-0.5 rounded bg-yellow-900/40 text-yellow-400">Нужны ракурсы</span>;
    return <span className="text-xs px-2 py-0.5 rounded bg-gray-700/40 text-gray-400">Нужна генерация</span>;
  };

  // ─── Counters ──────────────────────────────────
  const charsReady = characters.filter((c) => c.baseImage).length;
  const locsReady = locations.filter((l) => l.baseImage).length;
  const locsWithAngles = locations.filter((l) => l.angles.length >= 15).length;

  const allRefsReady =
    characters.length > 0 &&
    locations.length > 0 &&
    characters.every((c) => c.status === 'ready') &&
    locations.every((l) => l.status === 'ready');

  // ─── Get review items for a specific item ─────
  const getBaseReviewItem = (type: 'characters' | 'locations', itemId: string): RefReviewItem | undefined => {
    return reviewItems.find((r) => r.type === type && r.itemId === itemId && r.target === 'base');
  };

  const getAngleReviewItems = (type: 'characters' | 'locations', itemId: string): RefReviewItem[] => {
    return reviewItems.filter((r) => r.type === type && r.itemId === itemId && r.target === 'angle');
  };

  // ─── Render review inline ─────────────────────
  const renderReviewInline = (item: RefReviewItem) => {
    const key = reviewKey(item);
    const lastAttempt = item.manifest.attempts[item.manifest.attempts.length - 1];
    if (!lastAttempt || lastAttempt.variants.length === 0) return null;

    const selected = selectedVariants[key] ?? null;
    const feedback = feedbackTexts[key] || '';

    // Already accepted
    if (item.manifest.status === 'accepted') {
      return (
        <div className="mt-2 p-2 bg-green-900/20 border border-green-800/30 rounded-lg">
          <div className="flex items-center gap-2 text-green-400 text-sm">
            <CheckCircle size={14} />
            Принято (вариант {(item.manifest.selected_variant?.variant ?? 0) + 1})
          </div>
        </div>
      );
    }

    // Still generating
    if (item.manifest.status === 'generating') {
      return (
        <div className="mt-2 p-2 bg-amber-900/10 border border-amber-800/20 rounded-lg">
          <div className="flex items-center gap-2 text-amber-400 text-sm">
            <Loader2 size={14} className="animate-spin" />
            Генерация...
          </div>
        </div>
      );
    }

    // Build variant objects for VariantGrid
    const variants = lastAttempt.variants.map((v, idx) => ({
      index: idx,
      src: api.mediaUrl(projectId, item.variantPaths[idx] || ''),
      isVideo: false,
    }));

    return (
      <div className="mt-3 space-y-3">
        {/* Feedback from previous rejection */}
        {item.manifest.feedback && (
          <div className="p-2 bg-amber-900/10 border border-amber-800/20 rounded text-xs text-amber-400">
            Предыдущий фидбек: {item.manifest.feedback}
          </div>
        )}

        {/* Variant grid */}
        <VariantGrid
          clipId={`${item.itemId}_${item.target === 'angle' ? item.angleId : 'base'}`}
          component={item.target === 'base' ? 'nb_first' : 'nb_first'}
          attemptNum={lastAttempt.attempt}
          variants={variants}
          selectedIndex={selected}
          onSelect={(idx) => handleSelectVariant(item, idx)}
        />

        {/* Action buttons */}
        <div className="flex items-start gap-3">
          {/* Accept */}
          <button
            onClick={() => handleAccept(item)}
            disabled={selected == null || submitting}
            className="flex items-center gap-1.5 px-4 py-2 bg-green-700 hover:bg-green-600 rounded-lg text-sm transition-colors disabled:opacity-40"
          >
            <CheckCircle size={14} />
            Принять
          </button>

          {/* Reject */}
          <div className="flex-1 flex gap-2">
            <input
              type="text"
              placeholder="Фидбек для отклонения..."
              value={feedback}
              onChange={(e) => setFeedbackTexts((prev) => ({ ...prev, [key]: e.target.value }))}
              className="flex-1 px-3 py-2 bg-surface-light rounded-lg border border-surface-lighter focus:border-accent outline-none text-sm"
            />
            <button
              onClick={() => handleReject(item)}
              disabled={!feedback.trim() || submitting}
              className="flex items-center gap-1.5 px-4 py-2 bg-red-800 hover:bg-red-700 rounded-lg text-sm transition-colors disabled:opacity-40"
            >
              <AlertCircle size={14} />
              Отклонить
            </button>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">

      {/* ─── All ready banner ─────────────────── */}
      {allRefsReady && (
        <div className="p-4 bg-green-900/20 border border-green-800/30 rounded-lg">
          <div className="flex items-center gap-3">
            <CheckCircle size={24} className="text-green-400" />
            <div>
              <p className="text-green-300 font-medium">Все референсы готовы</p>
              <p className="text-green-400/70 text-sm">
                {characters.length} персонажей и {locations.length} локаций с базовыми образами и ракурсами
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ─── Submit message ───────────────────── */}
      {submitMessage && (
        <div className={`p-3 rounded-lg text-sm ${
          submitMessage.includes('Ошибка')
            ? 'bg-red-900/20 border border-red-800/30 text-red-400'
            : 'bg-green-900/20 border border-green-800/30 text-green-400'
        }`}>
          {submitMessage}
          <button
            onClick={() => setSubmitMessage(null)}
            className="ml-2 text-gray-500 hover:text-white"
          >
            x
          </button>
        </div>
      )}

      {/* ─── Characters ──────────────────────── */}
      {characters.length === 0 && locations.length === 0 && (
        <div className="text-center py-8 border-2 border-dashed border-surface-lighter rounded-lg">
          <Users size={40} className="mx-auto text-gray-500 mb-3" />
          <h2 className="text-lg font-medium mb-2">Нет референсов</h2>
          <p className="text-gray-400 text-sm mb-4 max-w-md mx-auto">
            Загрузите all_prompts.json на шаге "Промпты" -- персонажи и локации будут извлечены автоматически из ингредиентов.
          </p>
          <p className="text-gray-500 text-xs">
            Или добавьте персонажей и локации вручную ниже.
          </p>
        </div>
      )}

      <div>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <User size={18} className="text-accent" />
                <h3 className="text-lg font-medium">Персонажи</h3>
                <span className="text-sm text-gray-500">
                  {charsReady}/{characters.length} с фото
                </span>
              </div>
              <button
                onClick={() => setShowAddChar(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-400 hover:text-white border border-surface-lighter hover:border-accent rounded-lg transition-colors"
              >
                <Plus size={14} />
                Добавить
              </button>
            </div>

            {/* Add character form */}
            {showAddChar && (
              <div className="mb-3 p-3 bg-surface rounded-lg border border-surface-lighter space-y-2">
                <div className="grid grid-cols-2 gap-2">
                  <input
                    placeholder="Имя"
                    value={charForm.name}
                    onChange={(e) => setCharForm({ ...charForm, name: e.target.value })}
                    className="px-3 py-1.5 bg-surface-light rounded border border-surface-lighter focus:border-accent outline-none text-sm"
                    autoFocus
                  />
                  <input
                    placeholder="Имя (рус.)"
                    value={charForm.nameRu}
                    onChange={(e) => setCharForm({ ...charForm, nameRu: e.target.value })}
                    className="px-3 py-1.5 bg-surface-light rounded border border-surface-lighter focus:border-accent outline-none text-sm"
                  />
                </div>
                <input
                  placeholder='Одежда (напр. "in the grey hoodie")'
                  value={charForm.clothing}
                  onChange={(e) => setCharForm({ ...charForm, clothing: e.target.value })}
                  className="w-full px-3 py-1.5 bg-surface-light rounded border border-surface-lighter focus:border-accent outline-none text-sm"
                />
                <div className="flex gap-2 justify-end">
                  <button onClick={() => setShowAddChar(false)} className="px-3 py-1.5 text-xs text-gray-400">Отмена</button>
                  <button onClick={handleAddCharacter} disabled={!charForm.name.trim()} className="px-3 py-1.5 bg-accent rounded text-xs disabled:opacity-40">Добавить</button>
                </div>
              </div>
            )}

            {/* Character list */}
            <div className="space-y-1.5">
              {characters.map((char) => {
                const isExpanded = expandedChar === char.id;
                const baseReview = getBaseReviewItem('characters', char.id);
                const angleReviews = getAngleReviewItems('characters', char.id);
                const genKeyBase = `characters:${char.id}:base`;
                const genKeyAngles = `characters:${char.id}:angles`;
                const hasReviewItems = baseReview || angleReviews.length > 0;

                return (
                  <div key={char.id} className="bg-surface rounded-lg border border-surface-lighter overflow-hidden">
                    <div
                      className="flex items-center gap-3 p-3 cursor-pointer hover:bg-surface-light/50 transition-colors"
                      onClick={() => setExpandedChar(isExpanded ? null : char.id)}
                    >
                      {/* Photo */}
                      {char.baseImage ? (
                        <img
                          src={api.mediaUrl(projectId, char.baseImage)}
                          alt={char.name}
                          className="w-12 h-12 rounded-lg object-cover flex-shrink-0"
                        />
                      ) : (
                        <label className="w-12 h-12 rounded-lg bg-surface-lighter flex items-center justify-center cursor-pointer hover:bg-gray-600 transition-colors flex-shrink-0"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <User size={18} className="text-gray-500" />
                          <input
                            type="file"
                            accept="image/*"
                            className="hidden"
                            onChange={(e) => {
                              const file = e.target.files?.[0];
                              if (file) handleCharacterImage(char.id, file);
                            }}
                          />
                        </label>
                      )}

                      {/* Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-sm">{char.nameRu || char.name}</span>
                          {char.clothing && (
                            <span className="text-xs text-amber-400/80">{char.clothing}</span>
                          )}
                        </div>
                        {char.description && (
                          <p className="text-xs text-gray-500 truncate">{char.description}</p>
                        )}
                      </div>

                      {/* Review indicator */}
                      {hasReviewItems && (
                        <span className="text-xs px-2 py-0.5 rounded bg-purple-900/40 text-purple-400">
                          Ревью
                        </span>
                      )}

                      {/* Status */}
                      {statusBadge(char.status, !!char.baseImage, char.angles.length)}

                      {/* Expand arrow */}
                      {isExpanded ? <ChevronDown size={14} className="text-gray-500" /> : <ChevronRight size={14} className="text-gray-500" />}

                      {/* Delete */}
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDeleteCharacter(char.id); }}
                        className="text-gray-600 hover:text-red-400 transition-colors"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>

                    {/* Expanded: generate + review */}
                    {isExpanded && (
                      <div className="px-3 pb-3 border-t border-surface-lighter space-y-3">
                        {/* Generate base button */}
                        {!char.baseImage && !baseReview && (
                          <div className="pt-3">
                            <button
                              onClick={(e) => { e.stopPropagation(); handleGenerate('characters', char.id, 'base'); }}
                              disabled={generating[genKeyBase]}
                              className="flex items-center gap-2 px-3 py-2 bg-accent hover:bg-accent-hover rounded-lg text-sm transition-colors disabled:opacity-40"
                            >
                              {generating[genKeyBase] ? <Loader2 size={14} className="animate-spin" /> : <Camera size={14} />}
                              Сгенерировать базовый образ
                            </button>
                            {genMessages[genKeyBase] && (
                              <p className="text-xs text-gray-400 mt-1">{genMessages[genKeyBase]}</p>
                            )}
                          </div>
                        )}

                        {/* Base review inline */}
                        {baseReview && baseReview.manifest.status !== 'accepted' && (
                          <div className="pt-3">
                            <h4 className="text-sm font-medium text-amber-400 mb-1">Базовый образ — ревью</h4>
                            {renderReviewInline(baseReview)}
                          </div>
                        )}

                        {/* Generate angles button */}
                        {char.baseImage && char.status !== 'ready' && (
                          <div className="pt-2">
                            <button
                              onClick={(e) => { e.stopPropagation(); handleGenerate('characters', char.id, 'angles'); }}
                              disabled={generating[genKeyAngles]}
                              className="flex items-center gap-2 px-3 py-2 bg-blue-700 hover:bg-blue-600 rounded-lg text-sm transition-colors disabled:opacity-40"
                            >
                              {generating[genKeyAngles] ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
                              Сгенерировать ракурсы
                            </button>
                            {genMessages[genKeyAngles] && (
                              <p className="text-xs text-gray-400 mt-1">{genMessages[genKeyAngles]}</p>
                            )}
                          </div>
                        )}

                        {/* Angle reviews */}
                        {angleReviews.length > 0 && (
                          <div className="pt-2 space-y-3">
                            <h4 className="text-sm font-medium text-blue-400">Ракурсы — ревью</h4>
                            {angleReviews.map((angleItem) => (
                              <div key={angleItem.angleId} className="bg-surface-light rounded-lg p-3">
                                <p className="text-xs text-gray-400 mb-1">
                                  {angleItem.angleDescription || angleItem.angleId}
                                </p>
                                {renderReviewInline(angleItem)}
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Accepted angles grid */}
                        {char.angles.length > 0 && (
                          <div className="pt-2">
                            <h4 className="text-sm text-gray-400 mb-2">
                              Принятые ракурсы ({char.angles.filter((a) => a.status === 'accepted').length})
                            </h4>
                            <div className="grid grid-cols-5 gap-2">
                              {char.angles.filter((a) => a.status === 'accepted').map((angle) => (
                                <div key={angle.id} className="text-center">
                                  <img
                                    src={api.mediaUrl(projectId, angle.file)}
                                    alt={angle.description}
                                    className="w-full aspect-square rounded object-cover border border-surface-lighter"
                                    loading="lazy"
                                  />
                                  <span className="text-[10px] text-gray-500 mt-0.5 block truncate">
                                    {angle.description}
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {!char.baseImage && !baseReview && !generating[genKeyBase] && (
                          <p className="text-sm text-gray-500 pt-3">
                            Загрузите фото или сгенерируйте базовый образ.
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
              {characters.length === 0 && (
                <p className="text-gray-500 text-sm py-3 text-center">Нет персонажей</p>
              )}
            </div>
          </div>

          {/* ─── Locations ────────────────────── */}
          <div className="border-t border-surface-lighter pt-6">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <MapPin size={18} className="text-accent" />
                <h3 className="text-lg font-medium">Локации</h3>
                <span className="text-sm text-gray-500">
                  {locsReady}/{locations.length} с фото, {locsWithAngles} с ракурсами
                </span>
              </div>
              <button
                onClick={() => setShowAddLoc(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-400 hover:text-white border border-surface-lighter hover:border-accent rounded-lg transition-colors"
              >
                <Plus size={14} />
                Добавить
              </button>
            </div>

            {/* Add location form */}
            {showAddLoc && (
              <div className="mb-3 p-3 bg-surface rounded-lg border border-surface-lighter space-y-2">
                <div className="grid grid-cols-2 gap-2">
                  <input
                    placeholder="Название"
                    value={locForm.name}
                    onChange={(e) => setLocForm({ ...locForm, name: e.target.value })}
                    className="px-3 py-1.5 bg-surface-light rounded border border-surface-lighter focus:border-accent outline-none text-sm"
                    autoFocus
                  />
                  <input
                    placeholder="Название (рус.)"
                    value={locForm.nameRu}
                    onChange={(e) => setLocForm({ ...locForm, nameRu: e.target.value })}
                    className="px-3 py-1.5 bg-surface-light rounded border border-surface-lighter focus:border-accent outline-none text-sm"
                  />
                </div>
                <input
                  placeholder="Описание локации"
                  value={locForm.description}
                  onChange={(e) => setLocForm({ ...locForm, description: e.target.value })}
                  className="w-full px-3 py-1.5 bg-surface-light rounded border border-surface-lighter focus:border-accent outline-none text-sm"
                />
                <div className="flex gap-2 justify-end">
                  <button onClick={() => setShowAddLoc(false)} className="px-3 py-1.5 text-xs text-gray-400">Отмена</button>
                  <button onClick={handleAddLocation} disabled={!locForm.name.trim()} className="px-3 py-1.5 bg-accent rounded text-xs disabled:opacity-40">Добавить</button>
                </div>
              </div>
            )}

            {/* Location list */}
            <div className="space-y-1.5">
              {locations.map((loc) => {
                const isExpanded = expandedLoc === loc.id;
                const baseReview = getBaseReviewItem('locations', loc.id);
                const angleReviews = getAngleReviewItems('locations', loc.id);
                const genKeyBase = `locations:${loc.id}:base`;
                const genKeyAngles = `locations:${loc.id}:angles`;
                const hasReviewItems = baseReview || angleReviews.length > 0;

                return (
                  <div key={loc.id} className="bg-surface rounded-lg border border-surface-lighter overflow-hidden">
                    <div
                      className="flex items-center gap-3 p-3 cursor-pointer hover:bg-surface-light/50 transition-colors"
                      onClick={() => setExpandedLoc(isExpanded ? null : loc.id)}
                    >
                      {/* Photo */}
                      {loc.baseImage ? (
                        <img
                          src={api.mediaUrl(projectId, loc.baseImage)}
                          alt={loc.name}
                          className="w-16 h-12 rounded object-cover flex-shrink-0"
                        />
                      ) : (
                        <div className="w-16 h-12 rounded bg-surface-lighter flex items-center justify-center flex-shrink-0">
                          <MapPin size={18} className="text-gray-500" />
                        </div>
                      )}

                      {/* Info */}
                      <div className="flex-1 min-w-0">
                        <span className="font-medium text-sm">{loc.nameRu || loc.name}</span>
                        {loc.description && (
                          <p className="text-xs text-gray-500 truncate">{loc.description}</p>
                        )}
                      </div>

                      {/* Angles count */}
                      <div className="flex items-center gap-1 text-xs text-gray-500">
                        <Image size={12} />
                        {loc.angles.length}/15+
                      </div>

                      {/* Review indicator */}
                      {hasReviewItems && (
                        <span className="text-xs px-2 py-0.5 rounded bg-purple-900/40 text-purple-400">
                          Ревью
                        </span>
                      )}

                      {/* Status */}
                      {statusBadge(loc.status, !!loc.baseImage, loc.angles.length)}

                      {/* Expand arrow */}
                      {isExpanded ? <ChevronDown size={14} className="text-gray-500" /> : <ChevronRight size={14} className="text-gray-500" />}

                      {/* Delete */}
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDeleteLocation(loc.id); }}
                        className="text-gray-600 hover:text-red-400 transition-colors"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>

                    {/* Expanded: generate + review */}
                    {isExpanded && (
                      <div className="px-3 pb-3 border-t border-surface-lighter space-y-3">
                        {/* Generate base button */}
                        {!loc.baseImage && !baseReview && (
                          <div className="pt-3">
                            <button
                              onClick={(e) => { e.stopPropagation(); handleGenerate('locations', loc.id, 'base'); }}
                              disabled={generating[genKeyBase]}
                              className="flex items-center gap-2 px-3 py-2 bg-accent hover:bg-accent-hover rounded-lg text-sm transition-colors disabled:opacity-40"
                            >
                              {generating[genKeyBase] ? <Loader2 size={14} className="animate-spin" /> : <Camera size={14} />}
                              Сгенерировать базовый образ
                            </button>
                            {genMessages[genKeyBase] && (
                              <p className="text-xs text-gray-400 mt-1">{genMessages[genKeyBase]}</p>
                            )}
                          </div>
                        )}

                        {/* Base review inline */}
                        {baseReview && baseReview.manifest.status !== 'accepted' && (
                          <div className="pt-3">
                            <h4 className="text-sm font-medium text-amber-400 mb-1">Базовый образ — ревью</h4>
                            {renderReviewInline(baseReview)}
                          </div>
                        )}

                        {/* Generate angles button */}
                        {loc.baseImage && loc.status !== 'ready' && (
                          <div className="pt-2">
                            <button
                              onClick={(e) => { e.stopPropagation(); handleGenerate('locations', loc.id, 'angles'); }}
                              disabled={generating[genKeyAngles]}
                              className="flex items-center gap-2 px-3 py-2 bg-blue-700 hover:bg-blue-600 rounded-lg text-sm transition-colors disabled:opacity-40"
                            >
                              {generating[genKeyAngles] ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
                              Сгенерировать ракурсы ({loc.angles.filter((a) => a.status === 'accepted').length}/15+)
                            </button>
                            {genMessages[genKeyAngles] && (
                              <p className="text-xs text-gray-400 mt-1">{genMessages[genKeyAngles]}</p>
                            )}
                          </div>
                        )}

                        {/* Angle reviews */}
                        {angleReviews.length > 0 && (
                          <div className="pt-2 space-y-3">
                            <h4 className="text-sm font-medium text-blue-400">Ракурсы — ревью</h4>
                            {angleReviews.map((angleItem) => (
                              <div key={angleItem.angleId} className="bg-surface-light rounded-lg p-3">
                                <p className="text-xs text-gray-400 mb-1">
                                  {angleItem.angleDescription || angleItem.angleId}
                                </p>
                                {renderReviewInline(angleItem)}
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Accepted angles grid */}
                        {loc.angles.length > 0 && (
                          <div className="pt-2">
                            <h4 className="text-sm text-gray-400 mb-2">
                              Принятые ракурсы ({loc.angles.filter((a) => a.status === 'accepted').length}/15+)
                            </h4>
                            <div className="grid grid-cols-5 gap-2">
                              {loc.angles.filter((a) => a.status === 'accepted').map((angle) => (
                                <div key={angle.id} className="text-center">
                                  <img
                                    src={api.mediaUrl(projectId, angle.file)}
                                    alt={angle.description}
                                    className="w-full aspect-video rounded object-cover border border-surface-lighter"
                                    loading="lazy"
                                  />
                                  <span className="text-[10px] text-gray-500 mt-0.5 block truncate">
                                    {angle.description}
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {!loc.baseImage && !baseReview && !generating[genKeyBase] && (
                          <p className="text-sm text-gray-500 pt-3">
                            Загрузите фото или сгенерируйте базовый образ.
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
              {locations.length === 0 && (
                <p className="text-gray-500 text-sm py-3 text-center">Нет локаций</p>
              )}
            </div>
          </div>

          {/* ─── Промпты и генерация ──────── */}
          {(characters.some((c) => !c.baseImage) || locations.some((l) => !l.baseImage) ||
            characters.some((c) => c.baseImage && c.status !== 'ready') ||
            locations.some((l) => l.baseImage && l.status !== 'ready')) && (
            <div className="border-t border-surface-lighter pt-4 space-y-3">
              {/* Создание промптов */}
              {(characters.some((c) => !c.baseImage) || locations.some((l) => !l.baseImage) ||
                characters.some((c) => c.baseImage && c.status !== 'ready') ||
                locations.some((l) => l.baseImage && l.status !== 'ready')) && (
                <div className="flex items-center justify-between p-4 bg-amber-900/10 border border-amber-800/20 rounded-lg">
                  <div>
                    <p className="text-sm text-amber-300">
                      Не хватает референсов: {characters.filter((c) => !c.baseImage).length} персонажей,{' '}
                      {locations.filter((l) => !l.baseImage).length} локаций
                      {(characters.some((c) => c.baseImage && c.angles.length < 5) || locations.some((l) => l.baseImage && l.angles.length < 15)) && (
                        <>, нужны ракурсы</>
                      )}
                    </p>
                    {Object.values(generating).some(Boolean) && (
                      <p className="text-xs text-amber-400 mt-1 flex items-center gap-1.5">
                        <Loader2 size={12} className="animate-spin" />
                        Идёт создание промптов...
                      </p>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <button
                      className="flex items-center gap-2 px-4 py-2 bg-accent hover:bg-accent-hover rounded-lg text-sm transition-colors disabled:opacity-40"
                      onClick={handleGenerateAllMissing}
                      disabled={Object.values(generating).some(Boolean)}
                    >
                      {Object.values(generating).some(Boolean) ? (
                        <Loader2 size={14} className="animate-spin" />
                      ) : (
                        <Sparkles size={14} />
                      )}
                      Создать промпты
                    </button>
                  </div>
                </div>
              )}

              {/* Запуск генерации */}
              <div className="flex items-center justify-between p-4 bg-surface rounded-lg border border-surface-lighter">
                <div>
                  <p className="text-sm text-gray-300">Запуск генерации референсов</p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    Бот сгенерирует варианты по созданным промптам
                  </p>
                </div>
                <button
                  className="flex items-center gap-2 px-4 py-2 bg-green-700 hover:bg-green-600 rounded-lg text-sm transition-colors disabled:opacity-40"
                  disabled={Object.values(generating).some(Boolean)}
                  onClick={() => {
                    // TODO: запуск бота для генерации референсов
                    alert('Бот для генерации референсов будет подключён');
                  }}
                >
                  {Object.values(generating).some(Boolean) ? (
                    <>
                      <Loader2 size={14} className="animate-spin" />
                      Идёт создание промптов...
                    </>
                  ) : (
                    <>
                      <Camera size={14} />
                      Запустить генерацию
                    </>
                  )}
                </button>
              </div>
            </div>
          )}
    </div>
  );
}
