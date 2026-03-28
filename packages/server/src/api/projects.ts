import { Router } from 'express';
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
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

  // GET /api/projects/:id/review — клипы на ревью с манифестами (с пагинацией)
  router.get('/:id/review', (req, res) => {
    const project = store.get(req.params.id);
    if (!project) {
      res.status(404).json({ error: 'Проект не найден' });
      return;
    }

    const promptsFile = resolve(store.projectDir(project.id), 'prompts', 'all_prompts.json');
    if (!existsSync(promptsFile)) {
      res.json({ clips: [], manifests: {}, total: 0, page: 1, limit: 40 });
      return;
    }

    const allClips: Clip[] = JSON.parse(readFileSync(promptsFile, 'utf-8'));
    const reviewDir = resolve(store.projectDir(project.id), 'review');

    // Пагинация
    const page = Math.max(1, parseInt(req.query.page as string, 10) || 1);
    const limit = Math.max(1, Math.min(200, parseInt(req.query.limit as string, 10) || 40));
    const start = (page - 1) * limit;
    const pageClips = allClips.slice(start, start + limit);

    const manifests: Record<string, unknown> = {};
    for (const clip of pageClips) {
      const manifest = loadManifest(reviewDir, clip.clip_id);
      if (manifest) {
        manifests[clip.clip_id] = manifest;
      }
    }

    res.json({
      clips: allClips,  // Возвращаем все клипы для фильтрации на клиенте
      manifests,
      total: allClips.length,
      page,
      limit,
      // Загружаем манифесты только для текущей страницы
      manifestPage: pageClips.map((c) => c.clip_id),
    });
  });

  // POST /api/projects/:id/review/submit — batch accept/reject + Claude API для фидбеков
  router.post('/:id/review/submit', async (req, res) => {
    const project = store.get(req.params.id);
    if (!project) {
      res.status(404).json({ error: 'Проект не найден' });
      return;
    }

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
  });

  // POST /api/projects/:id/review/revoke — отозвать принятый вариант
  router.post('/:id/review/revoke', async (req, res) => {
    const project = store.get(req.params.id);
    if (!project) {
      res.status(404).json({ error: 'Проект не найден' });
      return;
    }

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
  });

  return router;
}
