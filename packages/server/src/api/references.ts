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

/** Генерирует промпт для базового образа */
function basePrompt(type: 'characters' | 'locations', name: string, description: string): string {
  if (type === 'characters') {
    return `Full body shot of ${description}. Front view, neutral pose, clear details. No text, no watermarks. 3D Pixar-style, family-friendly, cinematic.`;
  }
  return `${description}. Wide establishing shot showing the full location. Clear details, consistent lighting. No text, no watermarks. 3D Pixar-style, family-friendly, cinematic.`;
}

/** Генерирует промпт для ракурса (с инструкцией по консистентности) */
function anglePrompt(type: 'characters' | 'locations', angleDescription: string): string {
  if (type === 'characters') {
    return `The EXACT same character from Image 1 — same face, same body proportions, same clothing, same hairstyle, same accessories. IDENTICAL appearance. Pose: ${angleDescription}. No text, no watermarks. 3D Pixar-style, family-friendly, cinematic.`;
  }
  return `Reproduce the EXACT same location from Image 1 — same walls, same floor, same furniture, same objects, same colors, same textures, same lighting. NOTHING added, NOTHING removed, NOTHING changed. Camera angle: ${angleDescription}. The location must be IDENTICAL to Image 1 in every detail. Only the camera position and angle change. No text, no watermarks. 3D Pixar-style, family-friendly, cinematic.`;
}
import type { RefReviewDecision, Angle } from '@flow-app/shared';

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
  router.post('/:id/references/generate', (req, res) => {
    const project = store.get(req.params.id);
    if (!project) {
      res.status(404).json({ error: 'Проект не найден' });
      return;
    }

    const { type, itemId, target } = req.body as {
      type: 'characters' | 'locations';
      itemId: string;
      target: 'base' | 'angles';
    };

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
      const prompt = basePrompt(type, item?.name || itemId, description);

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
        message: 'Генерация базового образа запущена. Бот сгенерирует 4 варианта.',
        botImplemented: false,
        prompt,
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

      for (const angleType of angleTypes) {
        let manifest = loadRefManifest(refsDir, type, itemId, angleType.id);
        if (!manifest) {
          manifest = createRefManifest(itemId, type, angleType.id);
        }
        if (manifest.status !== 'accepted') {
          const prompt = anglePrompt(type, angleType.description);
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
        message: `Генерация ракурсов запущена. ${created.length} ракурсов × 4 варианта.`,
        angles: created,
        botImplemented: false,
        ingredient: baseImagePath,  // Базовый образ — Image 1 для всех ракурсов
      });
    }
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
  router.post('/:id/references/review/submit', (req, res) => {
    const project = store.get(req.params.id);
    if (!project) {
      res.status(404).json({ error: 'Проект не найден' });
      return;
    }

    const decisions: RefReviewDecision[] = req.body.decisions || [];
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
        // Reject with feedback
        markRefRejected(manifest, decision.feedback || '');
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
