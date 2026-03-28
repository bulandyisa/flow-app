import { useState, useMemo, useCallback, useRef, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';
import {
  Film,
  Plus,
  X,
  Play,
  Pause,
  Download,
  Loader2,
  AlertTriangle,
  GripVertical,
  Scissors,
  Trash2,
  ChevronRight,
  ChevronDown,
  Clock,
  Package,
  Check,
} from 'lucide-react';

// ─── Типы ───────────────────────────────────────────────

interface LibraryClip {
  clipId: string;
  sceneId: string;
  filename: string;
  filePath: string;
  duration: number | null;
  thumbnail: string | null;
  descriptionRu: string;
}

interface TimelineItem {
  id: string; // уникальный ID для drag & drop
  clipId: string;
  filePath: string;
  duration: number;
  startSec: number;
  endSec: number;
  thumbnail: string | null;
}

interface ExportInfo {
  name: string;
  filename: string;
  path: string;
  size: number;
  duration: number | null;
  clipCount: number;
  createdAt: string;
}

// ─── Утилиты ────────────────────────────────────────────

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

let nextId = 1;
function genId(): string {
  return `tl_${nextId++}_${Date.now()}`;
}

// ─── Основной компонент ─────────────────────────────────

export function Assembly() {
  const { id: projectId } = useParams<{ id: string }>();

  // Загрузка данных
  const { data: clipsData, isLoading: clipsLoading } = useQuery({
    queryKey: ['assembly-clips', projectId],
    queryFn: () => api.getAssemblyClips(projectId!),
    enabled: !!projectId,
  });

  const { data: exportsData, refetch: refetchExports } = useQuery({
    queryKey: ['assembly-exports', projectId],
    queryFn: () => api.getAssemblyExports(projectId!),
    enabled: !!projectId,
  });

  const { data: ffmpegStatus } = useQuery({
    queryKey: ['ffmpeg-status', projectId],
    queryFn: () => api.getFFmpegStatus(projectId!),
    enabled: !!projectId,
  });

  // Состояние
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const [selectedTimelineIdx, setSelectedTimelineIdx] = useState<number | null>(null);
  const [previewClipPath, setPreviewClipPath] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [exportName, setExportName] = useState('');
  const [collapsedScenes, setCollapsedScenes] = useState<Set<string>>(new Set());
  const [dragIdx, setDragIdx] = useState<number | null>(null);
  const [dragOverIdx, setDragOverIdx] = useState<number | null>(null);

  const videoRef = useRef<HTMLVideoElement>(null);

  const libraryClips = clipsData?.clips || [];
  const exports = exportsData?.exports || [];

  // Группировка клипов по сценам
  const sceneGroups = useMemo(() => {
    const groups = new Map<string, LibraryClip[]>();
    for (const clip of libraryClips) {
      if (!groups.has(clip.sceneId)) {
        groups.set(clip.sceneId, []);
      }
      groups.get(clip.sceneId)!.push(clip);
    }
    return groups;
  }, [libraryClips]);

  // ID клипов на таймлайне
  const timelineClipIds = useMemo(() => new Set(timeline.map((t) => t.clipId)), [timeline]);

  // Общая длительность таймлайна
  const totalDuration = useMemo(
    () => timeline.reduce((sum, item) => sum + (item.endSec - item.startSec), 0),
    [timeline],
  );

  // ─── Действия ──────────────────────────────────────────

  const addToTimeline = useCallback(
    (clip: LibraryClip) => {
      if (timelineClipIds.has(clip.clipId)) return;
      const duration = clip.duration || 8; // По умолчанию 8 сек
      setTimeline((prev) => [
        ...prev,
        {
          id: genId(),
          clipId: clip.clipId,
          filePath: clip.filePath,
          duration,
          startSec: 0,
          endSec: duration,
          thumbnail: clip.thumbnail,
        },
      ]);
    },
    [timelineClipIds],
  );

  const addAllClips = useCallback(() => {
    const newItems: TimelineItem[] = [];
    for (const clip of libraryClips) {
      if (timelineClipIds.has(clip.clipId)) continue;
      const duration = clip.duration || 8;
      newItems.push({
        id: genId(),
        clipId: clip.clipId,
        filePath: clip.filePath,
        duration,
        startSec: 0,
        endSec: duration,
        thumbnail: clip.thumbnail,
      });
    }
    setTimeline((prev) => [...prev, ...newItems]);
  }, [libraryClips, timelineClipIds]);

  const removeFromTimeline = useCallback(
    (idx: number) => {
      setTimeline((prev) => prev.filter((_, i) => i !== idx));
      if (selectedTimelineIdx === idx) {
        setSelectedTimelineIdx(null);
      } else if (selectedTimelineIdx !== null && selectedTimelineIdx > idx) {
        setSelectedTimelineIdx(selectedTimelineIdx - 1);
      }
    },
    [selectedTimelineIdx],
  );

  const clearTimeline = useCallback(() => {
    setTimeline([]);
    setSelectedTimelineIdx(null);
  }, []);

  const selectTimelineItem = useCallback(
    (idx: number) => {
      setSelectedTimelineIdx(idx);
      const item = timeline[idx];
      if (item && projectId) {
        setPreviewClipPath(api.mediaUrl(projectId, item.filePath));
      }
    },
    [timeline, projectId],
  );

  const previewLibraryClip = useCallback(
    (clip: LibraryClip) => {
      if (!projectId) return;
      setPreviewClipPath(api.mediaUrl(projectId, clip.filePath));
      setSelectedTimelineIdx(null);
    },
    [projectId],
  );

  const updateTrimStart = useCallback(
    (value: number) => {
      if (selectedTimelineIdx === null) return;
      setTimeline((prev) => {
        const updated = [...prev];
        const item = { ...updated[selectedTimelineIdx] };
        item.startSec = Math.min(value, item.endSec - 0.1);
        updated[selectedTimelineIdx] = item;
        return updated;
      });
    },
    [selectedTimelineIdx],
  );

  const updateTrimEnd = useCallback(
    (value: number) => {
      if (selectedTimelineIdx === null) return;
      setTimeline((prev) => {
        const updated = [...prev];
        const item = { ...updated[selectedTimelineIdx] };
        item.endSec = Math.max(value, item.startSec + 0.1);
        updated[selectedTimelineIdx] = item;
        return updated;
      });
    },
    [selectedTimelineIdx],
  );

  // Drag & drop на таймлайне
  const handleDragStart = useCallback((idx: number) => {
    setDragIdx(idx);
  }, []);

  const handleDragOver = useCallback(
    (e: React.DragEvent, idx: number) => {
      e.preventDefault();
      if (dragIdx === null || dragIdx === idx) return;
      setDragOverIdx(idx);
    },
    [dragIdx],
  );

  const handleDrop = useCallback(
    (idx: number) => {
      if (dragIdx === null || dragIdx === idx) {
        setDragIdx(null);
        setDragOverIdx(null);
        return;
      }
      setTimeline((prev) => {
        const updated = [...prev];
        const [moved] = updated.splice(dragIdx, 1);
        updated.splice(idx, 0, moved);
        return updated;
      });
      // Обновляем выделение
      if (selectedTimelineIdx === dragIdx) {
        setSelectedTimelineIdx(idx);
      } else if (selectedTimelineIdx !== null) {
        // Пересчитываем индекс выделенного
        let newIdx = selectedTimelineIdx;
        if (dragIdx < selectedTimelineIdx && idx >= selectedTimelineIdx) {
          newIdx--;
        } else if (dragIdx > selectedTimelineIdx && idx <= selectedTimelineIdx) {
          newIdx++;
        }
        setSelectedTimelineIdx(newIdx);
      }
      setDragIdx(null);
      setDragOverIdx(null);
    },
    [dragIdx, selectedTimelineIdx],
  );

  const handleDragEnd = useCallback(() => {
    setDragIdx(null);
    setDragOverIdx(null);
  }, []);

  const toggleScene = useCallback((sceneId: string) => {
    setCollapsedScenes((prev) => {
      const next = new Set(prev);
      if (next.has(sceneId)) {
        next.delete(sceneId);
      } else {
        next.add(sceneId);
      }
      return next;
    });
  }, []);

  // Экспорт → сразу скачивание
  const handleExport = useCallback(async () => {
    if (!projectId || timeline.length === 0) return;
    setIsExporting(true);
    setExportError(null);

    try {
      const timelineData = timeline.map((item) => ({
        filePath: item.filePath,
        startSec: item.startSec,
        endSec: item.endSec,
      }));

      const result = await api.exportAssembly(projectId, timelineData, exportName || undefined) as { exportPath?: string; fileName?: string };

      // Скачиваем файл сразу
      if (result.exportPath) {
        const downloadUrl = api.mediaUrl(projectId, result.exportPath);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = result.fileName || 'export.mp4';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      }

      setExportName('');
    } catch (err) {
      setExportError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsExporting(false);
    }
  }, [projectId, timeline, exportName]);

  // Видео-плеер
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const onPlay = () => setIsPlaying(true);
    const onPause = () => setIsPlaying(false);
    const onEnded = () => setIsPlaying(false);

    video.addEventListener('play', onPlay);
    video.addEventListener('pause', onPause);
    video.addEventListener('ended', onEnded);

    return () => {
      video.removeEventListener('play', onPlay);
      video.removeEventListener('pause', onPause);
      video.removeEventListener('ended', onEnded);
    };
  }, [previewClipPath]);

  // При смене selected clip на timeline — подгружаем trim в плеер
  useEffect(() => {
    const video = videoRef.current;
    if (!video || selectedTimelineIdx === null) return;
    const item = timeline[selectedTimelineIdx];
    if (!item) return;
    video.currentTime = item.startSec;
  }, [selectedTimelineIdx, timeline]);

  const togglePlayPause = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;
    if (video.paused) {
      video.play();
    } else {
      video.pause();
    }
  }, []);

  // ─── Рендер ─────────────────────────────────────────────

  if (clipsLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="animate-spin text-gray-400" size={32} />
        <span className="ml-3 text-gray-400">Загрузка клипов...</span>
      </div>
    );
  }

  const selectedItem = selectedTimelineIdx !== null ? timeline[selectedTimelineIdx] : null;

  return (
    <div className="flex flex-col h-full -m-6">
      {/* Верхняя часть: превью + библиотека */}
      <div className="flex flex-1 min-h-0">
        {/* Библиотека (левая панель) */}
        <div className="w-72 border-r border-surface-lighter flex flex-col bg-surface">
          <div className="px-4 py-3 border-b border-surface-lighter flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
              Библиотека
            </h2>
            <span className="text-xs text-gray-500">{libraryClips.length} клипов</span>
          </div>

          {libraryClips.length === 0 ? (
            <div className="flex-1 flex items-center justify-center p-4">
              <div className="text-center text-gray-500">
                <Film size={32} className="mx-auto mb-2 opacity-50" />
                <p className="text-sm">Нет принятых видео</p>
                <p className="text-xs mt-1">Примите VEO-видео в разделе Производство</p>
              </div>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto">
              {/* Кнопка "Добавить все" */}
              <div className="px-3 py-2 border-b border-surface-lighter">
                <button
                  onClick={addAllClips}
                  className="w-full px-3 py-1.5 text-xs bg-accent/20 text-accent hover:bg-accent/30 rounded transition-colors"
                >
                  Добавить все на таймлайн
                </button>
              </div>

              {Array.from(sceneGroups.entries()).map(([sceneId, clips]) => (
                <div key={sceneId} className="border-b border-surface-lighter/50">
                  {/* Заголовок сцены */}
                  <button
                    onClick={() => toggleScene(sceneId)}
                    className="w-full flex items-center gap-2 px-3 py-2 text-xs font-medium text-gray-400 hover:text-gray-300 hover:bg-surface-light transition-colors"
                  >
                    {collapsedScenes.has(sceneId) ? (
                      <ChevronRight size={14} />
                    ) : (
                      <ChevronDown size={14} />
                    )}
                    <span>{sceneId}</span>
                    <span className="text-gray-600 ml-auto">{clips.length}</span>
                  </button>

                  {/* Клипы сцены */}
                  {!collapsedScenes.has(sceneId) &&
                    clips.map((clip) => {
                      const onTimeline = timelineClipIds.has(clip.clipId);
                      return (
                        <div
                          key={clip.clipId}
                          className={`flex items-center gap-2 px-3 py-1.5 mx-1 rounded cursor-pointer transition-colors ${
                            onTimeline
                              ? 'opacity-40 bg-surface-lighter/30'
                              : 'hover:bg-surface-light'
                          }`}
                          onClick={() => previewLibraryClip(clip)}
                        >
                          {/* Миниатюра */}
                          <div className="w-12 h-8 rounded bg-surface-lighter flex-shrink-0 overflow-hidden flex items-center justify-center">
                            {clip.thumbnail && projectId ? (
                              <img
                                src={api.mediaUrl(projectId, clip.thumbnail)}
                                alt={clip.clipId}
                                className="w-full h-full object-cover"
                              />
                            ) : (
                              <Film size={14} className="text-gray-600" />
                            )}
                          </div>

                          {/* Инфо */}
                          <div className="flex-1 min-w-0">
                            <div className="text-xs text-gray-300 truncate">{clip.clipId}</div>
                            {clip.duration !== null && (
                              <div className="text-[10px] text-gray-500">
                                {formatDuration(clip.duration)}
                              </div>
                            )}
                          </div>

                          {/* Кнопка добавить */}
                          {!onTimeline && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                addToTimeline(clip);
                              }}
                              className="p-1 text-gray-500 hover:text-accent transition-colors"
                              title="Добавить на таймлайн"
                            >
                              <Plus size={14} />
                            </button>
                          )}
                          {onTimeline && (
                            <Check size={14} className="text-green-500/50 flex-shrink-0" />
                          )}
                        </div>
                      );
                    })}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Центральная часть: плеер + инфо */}
        <div className="flex-1 flex flex-col bg-surface">
          {/* Плеер */}
          <div className="flex-1 flex items-center justify-center bg-black/30 min-h-0">
            {previewClipPath ? (
              <div className="relative w-full h-full flex items-center justify-center">
                <video
                  ref={videoRef}
                  key={previewClipPath}
                  src={previewClipPath}
                  className="max-w-full max-h-full"
                  controls={false}
                  onClick={togglePlayPause}
                />

                {/* Оверлей управления */}
                <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-3 bg-black/60 backdrop-blur rounded-full px-4 py-2">
                  <button onClick={togglePlayPause} className="text-white hover:text-accent transition-colors">
                    {isPlaying ? <Pause size={20} /> : <Play size={20} />}
                  </button>
                  {selectedItem && (
                    <span className="text-xs text-gray-300">
                      {selectedItem.clipId} | {formatDuration(selectedItem.startSec)} - {formatDuration(selectedItem.endSec)}
                    </span>
                  )}
                </div>
              </div>
            ) : (
              <div className="text-center text-gray-500">
                <Film size={48} className="mx-auto mb-3 opacity-30" />
                <p className="text-sm">Выберите клип для предпросмотра</p>
              </div>
            )}
          </div>

          {/* Trim-контролы (показываем когда выбран клип на таймлайне) */}
          {selectedItem && (
            <div className="px-4 py-3 bg-surface-light border-t border-surface-lighter">
              <div className="flex items-center gap-4">
                <Scissors size={16} className="text-gray-400 flex-shrink-0" />
                <div className="flex-1 space-y-2">
                  <div className="flex items-center gap-3">
                    <label className="text-xs text-gray-400 w-16">Начало:</label>
                    <input
                      type="range"
                      min={0}
                      max={selectedItem.duration}
                      step={0.1}
                      value={selectedItem.startSec}
                      onChange={(e) => updateTrimStart(parseFloat(e.target.value))}
                      className="flex-1 accent-accent h-1"
                    />
                    <span className="text-xs text-gray-300 w-12 text-right">
                      {selectedItem.startSec.toFixed(1)}с
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <label className="text-xs text-gray-400 w-16">Конец:</label>
                    <input
                      type="range"
                      min={0}
                      max={selectedItem.duration}
                      step={0.1}
                      value={selectedItem.endSec}
                      onChange={(e) => updateTrimEnd(parseFloat(e.target.value))}
                      className="flex-1 accent-accent h-1"
                    />
                    <span className="text-xs text-gray-300 w-12 text-right">
                      {selectedItem.endSec.toFixed(1)}с
                    </span>
                  </div>
                </div>
                <div className="text-xs text-gray-400 text-right w-24">
                  <div>{formatDuration(selectedItem.endSec - selectedItem.startSec)}</div>
                  <div className="text-gray-600">из {formatDuration(selectedItem.duration)}</div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Нижняя часть: Таймлайн */}
      <div className="border-t border-surface-lighter bg-surface-light">
        {/* Заголовок таймлайна */}
        <div className="flex items-center gap-4 px-4 py-2 border-b border-surface-lighter">
          <h3 className="text-sm font-semibold text-gray-300">Таймлайн</h3>
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <Clock size={12} />
            <span>{timeline.length} клипов</span>
            <span className="text-gray-600">|</span>
            <span>{formatDuration(totalDuration)}</span>
          </div>

          <div className="ml-auto flex items-center gap-2">
            {timeline.length > 0 && (
              <button
                onClick={clearTimeline}
                className="px-2 py-1 text-xs text-gray-400 hover:text-red-400 transition-colors"
                title="Очистить таймлайн"
              >
                <Trash2 size={14} />
              </button>
            )}

            {/* FFmpeg статус */}
            {ffmpegStatus && !ffmpegStatus.available && (
              <div className="flex items-center gap-1 text-xs text-yellow-500" title={ffmpegStatus.error}>
                <AlertTriangle size={12} />
                <span>FFmpeg не найден</span>
              </div>
            )}

            {/* Экспорт */}
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={exportName}
                onChange={(e) => setExportName(e.target.value)}
                placeholder="Название..."
                className="px-2 py-1 text-xs bg-surface border border-surface-lighter rounded text-gray-300 placeholder-gray-600 w-32"
              />
              <button
                onClick={handleExport}
                disabled={isExporting || timeline.length === 0 || (ffmpegStatus && !ffmpegStatus.available)}
                className="flex items-center gap-1 px-3 py-1.5 text-xs bg-accent text-white rounded hover:bg-accent/80 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                {isExporting ? (
                  <>
                    <Loader2 size={12} className="animate-spin" />
                    <span>Экспорт...</span>
                  </>
                ) : (
                  <>
                    <Package size={12} />
                    <span>Экспорт</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {exportError && (
          <div className="px-4 py-2 bg-red-500/10 border-b border-red-500/20">
            <p className="text-xs text-red-400">{exportError}</p>
          </div>
        )}

        {/* Полоса таймлайна */}
        <div className="h-28 overflow-x-auto overflow-y-hidden">
          {timeline.length === 0 ? (
            <div className="flex items-center justify-center h-full text-gray-600">
              <p className="text-sm">Перетащите клипы из библиотеки или нажмите +</p>
            </div>
          ) : (
            <div className="flex items-stretch h-full p-2 gap-1 min-w-max">
              {timeline.map((item, idx) => {
                const trimmedDuration = item.endSec - item.startSec;
                // Ширина пропорциональна длительности (минимум 80px, максимум 300px)
                const width = Math.max(80, Math.min(300, trimmedDuration * 30));
                const isSelected = selectedTimelineIdx === idx;
                const isDragging = dragIdx === idx;
                const isDragOver = dragOverIdx === idx;

                return (
                  <div
                    key={item.id}
                    draggable
                    onDragStart={() => handleDragStart(idx)}
                    onDragOver={(e) => handleDragOver(e, idx)}
                    onDrop={() => handleDrop(idx)}
                    onDragEnd={handleDragEnd}
                    onClick={() => selectTimelineItem(idx)}
                    className={`relative flex-shrink-0 rounded-lg border-2 cursor-pointer transition-all group ${
                      isSelected
                        ? 'border-accent bg-accent/10'
                        : isDragOver
                          ? 'border-accent/50 bg-accent/5'
                          : 'border-surface-lighter bg-surface hover:border-gray-600'
                    } ${isDragging ? 'opacity-40' : ''}`}
                    style={{ width: `${width}px` }}
                  >
                    {/* Содержимое блока */}
                    <div className="flex flex-col h-full p-1.5">
                      {/* Drag handle + ID */}
                      <div className="flex items-center gap-1 mb-1">
                        <GripVertical size={10} className="text-gray-600 cursor-grab flex-shrink-0" />
                        <span className="text-[10px] font-medium text-gray-300 truncate">
                          {item.clipId}
                        </span>
                      </div>

                      {/* Визуальный блок (цветная полоска) */}
                      <div className="flex-1 rounded bg-gradient-to-r from-accent/30 to-accent/10 relative overflow-hidden">
                        {/* Визуальное отображение обрезки */}
                        {(item.startSec > 0 || item.endSec < item.duration) && (
                          <>
                            {item.startSec > 0 && (
                              <div
                                className="absolute left-0 top-0 bottom-0 bg-black/40"
                                style={{ width: `${(item.startSec / item.duration) * 100}%` }}
                              />
                            )}
                            {item.endSec < item.duration && (
                              <div
                                className="absolute right-0 top-0 bottom-0 bg-black/40"
                                style={{ width: `${((item.duration - item.endSec) / item.duration) * 100}%` }}
                              />
                            )}
                          </>
                        )}

                        {/* Миниатюра */}
                        {item.thumbnail && projectId && (
                          <img
                            src={api.mediaUrl(projectId, item.thumbnail)}
                            alt={item.clipId}
                            className="absolute inset-0 w-full h-full object-cover opacity-30"
                          />
                        )}
                      </div>

                      {/* Длительность */}
                      <div className="flex items-center justify-between mt-1">
                        <span className="text-[10px] text-gray-500">
                          {formatDuration(trimmedDuration)}
                        </span>
                        {(item.startSec > 0 || item.endSec < item.duration) && (
                          <Scissors size={8} className="text-yellow-500/50" />
                        )}
                      </div>
                    </div>

                    {/* Кнопка удаления */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        removeFromTimeline(idx);
                      }}
                      className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <X size={10} className="text-white" />
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
