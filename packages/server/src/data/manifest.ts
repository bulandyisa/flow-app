import { readFileSync, writeFileSync, existsSync, mkdirSync, copyFileSync, renameSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { randomBytes } from 'node:crypto';
import type { Manifest, ComponentName, ComponentState } from '@flow-app/shared';

/** Создаёт пустое состояние компонента */
function emptyComponent(): ComponentState {
  return {
    attempts: [],
    selected_variant_a: null,
    status: 'pending',
    feedback: '',
  };
}

/** Создаёт пустой манифест */
export function createManifest(clipId: string): Manifest {
  return {
    clip_id: clipId,
    components: {
      nb_first: emptyComponent(),
      veo: emptyComponent(),
    },
  };
}

/** Загружает манифест из файла */
export function loadManifest(reviewDir: string, clipId: string): Manifest | null {
  const file = resolve(reviewDir, clipId, 'manifest.json');
  if (!existsSync(file)) return null;
  return JSON.parse(readFileSync(file, 'utf-8'));
}

/** Сохраняет манифест (атомарно: write to temp → rename) */
export function saveManifest(reviewDir: string, manifest: Manifest): void {
  const dir = resolve(reviewDir, manifest.clip_id);
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
  const target = resolve(dir, 'manifest.json');
  const tmp = target + '.' + randomBytes(4).toString('hex') + '.tmp';
  writeFileSync(tmp, JSON.stringify(manifest, null, 2), 'utf-8');
  renameSync(tmp, target);
}

/** Отмечает вариант как принятый */
export function markAccepted(
  manifest: Manifest,
  component: ComponentName,
  attempt: number,
  variant: number,
  scores: Record<string, number> | null,
): void {
  const comp = manifest.components[component];
  comp.selected_variant_a = { attempt, variant };
  comp.status = 'accepted';

  // Обновляем скоры варианта
  const attemptData = comp.attempts.find((a) => a.attempt === attempt);
  if (attemptData && scores) {
    const v = attemptData.variants[variant];
    if (v) {
      v.scores = scores;
      v.avg = Object.values(scores).reduce((s, n) => s + n, 0) / Object.values(scores).length;
    }
  }
}

/** Отмечает компонент как отклонённый с фидбеком */
export function markRejected(manifest: Manifest, component: ComponentName, feedback: string): void {
  const comp = manifest.components[component];
  comp.status = 'pending';
  comp.feedback = feedback;
  comp.selected_variant_a = null;
}

/** Копирует принятый вариант в папку frames/clips */
export function copyAcceptedToOutput(
  reviewDir: string,
  outputDir: string,
  manifest: Manifest,
  component: ComponentName,
): string | null {
  const comp = manifest.components[component];
  if (!comp.selected_variant_a) return null;

  const { attempt, variant } = comp.selected_variant_a;
  const attemptData = comp.attempts.find((a) => a.attempt === attempt);
  if (!attemptData) return null;

  const variantFile = attemptData.variants[variant]?.file;
  if (!variantFile) return null;

  const srcPath = resolve(reviewDir, manifest.clip_id, component, `attempt_${attempt}`, variantFile);
  if (!existsSync(srcPath)) return null;

  const isVideo = component === 'veo';
  const destDir = resolve(outputDir, isVideo ? 'clips' : 'frames');
  if (!existsSync(destDir)) mkdirSync(destDir, { recursive: true });

  const suffix = component === 'nb_first' ? '_first' : '_clip';
  const ext = isVideo ? '.mp4' : '.png';
  const destPath = resolve(destDir, `${manifest.clip_id}${suffix}${ext}`);

  copyFileSync(srcPath, destPath);
  return destPath;
}
