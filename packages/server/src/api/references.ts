import { Router } from 'express';
import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import type { AppConfig } from '../config.js';
import { ProjectStore } from '../data/project-store.js';
import { projectPaths, ensureDir } from '../data/file-manager.js';
import {
  createRefManifest,
  loadRefManifest,
  saveRefManifest,
  markRefAccepted,
  markRefRejected,
  copyAcceptedBase,
  copyAcceptedAngle,
  getRefReviewItems,
} from '../data/ref-manifest.js';
import {
  LOCATION_ANGLE_TYPES,
  CHARACTER_ANGLE_TYPES,
} from '@flow-app/shared';
import { readFileSync } from 'node:fs';
import {
  generateBasePrompt as aiGenerateBasePrompt,
  generateAnglePrompt as aiGenerateAnglePrompt,
  rewritePromptWithFeedback,
  isClaudeAvailable,
} from '../ai/references.js';

type ModelChoice = 'opus' | 'sonnet';

/** Fallback: шаблонный промпт для базового образа (если Claude недоступен) */
function basePromptFallback(type: 'characters' | 'locations', name: string, description: string): string {
  if (type === 'characters') {
    return `Full body shot of ${description}. Front view, neutral pose, clear details. No text, no watermarks. 3D Pixar-style, family-friendly, cinematic.`;
  }
  return `${description}. Wide establishing shot showing the full location. Clear details, consistent lighting. No text, no watermarks. 3D Pixar-style, family-friendly, cinematic.`;
}

/** Fallback: шаблонный промпт для ракурса (если Claude недоступен) */
function anglePromptFallback(type: 'characters' | 'locations', angleDescription: string): string {
  if (type === 'characters') {
    return `The EXACT same character from Image 1 — same face, same body proportions, same clothing, same hairstyle, same accessories. IDENTICAL appearance. Pose: ${angleDescription}. No text, no watermarks. 3D Pixar-style, family-friendly, cinematic.`;
  }
  return `Reproduce the EXACT same location from Image 1 — same walls, same floor, same furniture, same objects, same colors, same textures, same lighting. NOTHING added, NOTHING removed, NOTHING changed. Camera angle: ${angleDescription}. The location must be IDENTICAL to Image 1 in every detail. Only the camera position and angle change. No text, no watermarks. 3D Pixar-style, family-friendly, cinematic.`;
}

/** Генерирует промпт для базового образа (Claude AI с fallback на шаблон) */
async function generateBasePromptSafe(
  config: AppConfig,
  type: 'characters' | 'locations',
  name: string,
  description: string,
  model: ModelChoice,
): Promise<{ prompt: string; aiGenerated: boolean }> {
  if (isClaudeAvailable(config)) {
    try {
      const prompt = await aiGenerateBasePrompt(config, type, name, description, model);
      return { prompt, aiGenerated: true };
    } catch (err) {
      console.warn('[references] Claude API error for base prompt, using fallback:', err);
    }
  }
  return { prompt: basePromptFallback(type, name, description), aiGenerated: false };
}

/** Генерирует промпт для ракурса (Claude AI с fallback на шаблон) */
async function generateAnglePromptSafe(
  config: AppConfig,
  type: 'characters' | 'locations',
  name: string,
  angleDescription: string,
  model: ModelChoice,
): Promise<{ prompt: string; aiGenerated: boolean }> {
  if (isClaudeAvailable(config)) {
    try {
      const prompt = await aiGenerateAnglePrompt(config, type, name, angleDescription, model);
      return { prompt, aiGenerated: true };
    } catch (err) {
      console.warn('[references] Claude API error for angle prompt, using fallback:', err);
    }
  }
  return { prompt: anglePromptFallback(type, angleDescription), aiGenerated: false };
}
import type { RefReviewDecision, Angle } from '@flow-app/shared';
import { getBotManager } from '../bot/manager.js';

export function referencesRouter(config: AppConfig): Router {
  const router = Router();
  const store = new ProjectStore(config.dataDir);

  // ─── GENERATE ────────────────────────────────────────────

  /**
   * POST /api/setup/:id/references/generate
   * Body: { type: "characters" | "locations", itemId: string, target: "base" | "angles" }
   *
   * Triggers reference generation. For now creates manifest stubs and returns
   * "not implemented" since actual bot integration is pending.
   *
   * When variants are manually placed in the review directory, the review
   * flow is fully functional.
   */
  router.post('/:id/references/generate', async (req, res) => {
    const project = store.get(req.params.id);
    if (!project) {
      res.status(404).json({ error: 'Проект не найден' });
      return;
    }

    const { type, itemId, target, model: requestedModel } = req.body as {
      type: 'characters' | 'locations';
      itemId: string;
      target: 'base' | 'angles';
      model?: 'opus' | 'sonnet';
    };
    const model: ModelChoice = requestedModel || 'sonnet';

    if (!type || !itemId || !target) {
      res.status(400).json({ error: 'type, itemId и target обязательны' });
      return;
    }

    // Validate item exists
    if (type === 'characters') {
      const char = project.characters.find((c) => c.id === itemId);
      if (!char) {
        res.status(404).json({ error: `Персонаж ${itemId} не найден` });
        return;
      }
    } else {
      const loc = project.locations.find((l) => l.id === itemId);
      if (!loc) {
        res.status(404).json({ error: `Локация ${itemId} не найдена` });
        return;
      }
    }

    const paths = projectPaths(config.dataDir, project.id);
    const refsDir = resolve(paths.root, 'references');

    if (target === 'base') {
      // Create base manifest (if not exists)
      let manifest = loadRefManifest(refsDir, type, itemId, 'base');
      if (!manifest) {
        manifest = createRefManifest(itemId, type, 'base');
      }
      // Определяем описание для промпта
      const item = type === 'characters'
        ? project.characters.find((c) => c.id === itemId)
        : project.locations.find((l) => l.id === itemId);
      const description = item?.description || item?.name || itemId;
      const { prompt, aiGenerated } = await generateBasePromptSafe(config, type, item?.name || itemId, description, model);

      manifest.status = 'generating';
      // Сохраняем промпт в манифест (бот будет его использовать)
      if (manifest.attempts.length === 0) {
        manifest.attempts.push({
          attempt: 1,
          prompt,
          variants: [],
        });
      }
      saveRefManifest(refsDir, manifest);

      // Update item status
      if (type === 'characters') {
        const char = project.characters.find((c) => c.id === itemId);
        if (char) char.status = 'base_review';
      } else {
        const loc = project.locations.find((l) => l.id === itemId);
        if (loc) loc.status = 'base_review';
      }
      store.save(project);

      // Ensure review directory exists
      const reviewDir = resolve(refsDir, type, itemId, 'review', 'base', 'attempt_1');
      ensureDir(reviewDir);

      res.json({
        success: true,
        message: aiGenerated
          ? `Промпт сгенерирован через Claude (${model}). Бот сгенерирует 4 варианта.`
          : 'Генерация базового образа запущена (шаблон). Бот сгенерирует 4 варианта.',
        botImplemented: false,
        prompt,
        aiGenerated,
        model: aiGenerated ? model : undefined,
        ingredients: [],  // Нет ингредиентов для базового образа
        reviewDir: `references/${type}/${itemId}/review/base/`,
      });
    } else {
      // angles — create manifests for each angle type
      const angleTypes = type === 'characters' ? CHARACTER_ANGLE_TYPES : LOCATION_ANGLE_TYPES;
      const created: string[] = [];

      // Путь к принятому базовому образу (ингредиент для всех ракурсов)
      const item = type === 'characters'
        ? project.characters.find((c) => c.id === itemId)
        : project.locations.find((l) => l.id === itemId);
      const baseImagePath = item?.baseImage || '';

      let anyAiGenerated = false;
      for (const angleType of angleTypes) {
        let manifest = loadRefManifest(refsDir, type, itemId, angleType.id);
        if (!manifest) {
          manifest = createRefManifest(itemId, type, angleType.id);
        }
        if (manifest.status !== 'accepted') {
          const { prompt, aiGenerated } = await generateAnglePromptSafe(
            config, type, item?.name || itemId, angleType.description, model,
          );
          if (aiGenerated) anyAiGenerated = true;
          manifest.status = 'generating';
          // Сохраняем промпт и ингредиент в манифест
          if (manifest.attempts.length === 0) {
            manifest.attempts.push({
              attempt: 1,
              prompt,
              variants: [],
            });
          }
          saveRefManifest(refsDir, manifest);
          created.push(angleType.id);

          // Ensure review directory exists
          const reviewDir = resolve(refsDir, type, itemId, 'review', 'angles', angleType.id, 'attempt_1');
          ensureDir(reviewDir);
        }
      }

      // Update item status
      if (type === 'characters') {
        const char = project.characters.find((c) => c.id === itemId);
        if (char) char.status = 'angles_review';
      } else {
        const loc = project.locations.find((l) => l.id === itemId);
        if (loc) loc.status = 'angles_review';
      }
      store.save(project);

      res.json({
        success: true,
        message: anyAiGenerated
          ? `Промпты сгенерированы через Claude (${model}). ${created.length} ракурсов × 4 варианта.`
          : `Генерация ракурсов запущена (шаблон). ${created.length} ракурсов × 4 варианта.`,
        angles: created,
        botImplemented: false,
        aiGenerated: anyAiGenerated,
        model: anyAiGenerated ? model : undefined,
        ingredient: baseImagePath,  // Базовый образ — Image 1 для всех ракурсов
      });
    }
  });

  // ─── REWRITE REJECTED PROMPTS ────────────────────────────

  /**
   * POST /api/references/:id/references/rewrite-rejected
   * Body: { filter?: { characters: string[], locations: string[] }, model?: 'opus' | 'sonnet' }
   *
   * Rewrites prompts for all rejected items (filtered by selection).
   * Creates new attempts so the bot can regenerate.
   */
  router.post('/:id/references/rewrite-rejected', async (req, res) => {
    const project = store.get(req.params.id);
    if (!project) {
      res.status(404).json({ error: 'Проект не найден' });
      return;
    }

    const { filter, model = 'sonnet' } = req.body as {
      filter?: { characters: string[]; locations: string[] };
      model?: ModelChoice;
    };

    const paths = projectPaths(config.dataDir, project.id);
    const refsDir = resolve(paths.root, 'references');
    let rewrittenCount = 0;

    // Collect all rejected manifests
    const reviewItems = getRefReviewItems(refsDir, project);
    const rejected = reviewItems.filter((item) => item.manifest.status === 'rejected');

    for (const item of rejected) {
      // Apply filter
      if (filter) {
        if (item.type === 'characters' && !filter.characters.includes(item.itemId)) continue;
        if (item.type === 'locations' && !filter.locations.includes(item.itemId)) continue;
      }

      const manifest = item.manifest;
      const lastAttempt = manifest.attempts[manifest.attempts.length - 1];
      const originalPrompt = lastAttempt?.prompt || '';
      const feedback = manifest.feedback || '';

      if (!originalPrompt) continue;

      let newPrompt = originalPrompt;

      // Rewrite with Claude if feedback exists
      if (feedback.trim() && isClaudeAvailable(config)) {
        try {
          newPrompt = await rewritePromptWithFeedback(
            config, originalPrompt, feedback, item.type, model,
          );
        } catch (err) {
          console.warn('[references] Claude rewrite failed:', err);
        }
      }

      const newAttemptNum = (lastAttempt?.attempt || 0) + 1;
      manifest.attempts.push({
        attempt: newAttemptNum,
        prompt: newPrompt,
        variants: [],
      });
      manifest.status = 'generating';

      const target = item.target === 'base' ? 'base' : item.angleId || 'base';
      const newReviewDir = target === 'base'
        ? resolve(refsDir, item.type, item.itemId, 'review', 'base', `attempt_${newAttemptNum}`)
        : resolve(refsDir, item.type, item.itemId, 'review', 'angles', target, `attempt_${newAttemptNum}`);
      ensureDir(newReviewDir);

      saveRefManifest(refsDir, manifest);
      rewrittenCount++;
    }

    res.json({ success: true, rewrittenCount });
  });

  // ─── START BOT ──────────────────────────────────────────

  /**
   * POST /api/references/:id/references/start-bot
   * Body: { botCount?: number, accounts?: number[] }
   *
   * Starts one or more bots in --generate-refs mode for this project.
   * Tasks are distributed evenly across bots by index.
   */
  router.post('/:id/references/start-bot', (req, res) => {
    const project = store.get(req.params.id);
    if (!project) {
      res.status(404).json({ error: 'Проект не найден' });
      return;
    }

    const { botCount = 1, accounts = [1], filter } = req.body as {
      botCount?: number;
      accounts?: number[];
      filter?: { characters: string[]; locations: string[]; angles: string[] };
    };

    const manager = getBotManager(config);

    // Check if any ref bots are already running
    const refStatuses = manager.getRefBotStatuses();
    const runningBots = refStatuses.filter((b) => b.running);
    if (runningBots.length > 0) {
      res.status(409).json({
        error: `Уже запущено ${runningBots.length} бот(ов) для генерации референсов`,
      });
      return;
    }

    const projectDir = store.projectDir(req.params.id);

    if (botCount <= 1) {
      // Single bot mode (backward compatible)
      const account = accounts[0] || 1;
      const REF_BOT_ID = 99;
      const result = manager.startRefGeneration(REF_BOT_ID, account, projectDir, filter);
      if (result.success) {
        res.json({
          success: true,
          botIds: [REF_BOT_ID],
          message: 'Бот запущен для генерации референсов',
        });
      } else {
        res.status(400).json({ error: result.error });
      }
    } else {
      // Multi-bot mode
      const result = manager.startMultiRefGeneration(botCount, accounts, projectDir, filter);
      if (result.success) {
        res.json({
          success: true,
          botIds: result.botIds,
          message: `Запущено ${result.botIds.length} бот(ов) для генерации референсов`,
          errors: result.errors.length > 0 ? result.errors : undefined,
        });
      } else {
        res.status(400).json({
          error: 'Не удалось запустить ботов',
          details: result.errors,
        });
      }
    }
  });

  /**
   * POST /api/references/:id/references/stop-bot
   *
   * Stops all running reference generation bots.
   */
  router.post('/:id/references/stop-bot', (req, res) => {
    const manager = getBotManager(config);
    const refStatuses = manager.getRefBotStatuses();
    const runningBots = refStatuses.filter((b) => b.running);

    for (const bot of runningBots) {
      manager.stopBot(bot.botId);
    }

    res.json({
      success: true,
      stopped: runningBots.length,
      message: `Остановлено ${runningBots.length} бот(ов)`,
    });
  });

  /**
   * GET /api/references/:id/references/bot-status
   *
   * Returns the status of all reference generation bots.
   */
  router.get('/:id/references/bot-status', (req, res) => {
    const manager = getBotManager(config);
    const refStatuses = manager.getRefBotStatuses();

    if (refStatuses.length === 0) {
      res.json({ bots: [], running: false, started: false, totalCompleted: 0, totalErrors: 0 });
      return;
    }

    const anyRunning = refStatuses.some((b) => b.running);
    const totalCompleted = refStatuses.reduce((sum, b) => sum + b.completedCount, 0);
    const totalErrors = refStatuses.reduce((sum, b) => sum + b.errorCount, 0);

    res.json({
      bots: refStatuses,
      running: anyRunning,
      started: true,
      totalCompleted,
      totalErrors,
    });
  });

  // ─── REVIEW: GET ─────────────────────────────────────────

  /**
   * GET /api/setup/:id/references/review
   * Returns all reference items that have generated variants for review.
   */
  router.get('/:id/references/review', (req, res) => {
    const project = store.get(req.params.id);
    if (!project) {
      res.status(404).json({ error: 'Проект не найден' });
      return;
    }

    const paths = projectPaths(config.dataDir, project.id);
    const refsDir = resolve(paths.root, 'references');

    const items = getRefReviewItems(refsDir, project);

    res.json({ items });
  });

  // ─── REVIEW: SUBMIT ──────────────────────────────────────

  /**
   * POST /api/setup/:id/references/review/submit
   * Body: { decisions: RefReviewDecision[] }
   */
  router.post('/:id/references/review/submit', async (req, res) => {
    const project = store.get(req.params.id);
    if (!project) {
      res.status(404).json({ error: 'Проект не найден' });
      return;
    }

    const decisions: RefReviewDecision[] = req.body.decisions || [];
    const reviewModel: ModelChoice = req.body.model || 'sonnet';
    if (decisions.length === 0) {
      res.status(400).json({ error: 'Нет решений' });
      return;
    }

    const paths = projectPaths(config.dataDir, project.id);
    const refsDir = resolve(paths.root, 'references');

    const results: Array<{ itemId: string; target: string; success: boolean; error?: string }> = [];
    let acceptedCount = 0;
    let rejectedCount = 0;

    for (const decision of decisions) {
      const target = decision.target === 'base' ? 'base' : decision.angleId || 'base';

      const manifest = loadRefManifest(refsDir, decision.type, decision.itemId, target);
      if (!manifest) {
        results.push({
          itemId: decision.itemId,
          target,
          success: false,
          error: 'Манифест не найден',
        });
        continue;
      }

      if (decision.action === 'accept' && decision.attempt != null && decision.variant != null) {
        // Accept
        markRefAccepted(manifest, decision.attempt, decision.variant);
        saveRefManifest(refsDir, manifest);

        if (decision.target === 'base') {
          // Copy accepted base image
          const basePath = copyAcceptedBase(refsDir, manifest);

          // Update project.json
          if (decision.type === 'characters') {
            const char = project.characters.find((c) => c.id === decision.itemId);
            if (char && basePath) {
              char.baseImage = basePath;
              // If no angles yet, mark as base_review, otherwise keep current status
              if (char.status === 'pending' || char.status === 'base_review') {
                char.status = 'base_review';
              }
            }
          } else {
            const loc = project.locations.find((l) => l.id === decision.itemId);
            if (loc && basePath) {
              loc.baseImage = basePath;
              if (loc.status === 'pending' || loc.status === 'base_review') {
                loc.status = 'base_review';
              }
            }
          }
        } else if (decision.angleId) {
          // Copy accepted angle image
          const anglePath = copyAcceptedAngle(refsDir, manifest);

          // Update project.json angles array
          if (decision.type === 'characters') {
            const char = project.characters.find((c) => c.id === decision.itemId);
            if (char && anglePath) {
              const existing = char.angles.findIndex((a) => a.id === decision.angleId);
              const angleObj: Angle = {
                id: decision.angleId!,
                file: anglePath,
                description: decision.angleId!.replace(/_/g, ' '),
                type: getAngleType(decision.type, decision.angleId!),
                status: 'accepted',
              };
              if (existing >= 0) {
                char.angles[existing] = angleObj;
              } else {
                char.angles.push(angleObj);
              }

              // Check if all angles are ready
              const totalAngles = CHARACTER_ANGLE_TYPES.length;
              const acceptedAngles = char.angles.filter((a) => a.status === 'accepted').length;
              if (acceptedAngles >= totalAngles) {
                char.status = 'ready';
              } else {
                char.status = 'angles_review';
              }
            }
          } else {
            const loc = project.locations.find((l) => l.id === decision.itemId);
            if (loc && anglePath) {
              const existing = loc.angles.findIndex((a) => a.id === decision.angleId);
              const angleObj: Angle = {
                id: decision.angleId!,
                file: anglePath,
                description: decision.angleId!.replace(/_/g, ' '),
                type: getAngleType(decision.type, decision.angleId!),
                status: 'accepted',
              };
              if (existing >= 0) {
                loc.angles[existing] = angleObj;
              } else {
                loc.angles.push(angleObj);
              }

              // Check if all angles are ready
              const totalAngles = LOCATION_ANGLE_TYPES.length;
              const acceptedAngles = loc.angles.filter((a) => a.status === 'accepted').length;
              if (acceptedAngles >= totalAngles) {
                loc.status = 'ready';
              } else {
                loc.status = 'angles_review';
              }
            }
          }
        }

        acceptedCount++;
        results.push({ itemId: decision.itemId, target, success: true });
      } else if (decision.action === 'reject') {
        const feedback = decision.feedback || '';
        markRefRejected(manifest, feedback);
        manifest.status = 'rejected';
        saveRefManifest(refsDir, manifest);
        rejectedCount++;
        results.push({ itemId: decision.itemId, target, success: true });
      }
    }

    store.save(project);

    // Check if all references are ready
    const allReady =
      project.characters.every((c) => c.status === 'ready') &&
      project.locations.every((l) => l.status === 'ready');

    res.json({
      results,
      accepted: acceptedCount,
      rejected: rejectedCount,
      allReady,
    });
  });

  return router;
}

/** Определяет тип ракурса по ID */
function getAngleType(
  entityType: 'characters' | 'locations',
  angleId: string,
): 'wide' | 'medium' | 'closeup' | 'detail' | 'pov' {
  const angleTypes = entityType === 'characters' ? CHARACTER_ANGLE_TYPES : LOCATION_ANGLE_TYPES;
  const found = angleTypes.find((a) => a.id === angleId);
  return (found?.type || 'medium') as 'wide' | 'medium' | 'closeup' | 'detail' | 'pov';
}
