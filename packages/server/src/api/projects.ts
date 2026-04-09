import { Router } from 'express';
import { readFileSync, writeFileSync, existsSync, readdirSync } from 'node:fs';
import { resolve } from 'node:path';
import type { AppConfig } from '../config.js';
import { ProjectStore } from '../data/project-store.js';
import { loadManifest, saveManifest, markAccepted, markRejected, copyAcceptedToOutput } from '../data/manifest.js';
import { fixPromptsBatch, fixPromptByFeedback } from '../ai/feedback.js';
import { broadcast } from '../ws/events.js';
import type { Clip, ComponentName } from '@flow-app/shared';

export function projectsRouter(config: AppConfig): Router {
  const router = Router();
  const store = new ProjectStore(config.dataDir);

  // GET /api/projects — список проектов
  router.get('/', (_req, res) => {
    res.json(store.list());
  });

  // POST /api/projects — создать проект
  router.post('/', (req, res) => {
    const { name, nameRu } = req.body;
    if (!name) {
      res.status(400).json({ error: 'Имя проекта обязательно' });
      return;
    }
    const project = store.create(name, nameRu || name);
    res.status(201).json(project);
  });

  // GET /api/projects/:id — данные проекта
  router.get('/:id', (req, res) => {
    const project = store.get(req.params.id);
    if (!project) {
      res.status(404).json({ error: 'Проект не найден' });
      return;
    }
    res.json(project);
  });

  // PATCH /api/projects/:id — обновить проект
  router.patch('/:id', (req, res) => {
    const project = store.get(req.params.id);
    if (!project) {
      res.status(404).json({ error: 'Проект не найден' });
      return;
    }
    Object.assign(project, req.body);
    store.save(project);
    res.json(project);
  });

  // GET /api/projects/:id/clips — все клипы
  router.get('/:id/clips', (req, res) => {
    const project = store.get(req.params.id);
    if (!project) {
      res.status(404).json({ error: 'Проект не найден' });
      return;
    }
    const promptsFile = resolve(store.projectDir(project.id), 'prompts', 'all_prompts.json');
    if (!existsSync(promptsFile)) {
      res.json([]);
      return;
    }
    const clips: Clip[] = JSON.parse(readFileSync(promptsFile, 'utf-8'));
    res.json(clips);
  });

  // GET /api/projects/:id/review — клипы на ревью с манифестами (с пагинацией и фильтрацией)
  router.get('/:id/review', (req, res) => {
    const project = store.get(req.params.id);
    if (!project) {
      res.status(404).json({ error: 'Проект не найден' });
      return;
    }

    const promptsFile = resolve(store.projectDir(project.id), 'prompts', 'all_prompts.json');
    if (!existsSync(promptsFile)) {
      res.json({ clips: [], manifests: {}, total: 0, totalAll: 0, page: 1, limit: 40, stats: { total: 0, firstAccepted: 0, veoAccepted: 0, needsReview: 0, pendingPhotos: 0, pendingVideos: 0, chainBlocked: 0 } });
      return;
    }

    const allClips: Clip[] = JSON.parse(readFileSync(promptsFile, 'utf-8'));
    const reviewDir = resolve(store.projectDir(project.id), 'review');

    // Load all manifests for filtering and stats
    const allManifests: Record<string, Record<string, unknown>> = {};
    for (const clip of allClips) {
      const manifest = loadManifest(reviewDir, clip.clip_id);
      if (manifest) {
        allManifests[clip.clip_id] = manifest as unknown as Record<string, unknown>;
      }
    }

    // Stats
    let firstAccepted = 0, veoAccepted = 0, needsReview = 0, pendingPhotos = 0, pendingVideos = 0, chainBlocked = 0;
    for (const clip of allClips) {
      const m = allManifests[clip.clip_id] as { components?: Record<string, { status?: string }> } | undefined;
      const firstSt = m?.components?.nb_first?.status || 'pending';
      const veoSt = m?.components?.veo?.status || 'pending';
      if (firstSt === 'accepted') firstAccepted++;
      if (veoSt === 'accepted') veoAccepted++;
      if (firstSt === 'generated' || veoSt === 'generated') needsReview++;
      if (firstSt === 'pending') pendingPhotos++;
      if (veoSt === 'pending' && firstSt === 'accepted') pendingVideos++;
      if (veoSt === 'pending' && firstSt !== 'accepted' && firstSt !== 'generated') chainBlocked++;
    }

    // Server-side filtering
    const filter = (req.query.filter as string) || 'all';
    const search = ((req.query.search as string) || '').toLowerCase().trim();

    let filtered = allClips;

    // Search
    if (search) {
      filtered = filtered.filter(clip =>
        clip.clip_id.toLowerCase().includes(search) ||
        clip.scene_id.toLowerCase().includes(search) ||
        (clip.scene_description_ru || '').toLowerCase().includes(search)
      );
    }

    // Filter by view mode
    filtered = filtered.filter(clip => {
      const m = allManifests[clip.clip_id] as { components?: Record<string, { status?: string }> } | undefined;
      const firstSt = m?.components?.nb_first?.status || 'pending';
      const veoSt = m?.components?.veo?.status || 'pending';

      switch (filter) {
        case 'review_photos': return firstSt === 'generated';
        case 'review_videos': return veoSt === 'generated';
        case 'review_all': return firstSt === 'generated' || veoSt === 'generated';
        case 'all_photos': return true;
        case 'all_videos': return veoSt !== 'pending';
        case 'accepted': return firstSt === 'accepted';
        case 'blocked': return veoSt === 'pending' && firstSt !== 'accepted' && firstSt !== 'generated';
        case 'all': default: return true;
      }
    });

    // Pagination
    const page = Math.max(1, parseInt(req.query.page as string, 10) || 1);
    const limit = Math.max(1, Math.min(200, parseInt(req.query.limit as string, 10) || 40));
    const totalFiltered = filtered.length;
    const start = (page - 1) * limit;
    const pageClips = filtered.slice(start, start + limit);

    // Return manifests only for current page
    const manifests: Record<string, unknown> = {};
    for (const clip of pageClips) {
      if (allManifests[clip.clip_id]) {
        manifests[clip.clip_id] = allManifests[clip.clip_id];
      }
    }

    res.json({
      clips: pageClips,
      manifests,
      total: totalFiltered,
      totalAll: allClips.length,
      page,
      limit,
      stats: { total: allClips.length, firstAccepted, veoAccepted, needsReview, pendingPhotos, pendingVideos, chainBlocked },
    });
  });

  // POST /api/projects/:id/review/submit — batch accept/reject + Claude API для фидбеков
  router.post('/:id/review/submit', async (req, res) => {
    const project = store.get(req.params.id);
    if (!project) {
      res.status(404).json({ error: 'Проект не найден' });
      return;
    }

    try {
      const projectDir = store.projectDir(project.id);
      const reviewDir = resolve(projectDir, 'review');
      const promptsFile = resolve(projectDir, 'prompts', 'all_prompts.json');
      const model = (req.body.model || 'sonnet') as 'opus' | 'sonnet';
      const decisions: Array<{
        clipId: string;
        component: string;
        action: 'accept' | 'reject';
        attempt?: number;
        variant?: number;
        scores?: Record<string, number>;
        feedback?: string;
      }> = req.body.decisions || [];

      // Загружаем промпты для исправлений
      let clips: Clip[] = [];
      if (existsSync(promptsFile)) {
        clips = JSON.parse(readFileSync(promptsFile, 'utf-8'));
      }

      const results: Array<{ clipId: string; success: boolean; error?: string }> = [];
      const toFix: Array<{ clip: Clip; component: string; feedback: string; sceneContext: string }> = [];
      let acceptedCount = 0;

      // 1. Обрабатываем решения: принятые сразу, отклонённые собираем для Claude
      for (const decision of decisions) {
        try {
          const manifest = loadManifest(reviewDir, decision.clipId);
          if (!manifest) {
            results.push({ clipId: decision.clipId, success: false, error: 'Манифест не найден' });
            continue;
          }

          const component = decision.component as ComponentName;

          if (decision.action === 'accept' && decision.attempt != null && decision.variant != null) {
            markAccepted(manifest, component, decision.attempt, decision.variant, decision.scores || null);
            copyAcceptedToOutput(reviewDir, projectDir, manifest, component);
            saveManifest(reviewDir, manifest);
            acceptedCount++;
            results.push({ clipId: decision.clipId, success: true });
          } else if (decision.action === 'reject' && decision.feedback) {
            markRejected(manifest, component, decision.feedback);
            saveManifest(reviewDir, manifest);

            // Собираем для Claude
            const clip = clips.find((c) => c.clip_id === decision.clipId);
            if (clip) {
              toFix.push({
                clip,
                component,
                feedback: decision.feedback,
                sceneContext: clip.scene_description_ru,
              });
            }
            results.push({ clipId: decision.clipId, success: true });
          }
        } catch (decisionErr) {
          const msg = decisionErr instanceof Error ? decisionErr.message : String(decisionErr);
          console.error(`Ошибка обработки решения для ${decision.clipId}:`, msg);
          results.push({ clipId: decision.clipId, success: false, error: msg });
        }
      }

      // 2. Если есть отклонённые с фидбеком и есть API ключ — исправляем через Claude
      let fixResults: Array<{ clipId: string; component: string; explanation: string }> = [];
      let fixFailures: Array<{ clipId: string; component: string; error: string }> = [];

      if (toFix.length > 0 && config.anthropicApiKey) {
        // Оповещаем фронт что началось исправление
        broadcast({ type: 'generation_progress', data: { action: 'fixing_start', total: toFix.length } });

        try {
          const { successes, failures } = await fixPromptsBatch(config, toFix, model, (done, total) => {
            broadcast({ type: 'generation_progress', data: { action: 'fixing_progress', done, total } });
          });

          // 3. Обновляем промпты в all_prompts.json
          for (const fix of successes) {
            const clipIdx = clips.findIndex((c) => c.clip_id === fix.clip_id);
            if (clipIdx < 0) continue;

            if (fix.component === 'nb_first') {
              clips[clipIdx].nano_banana_prompt_first = fix.new_prompt;
            } else if (fix.component === 'veo') {
              clips[clipIdx].veo_prompt = fix.new_prompt;
            }

            fixResults.push({
              clipId: fix.clip_id,
              component: fix.component,
              explanation: fix.explanation,
            });
          }

          fixFailures = failures.map((f) => ({
            clipId: f.clip_id,
            component: f.component,
            error: f.error,
          }));

          // Сохраняем обновлённые промпты
          writeFileSync(promptsFile, JSON.stringify(clips, null, 2), 'utf-8');

          broadcast({
            type: 'generation_progress',
            data: {
              action: 'fixing_done',
              fixed: successes.length,
              failed: failures.length,
            },
          });
        } catch (err) {
          const message = err instanceof Error ? err.message : String(err);
          broadcast({ type: 'generation_progress', data: { action: 'fixing_error', error: message } });
        }
      }

      res.json({
        results,
        accepted: acceptedCount,
        rejected: toFix.length,
        promptsFixed: fixResults,
        promptsFailures: fixFailures,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      console.error('Ошибка в review/submit:', message);
      res.status(500).json({ error: `Ошибка сервера: ${message}` });
    }
  });

  // POST /api/projects/:id/review/revoke — отозвать принятый вариант
  router.post('/:id/review/revoke', async (req, res) => {
    const project = store.get(req.params.id);
    if (!project) {
      res.status(404).json({ error: 'Проект не найден' });
      return;
    }

    try {
      const { clipId, component, feedback } = req.body as {
        clipId: string;
        component: string;
        feedback?: string;
      };

      if (!clipId || !component) {
        res.status(400).json({ error: 'clipId и component обязательны' });
        return;
      }

      const projectDir = store.projectDir(project.id);
      const reviewDir = resolve(projectDir, 'review');
      const manifest = loadManifest(reviewDir, clipId);

      if (!manifest) {
        res.status(404).json({ error: 'Манифест не найден' });
        return;
      }

      const comp = manifest.components[component as ComponentName];
      if (!comp) {
        res.status(404).json({ error: 'Компонент не найден' });
        return;
      }

      if (comp.status !== 'accepted') {
        res.status(400).json({ error: 'Компонент не в статусе "accepted"' });
        return;
      }

      // Сбрасываем статус
      comp.status = 'pending';
      comp.selected_variant_a = null;
      comp.feedback = feedback || '';
      saveManifest(reviewDir, manifest);

      // Если есть фидбек и API ключ — исправляем промпт через Claude
      let fixResult = null;
      if (feedback && config.anthropicApiKey) {
        const promptsFile = resolve(projectDir, 'prompts', 'all_prompts.json');
        if (existsSync(promptsFile)) {
          const clips: Clip[] = JSON.parse(readFileSync(promptsFile, 'utf-8'));
          const clip = clips.find((c) => c.clip_id === clipId);
          if (clip) {
            try {
              const fix = await fixPromptByFeedback(
                config,
                clip,
                component,
                feedback,
                clip.scene_description_ru,
                'sonnet',
              );

              // Обновляем промпт
              const clipIdx = clips.findIndex((c) => c.clip_id === clipId);
              if (fix.component === 'nb_first' || component === 'nb_first') {
                clips[clipIdx].nano_banana_prompt_first = fix.new_prompt;
              } else if (fix.component === 'veo' || component === 'veo') {
                clips[clipIdx].veo_prompt = fix.new_prompt;
              }

              writeFileSync(promptsFile, JSON.stringify(clips, null, 2), 'utf-8');
              fixResult = { explanation: fix.explanation };
            } catch (err) {
              const message = err instanceof Error ? err.message : String(err);
              fixResult = { error: message };
            }
          }
        }
      }

      res.json({ success: true, fixResult });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      console.error('Ошибка в review/revoke:', message);
      res.status(500).json({ error: `Ошибка сервера: ${message}` });
    }
  });

  // POST /api/projects/:id/review/reset-veo — сбросить все VEO "generated" → "pending"
  router.post('/:id/review/reset-veo', async (req, res) => {
    const project = store.get(req.params.id);
    if (!project) {
      res.status(404).json({ error: 'Проект не найден' });
      return;
    }

    try {
      const projectDir = store.projectDir(project.id);
      const reviewDir = resolve(projectDir, 'review');

      if (!existsSync(reviewDir)) {
        res.json({ reset: 0, message: 'Нет папки review' });
        return;
      }

      let resetCount = 0;
      const clipDirs = readdirSync(reviewDir, { withFileTypes: true })
        .filter((d) => d.isDirectory())
        .map((d) => d.name);

      for (const clipId of clipDirs) {
        const manifest = loadManifest(reviewDir, clipId);
        if (!manifest) continue;

        const veo = manifest.components.veo;
        if (veo && veo.status === 'generated') {
          veo.status = 'pending';
          veo.attempts = [];
          veo.selected_variant_a = null;
          veo.feedback = '';
          saveManifest(reviewDir, manifest);
          resetCount++;
        }
      }

      res.json({ reset: resetCount, message: `Сброшено ${resetCount} VEO на pending` });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      console.error('Ошибка в reset-veo:', message);
      res.status(500).json({ error: `Ошибка сервера: ${message}` });
    }
  });

  return router;
}
