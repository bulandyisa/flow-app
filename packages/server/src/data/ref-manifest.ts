import { readFileSync, writeFileSync, existsSync, mkdirSync, copyFileSync, readdirSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import type { RefManifest, RefStatus, RefReviewItem } from '@flow-app/shared';
import type { Project, Character, Location } from '@flow-app/shared';

// ─── Paths ───────────────────────────────────────────────

/** Директория review для базового образа */
function baseReviewDir(refsDir: string, type: 'characters' | 'locations', itemId: string): string {
  return resolve(refsDir, type, itemId, 'review', 'base');
}

/** Директория review для ракурса */
function angleReviewDir(refsDir: string, type: 'characters' | 'locations', itemId: string, angleId: string): string {
  return resolve(refsDir, type, itemId, 'review', 'angles', angleId);
}

/** Путь к манифесту base */
function baseManifestPath(refsDir: string, type: 'characters' | 'locations', itemId: string): string {
  return resolve(baseReviewDir(refsDir, type, itemId), 'manifest.json');
}

/** Путь к манифесту ракурса */
function angleManifestPath(refsDir: string, type: 'characters' | 'locations', itemId: string, angleId: string): string {
  return resolve(angleReviewDir(refsDir, type, itemId, angleId), 'manifest.json');
}

// ─── CRUD ────────────────────────────────────────────────

/** Создаёт пустой RefManifest */
export function createRefManifest(
  itemId: string,
  type: 'characters' | 'locations',
  target: string,
): RefManifest {
  return {
    itemId,
    type,
    target,
    status: 'pending',
    feedback: '',
    attempts: [],
    selected_variant: null,
  };
}

/** Загружает манифест базового образа */
export function loadRefManifest(
  refsDir: string,
  type: 'characters' | 'locations',
  itemId: string,
  target: 'base' | string,
): RefManifest | null {
  const path = target === 'base'
    ? baseManifestPath(refsDir, type, itemId)
    : angleManifestPath(refsDir, type, itemId, target);

  if (!existsSync(path)) return null;
  return JSON.parse(readFileSync(path, 'utf-8'));
}

/** Сохраняет манифест */
export function saveRefManifest(
  refsDir: string,
  manifest: RefManifest,
): void {
  const dir = manifest.target === 'base'
    ? baseReviewDir(refsDir, manifest.type, manifest.itemId)
    : angleReviewDir(refsDir, manifest.type, manifest.itemId, manifest.target);

  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });

  const path = manifest.target === 'base'
    ? baseManifestPath(refsDir, manifest.type, manifest.itemId)
    : angleManifestPath(refsDir, manifest.type, manifest.itemId, manifest.target);

  writeFileSync(path, JSON.stringify(manifest, null, 2), 'utf-8');
}

/** Отмечает вариант как принятый */
export function markRefAccepted(
  manifest: RefManifest,
  attempt: number,
  variant: number,
): void {
  manifest.selected_variant = { attempt, variant };
  manifest.status = 'accepted';
}

/** Отмечает как отклонённый с фидбеком */
export function markRefRejected(
  manifest: RefManifest,
  feedback: string,
): void {
  manifest.status = 'pending';
  manifest.feedback = feedback;
  manifest.selected_variant = null;
}

// ─── Copy accepted ──────────────────────────────────────

/**
 * Копирует принятый вариант base в `<type>/<itemId>/base.png`.
 * Возвращает относительный путь `references/<type>/<itemId>/base.png`.
 */
export function copyAcceptedBase(
  refsDir: string,
  manifest: RefManifest,
): string | null {
  if (!manifest.selected_variant) return null;

  const { attempt, variant } = manifest.selected_variant;
  const attemptData = manifest.attempts.find((a) => a.attempt === attempt);
  if (!attemptData) return null;

  const variantFile = attemptData.variants[variant]?.file;
  if (!variantFile) return null;

  const srcPath = resolve(
    baseReviewDir(refsDir, manifest.type, manifest.itemId),
    `attempt_${attempt}`,
    variantFile,
  );
  if (!existsSync(srcPath)) return null;

  const destDir = resolve(refsDir, manifest.type, manifest.itemId);
  if (!existsSync(destDir)) mkdirSync(destDir, { recursive: true });

  const destFile = `${manifest.itemId}_base.png`;
  const destPath = resolve(destDir, destFile);
  copyFileSync(srcPath, destPath);

  return `references/${manifest.type}/${manifest.itemId}/${destFile}`;
}

/**
 * Копирует принятый вариант ракурса в `<type>/<itemId>/angles/<angleId>.png`.
 * Возвращает относительный путь `references/<type>/<itemId>/angles/<angleId>.png`.
 */
export function copyAcceptedAngle(
  refsDir: string,
  manifest: RefManifest,
): string | null {
  if (!manifest.selected_variant || manifest.target === 'base') return null;

  const { attempt, variant } = manifest.selected_variant;
  const attemptData = manifest.attempts.find((a) => a.attempt === attempt);
  if (!attemptData) return null;

  const variantFile = attemptData.variants[variant]?.file;
  if (!variantFile) return null;

  const srcPath = resolve(
    angleReviewDir(refsDir, manifest.type, manifest.itemId, manifest.target),
    `attempt_${attempt}`,
    variantFile,
  );
  if (!existsSync(srcPath)) return null;

  const destDir = resolve(refsDir, manifest.type, manifest.itemId, 'angles');
  if (!existsSync(destDir)) mkdirSync(destDir, { recursive: true });

  const destPath = resolve(destDir, `${manifest.target}.png`);
  copyFileSync(srcPath, destPath);

  return `references/${manifest.type}/${manifest.itemId}/angles/${manifest.target}.png`;
}

// ─── Scan for review items ──────────────────────────────

/**
 * Сканирует все референсы проекта и возвращает элементы, требующие ревью.
 */
export function getRefReviewItems(
  refsDir: string,
  project: Project,
): RefReviewItem[] {
  const items: RefReviewItem[] = [];

  // Персонажи
  for (const char of project.characters) {
    // Base
    const baseManifest = loadRefManifest(refsDir, 'characters', char.id, 'base');
    if (baseManifest && baseManifest.attempts.length > 0) {
      const paths = getVariantPaths(refsDir, 'characters', char.id, 'base', baseManifest);
      items.push({
        itemId: char.id,
        type: 'characters',
        name: char.name,
        nameRu: char.nameRu,
        target: 'base',
        manifest: baseManifest,
        variantPaths: paths,
      });
    }

    // Angles
    const anglesDir = resolve(refsDir, 'characters', char.id, 'review', 'angles');
    if (existsSync(anglesDir)) {
      const angleDirs = readdirSync(anglesDir, { withFileTypes: true })
        .filter((d) => d.isDirectory())
        .map((d) => d.name);

      for (const angleId of angleDirs) {
        const angleManifest = loadRefManifest(refsDir, 'characters', char.id, angleId);
        if (angleManifest && angleManifest.attempts.length > 0) {
          const paths = getVariantPaths(refsDir, 'characters', char.id, angleId, angleManifest);
          items.push({
            itemId: char.id,
            type: 'characters',
            name: char.name,
            nameRu: char.nameRu,
            target: 'angle',
            angleId,
            angleDescription: angleId.replace(/_/g, ' '),
            manifest: angleManifest,
            variantPaths: paths,
          });
        }
      }
    }
  }

  // Локации
  for (const loc of project.locations) {
    // Base
    const baseManifest = loadRefManifest(refsDir, 'locations', loc.id, 'base');
    if (baseManifest && baseManifest.attempts.length > 0) {
      const paths = getVariantPaths(refsDir, 'locations', loc.id, 'base', baseManifest);
      items.push({
        itemId: loc.id,
        type: 'locations',
        name: loc.name,
        nameRu: loc.nameRu,
        target: 'base',
        manifest: baseManifest,
        variantPaths: paths,
      });
    }

    // Angles
    const anglesDir = resolve(refsDir, 'locations', loc.id, 'review', 'angles');
    if (existsSync(anglesDir)) {
      const angleDirs = readdirSync(anglesDir, { withFileTypes: true })
        .filter((d) => d.isDirectory())
        .map((d) => d.name);

      for (const angleId of angleDirs) {
        const angleManifest = loadRefManifest(refsDir, 'locations', loc.id, angleId);
        if (angleManifest && angleManifest.attempts.length > 0) {
          const paths = getVariantPaths(refsDir, 'locations', loc.id, angleId, angleManifest);
          items.push({
            itemId: loc.id,
            type: 'locations',
            name: loc.name,
            nameRu: loc.nameRu,
            target: 'angle',
            angleId,
            angleDescription: angleId.replace(/_/g, ' '),
            manifest: angleManifest,
            variantPaths: paths,
          });
        }
      }
    }
  }

  return items;
}

/** Собирает пути к файлам вариантов последней попытки */
function getVariantPaths(
  refsDir: string,
  type: 'characters' | 'locations',
  itemId: string,
  target: string,
  manifest: RefManifest,
): string[] {
  if (manifest.attempts.length === 0) return [];

  const lastAttempt = manifest.attempts[manifest.attempts.length - 1];
  const reviewBase = target === 'base'
    ? baseReviewDir(refsDir, type, itemId)
    : angleReviewDir(refsDir, type, itemId, target);

  return lastAttempt.variants.map((v) =>
    `references/${type}/${itemId}/review/${target === 'base' ? 'base' : `angles/${target}`}/attempt_${lastAttempt.attempt}/${v.file}`,
  );
}
