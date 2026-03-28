import { Router } from 'express';
import { existsSync, readdirSync, statSync, readFileSync } from 'node:fs';
import { resolve, extname, basename } from 'node:path';
import type { AppConfig } from '../config.js';
import { ProjectStore } from '../data/project-store.js';
import { projectPaths, ensureDir } from '../data/file-manager.js';
import { findFFmpeg, getVideoDuration, exportVideo } from '../ffmpeg/runner.js';
import type { TimelineClip } from '../ffmpeg/runner.js';

/** Информация о клипе в библиотеке */
interface LibraryClip {
  clipId: string;
  sceneId: string;
  filename: string;
  filePath: string;
  duration: number | null;
  thumbnail: string | null;
  descriptionRu: string;
}

/** Информация об экспортированном видео */
interface ExportInfo {
  name: string;
  filename: string;
  path: string;
  size: number;
  duration: number | null;
  clipCount: number;
  createdAt: string;
}

export function assemblyRouter(config: AppConfig): Router {
  const router = Router();
  const store = new ProjectStore(config.dataDir);

  // GET /api/assembly/:projectId/clips — все принятые видеоклипы
  router.get('/:projectId/clips', async (req, res) => {
    const project = store.get(req.params.projectId);
    if (!project) {
      res.status(404).json({ error: 'Проект не найден' });
      return;
    }

    const paths = projectPaths(config.dataDir, project.id);
    const clipsDir = paths.clips;
    const reviewDir = paths.review;

    // Собираем все видеоклипы из clips/ директории
    const clips: LibraryClip[] = [];

    // Ищем .mp4 файлы в clips/
    if (existsSync(clipsDir)) {
      const files = readdirSync(clipsDir).filter((f) =>
        ['.mp4', '.webm', '.mov'].includes(extname(f).toLowerCase()),
      );

      // Пробуем найти ffprobe для получения длительности
      let ffprobePath: string | null = null;
      try {
        const bins = findFFmpeg();
        ffprobePath = bins.ffprobe;
      } catch {
        // ffprobe не найден — длительность будет null
      }

      // Загружаем промпты для описаний
      let promptsMap: Record<string, string> = {};
      if (existsSync(paths.prompts)) {
        try {
          const promptsData = JSON.parse(readFileSync(paths.prompts, 'utf-8'));
          if (Array.isArray(promptsData)) {
            for (const clip of promptsData) {
              if (clip.clip_id && clip.scene_description_ru) {
                promptsMap[clip.clip_id] = clip.scene_description_ru;
              }
            }
          }
        } catch { /* ignore parse errors */ }
      }

      for (const file of files) {
        const filePath = resolve(clipsDir, file);
        const clipId = basename(file, extname(file));
        const sceneMatch = clipId.match(/^(SC\d+)/);
        const sceneId = sceneMatch ? sceneMatch[1] : clipId;

        // Ищем thumbnail (первый кадр) в frames/
        let thumbnail: string | null = null;
        const framesDir = paths.frames;
        if (existsSync(framesDir)) {
          // Ищем файл типа SC001_A.png или SC001_A_frame.png
          const candidates = [
            `${clipId}.png`, `${clipId}.jpg`,
            `${clipId}_frame.png`, `${clipId}_first.png`,
          ];
          for (const cand of candidates) {
            if (existsSync(resolve(framesDir, cand))) {
              thumbnail = `frames/${cand}`;
              break;
            }
          }
        }

        // Если нет в frames/, ищем принятый первый кадр в review/
        if (!thumbnail && existsSync(reviewDir)) {
          const clipReviewDir = resolve(reviewDir, clipId, 'nb_first');
          if (existsSync(clipReviewDir)) {
            // Ищем принятый вариант
            const attemptDirs = readdirSync(clipReviewDir).filter((d) =>
              d.startsWith('attempt_') && statSync(resolve(clipReviewDir, d)).isDirectory(),
            );
            for (const ad of attemptDirs) {
              const varFiles = readdirSync(resolve(clipReviewDir, ad)).filter((f) =>
                ['.png', '.jpg', '.jpeg'].includes(extname(f).toLowerCase()),
              );
              if (varFiles.length > 0) {
                thumbnail = `review/${clipId}/nb_first/${ad}/${varFiles[0]}`;
                break;
              }
            }
          }
        }

        let duration: number | null = null;
        if (ffprobePath) {
          try {
            duration = await getVideoDuration(ffprobePath, filePath);
          } catch { /* ignore */ }
        }

        clips.push({
          clipId,
          sceneId,
          filename: file,
          filePath: `clips/${file}`,
          duration,
          thumbnail,
          descriptionRu: promptsMap[clipId] || '',
        });
      }
    }

    // Также ищем принятые VEO видео из review/ (если clips/ ещё не собраны)
    if (existsSync(reviewDir) && clips.length === 0) {
      const clipDirs = readdirSync(reviewDir).filter((d) => {
        const dp = resolve(reviewDir, d);
        return statSync(dp).isDirectory() && d.match(/^SC\d+/);
      });

      let ffprobePath: string | null = null;
      try {
        const bins = findFFmpeg();
        ffprobePath = bins.ffprobe;
      } catch { /* ignore */ }

      // Загружаем промпты для описаний
      let promptsMap: Record<string, string> = {};
      if (existsSync(paths.prompts)) {
        try {
          const promptsData = JSON.parse(readFileSync(paths.prompts, 'utf-8'));
          if (Array.isArray(promptsData)) {
            for (const clip of promptsData) {
              if (clip.clip_id && clip.scene_description_ru) {
                promptsMap[clip.clip_id] = clip.scene_description_ru;
              }
            }
          }
        } catch { /* ignore */ }
      }

      // Загружаем манифесты
      for (const clipId of clipDirs) {
        const veoDir = resolve(reviewDir, clipId, 'veo');
        if (!existsSync(veoDir)) continue;

        // Проверяем манифест
        const manifestPath = resolve(reviewDir, clipId, 'manifest.json');
        if (!existsSync(manifestPath)) continue;

        let manifest;
        try {
          manifest = JSON.parse(readFileSync(manifestPath, 'utf-8'));
        } catch { continue; }

        const veoState = manifest.components?.veo;
        if (!veoState || veoState.status !== 'accepted') continue;

        // Находим принятый вариант
        const selected = veoState.selected_variant_a;
        if (!selected) continue;

        const attemptDir = resolve(veoDir, `attempt_${selected.attempt}`);
        if (!existsSync(attemptDir)) continue;

        const videoFiles = readdirSync(attemptDir).filter((f) =>
          ['.mp4', '.webm', '.mov'].includes(extname(f).toLowerCase()),
        );

        const variantFile = videoFiles.find((f) => f.includes(`variant_${selected.variant}`)) || videoFiles[selected.variant];
        if (!variantFile) continue;

        const filePath = resolve(attemptDir, variantFile);
        const sceneMatch = clipId.match(/^(SC\d+)/);
        const sceneId = sceneMatch ? sceneMatch[1] : clipId;

        // Ищем thumbnail
        let thumbnail: string | null = null;
        const firstDir = resolve(reviewDir, clipId, 'nb_first');
        if (existsSync(firstDir)) {
          const firstState = manifest.components?.nb_first;
          const firstSelected = firstState?.selected_variant_a;
          if (firstSelected) {
            const fAttemptDir = resolve(firstDir, `attempt_${firstSelected.attempt}`);
            if (existsSync(fAttemptDir)) {
              const imgFiles = readdirSync(fAttemptDir).filter((f) =>
                ['.png', '.jpg', '.jpeg'].includes(extname(f).toLowerCase()),
              );
              const imgFile = imgFiles.find((f) => f.includes(`variant_${firstSelected.variant}`)) || imgFiles[firstSelected.variant];
              if (imgFile) {
                thumbnail = `review/${clipId}/nb_first/attempt_${firstSelected.attempt}/${imgFile}`;
              }
            }
          }
        }

        let duration: number | null = null;
        if (ffprobePath) {
          try {
            duration = await getVideoDuration(ffprobePath, filePath);
          } catch { /* ignore */ }
        }

        clips.push({
          clipId,
          sceneId,
          filename: variantFile,
          filePath: `review/${clipId}/veo/attempt_${selected.attempt}/${variantFile}`,
          duration,
          thumbnail,
          descriptionRu: promptsMap[clipId] || '',
        });
      }
    }

    // Сортируем по clipId
    clips.sort((a, b) => {
      const aNum = parseInt(a.clipId.replace(/\D/g, ''), 10) || 0;
      const bNum = parseInt(b.clipId.replace(/\D/g, ''), 10) || 0;
      if (aNum !== bNum) return aNum - bNum;
      return a.clipId.localeCompare(b.clipId);
    });

    res.json({ clips });
  });

  // POST /api/assembly/:projectId/export — экспорт склеенного видео
  router.post('/:projectId/export', async (req, res) => {
    const project = store.get(req.params.projectId);
    if (!project) {
      res.status(404).json({ error: 'Проект не найден' });
      return;
    }

    const { timeline, name } = req.body as {
      timeline: Array<{ filePath: string; startSec: number; endSec: number }>;
      name?: string;
    };

    if (!timeline || !Array.isArray(timeline) || timeline.length === 0) {
      res.status(400).json({ error: 'Таймлайн пуст' });
      return;
    }

    // Проверяем наличие FFmpeg
    try {
      findFFmpeg();
    } catch (err) {
      res.status(500).json({ error: (err as Error).message });
      return;
    }

    const projectDir = resolve(config.dataDir, 'projects', project.id);

    // Преобразуем относительные пути в абсолютные
    const timelineClips: TimelineClip[] = timeline.map((item) => ({
      file: resolve(projectDir, item.filePath),
      startSec: item.startSec || 0,
      endSec: item.endSec || 0,
    }));

    // Проверяем что все файлы существуют
    for (const clip of timelineClips) {
      if (!existsSync(clip.file)) {
        res.status(400).json({ error: `Файл не найден: ${clip.file}` });
        return;
      }
    }

    // Генерируем имя файла
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    const outputName = name
      ? `${name.replace(/[^a-zA-Z0-9_а-яА-ЯёЁ-]/g, '_')}.mp4`
      : `export_${timestamp}.mp4`;

    try {
      const result = await exportVideo(projectDir, timelineClips, outputName);

      res.json({
        success: true,
        export: {
          name: outputName,
          path: `exports/${outputName}`,
          duration: result.duration,
          clipCount: result.clipCount,
        },
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      res.status(500).json({ error: `Ошибка экспорта: ${message}` });
    }
  });

  // GET /api/assembly/:projectId/exports — список экспортированных видео
  router.get('/:projectId/exports', async (req, res) => {
    const project = store.get(req.params.projectId);
    if (!project) {
      res.status(404).json({ error: 'Проект не найден' });
      return;
    }

    const projectDir = resolve(config.dataDir, 'projects', project.id);
    const exportsDir = resolve(projectDir, 'exports');

    if (!existsSync(exportsDir)) {
      res.json({ exports: [] });
      return;
    }

    let ffprobePath: string | null = null;
    try {
      const bins = findFFmpeg();
      ffprobePath = bins.ffprobe;
    } catch { /* ignore */ }

    const files = readdirSync(exportsDir).filter((f) =>
      ['.mp4', '.webm', '.mov'].includes(extname(f).toLowerCase()),
    );

    const exports: ExportInfo[] = [];

    for (const file of files) {
      const filePath = resolve(exportsDir, file);
      const stat = statSync(filePath);

      let duration: number | null = null;
      if (ffprobePath) {
        try {
          duration = await getVideoDuration(ffprobePath, filePath);
        } catch { /* ignore */ }
      }

      exports.push({
        name: basename(file, extname(file)),
        filename: file,
        path: `exports/${file}`,
        size: stat.size,
        duration,
        clipCount: 0, // Неизвестно для уже экспортированных
        createdAt: stat.mtime.toISOString(),
      });
    }

    // Сортируем по дате (новые сверху)
    exports.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());

    res.json({ exports });
  });

  // GET /api/assembly/:projectId/ffmpeg-status — проверка наличия FFmpeg
  router.get('/:projectId/ffmpeg-status', (_req, res) => {
    try {
      const bins = findFFmpeg();
      res.json({ available: true, ffmpeg: bins.ffmpeg, ffprobe: bins.ffprobe });
    } catch (err) {
      res.json({ available: false, error: (err as Error).message });
    }
  });

  return router;
}
