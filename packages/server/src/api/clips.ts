import { Router } from 'express';
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';
import type { AppConfig } from '../config.js';
import { ProjectStore } from '../data/project-store.js';
import { askClaudeJson } from '../ai/client.js';
import { fixPromptByFeedback } from '../ai/feedback.js';
import type { Clip } from '@flow-app/shared';

export function clipsRouter(config: AppConfig): Router {
  const router = Router();
  const store = new ProjectStore(config.dataDir);

  // POST /api/clips/translate — перевести промпты на русский
  router.post('/translate', async (req, res) => {
    const { projectId, texts } = req.body as {
      projectId: string;
      texts: { first: string; veo: string };
    };

    if (!config.anthropicApiKey) {
      res.status(400).json({ error: 'Claude API ключ не настроен' });
      return;
    }

    try {
      const result = await askClaudeJson<{ first: string; veo: string }>(
        config,
        'You are a translator. Translate the following animation prompts from English to Russian. Keep it natural and concise. Return JSON: {"first": "...", "veo": "..."}',
        `Translate these prompts:\n\nFirst: ${texts.first}\n\nVEO: ${texts.veo}`,
        'sonnet',
        false,  // не нужны правила для перевода
      );

      res.json({ translations: result });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      res.status(500).json({ error: `Ошибка перевода: ${message}` });
    }
  });

  // POST /api/clips/fix — исправить один промпт по фидбеку
  router.post('/fix', async (req, res) => {
    const { projectId, clipId, component, feedback, model } = req.body as {
      projectId: string;
      clipId: string;
      component: string;
      feedback: string;
      model: 'sonnet' | 'opus';
    };

    if (!config.anthropicApiKey) {
      res.status(400).json({ error: 'Claude API ключ не настроен' });
      return;
    }

    const project = store.get(projectId);
    if (!project) {
      res.status(404).json({ error: 'Проект не найден' });
      return;
    }

    const promptsFile = resolve(store.projectDir(projectId), 'prompts', 'all_prompts.json');
    if (!existsSync(promptsFile)) {
      res.status(404).json({ error: 'Файл промптов не найден' });
      return;
    }

    const clips: Clip[] = JSON.parse(readFileSync(promptsFile, 'utf-8'));
    const clip = clips.find((c) => c.clip_id === clipId);
    if (!clip) {
      res.status(404).json({ error: `Клип ${clipId} не найден` });
      return;
    }

    try {
      const fix = await fixPromptByFeedback(
        config,
        clip,
        component,
        feedback,
        clip.scene_description_ru,
        model || 'sonnet',
      );

      // Обновляем промпт
      const clipIdx = clips.findIndex((c) => c.clip_id === clipId);
      if (fix.component === 'nb_first' || component === 'nb_first') {
        clips[clipIdx].nano_banana_prompt_first = fix.new_prompt;
      } else if (fix.component === 'veo' || component === 'veo') {
        clips[clipIdx].veo_prompt = fix.new_prompt;
      }

      writeFileSync(promptsFile, JSON.stringify(clips, null, 2), 'utf-8');

      res.json({
        success: true,
        fix: {
          oldPrompt: fix.old_prompt,
          newPrompt: fix.new_prompt,
          explanation: fix.explanation,
        },
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      res.status(500).json({ error: `Ошибка исправления промпта: ${message}` });
    }
  });

  return router;
}
