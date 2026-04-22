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

  // PATCH /api/clips/update — прямое редактирование промпта
  router.patch('/update', (req, res) => {
    const { projectId, clipId, component, prompt } = req.body as {
      projectId: string;
      clipId: string;
      component: 'nb_first' | 'veo';
      prompt: string;
    };

    if (!projectId || !clipId || !component || prompt == null) {
      res.status(400).json({ error: 'projectId, clipId, component и prompt обязательны' });
      return;
    }

    const promptsFile = resolve(store.projectDir(projectId), 'prompts', 'all_prompts.json');
    if (!existsSync(promptsFile)) {
      res.status(404).json({ error: 'Файл промптов не найден' });
      return;
    }

    const clips: Clip[] = JSON.parse(readFileSync(promptsFile, 'utf-8'));
    const clipIdx = clips.findIndex((c) => c.clip_id === clipId);
    if (clipIdx < 0) {
      res.status(404).json({ error: `Клип ${clipId} не найден` });
      return;
    }

    if (component === 'nb_first') {
      clips[clipIdx].nano_banana_prompt_first = prompt;
    } else if (component === 'veo') {
      clips[clipIdx].veo_prompt = prompt;
    } else {
      res.status(400).json({ error: `Неизвестный компонент: ${component}` });
      return;
    }

    writeFileSync(promptsFile, JSON.stringify(clips, null, 2), 'utf-8');
    res.json({ success: true, clipId, component, prompt });
  });

  // PATCH /api/clips/update-ingredient — заменить один ингредиент клипа по индексу
  router.patch('/update-ingredient', (req, res) => {
    const { projectId, clipId, index, path } = req.body as {
      projectId: string;
      clipId: string;
      index: number;
      path: string;
    };

    if (!projectId || !clipId || index == null || !path) {
      res.status(400).json({ error: 'projectId, clipId, index и path обязательны' });
      return;
    }

    const promptsFile = resolve(store.projectDir(projectId), 'prompts', 'all_prompts.json');
    if (!existsSync(promptsFile)) {
      res.status(404).json({ error: 'Файл промптов не найден' });
      return;
    }

    const clips: Clip[] = JSON.parse(readFileSync(promptsFile, 'utf-8'));
    const clipIdx = clips.findIndex((c) => c.clip_id === clipId);
    if (clipIdx < 0) {
      res.status(404).json({ error: `Клип ${clipId} не найден` });
      return;
    }

    const ingredients = [...clips[clipIdx].nano_banana_ingredients];
    if (index < 0 || index >= ingredients.length) {
      res.status(400).json({ error: `Индекс вне диапазона (${ingredients.length} ингр.)` });
      return;
    }

    ingredients[index] = path;
    clips[clipIdx].nano_banana_ingredients = ingredients;

    writeFileSync(promptsFile, JSON.stringify(clips, null, 2), 'utf-8');
    res.json({ success: true, clipId, index, path });
  });

  // POST /api/clips/add-ingredient — добавить ингредиент в конец массива
  router.post('/add-ingredient', (req, res) => {
    const { projectId, clipId, path } = req.body as {
      projectId: string;
      clipId: string;
      path: string;
    };

    if (!projectId || !clipId || !path) {
      res.status(400).json({ error: 'projectId, clipId и path обязательны' });
      return;
    }

    const promptsFile = resolve(store.projectDir(projectId), 'prompts', 'all_prompts.json');
    if (!existsSync(promptsFile)) {
      res.status(404).json({ error: 'Файл промптов не найден' });
      return;
    }

    const clips: Clip[] = JSON.parse(readFileSync(promptsFile, 'utf-8'));
    const clipIdx = clips.findIndex((c) => c.clip_id === clipId);
    if (clipIdx < 0) {
      res.status(404).json({ error: `Клип ${clipId} не найден` });
      return;
    }

    const ingredients = [...clips[clipIdx].nano_banana_ingredients];
    if (ingredients.length >= 14) {
      res.status(400).json({ error: 'Достигнут лимит NB Pro (14 ингредиентов)' });
      return;
    }

    ingredients.push(path);
    clips[clipIdx].nano_banana_ingredients = ingredients;

    writeFileSync(promptsFile, JSON.stringify(clips, null, 2), 'utf-8');
    res.json({ success: true, clipId, index: ingredients.length - 1, path });
  });

  // DELETE /api/clips/remove-ingredient — удалить ингредиент по индексу
  router.delete('/remove-ingredient', (req, res) => {
    const { projectId, clipId, index } = req.body as {
      projectId: string;
      clipId: string;
      index: number;
    };

    if (!projectId || !clipId || index == null) {
      res.status(400).json({ error: 'projectId, clipId и index обязательны' });
      return;
    }

    const promptsFile = resolve(store.projectDir(projectId), 'prompts', 'all_prompts.json');
    if (!existsSync(promptsFile)) {
      res.status(404).json({ error: 'Файл промптов не найден' });
      return;
    }

    const clips: Clip[] = JSON.parse(readFileSync(promptsFile, 'utf-8'));
    const clipIdx = clips.findIndex((c) => c.clip_id === clipId);
    if (clipIdx < 0) {
      res.status(404).json({ error: `Клип ${clipId} не найден` });
      return;
    }

    const ingredients = [...clips[clipIdx].nano_banana_ingredients];
    if (index < 0 || index >= ingredients.length) {
      res.status(400).json({ error: `Индекс вне диапазона (${ingredients.length} ингр.)` });
      return;
    }

    ingredients.splice(index, 1);
    clips[clipIdx].nano_banana_ingredients = ingredients;

    writeFileSync(promptsFile, JSON.stringify(clips, null, 2), 'utf-8');
    res.json({ success: true, clipId, index, remaining: ingredients.length });
  });

  return router;
}
