import type { Clip } from './types/clip.js';
import { VEO_MAX_LENGTH } from './constants.js';

export interface ValidationError {
  clipId: string;
  rule: string;
  message: string;
  severity: 'error' | 'warning';
}

/** Слова, запрещённые в промптах (физическая внешность) */
const FORBIDDEN_APPEARANCE = [
  'dark circles',
  'wrinkles',
  'scar',
  'eye color',
  'brown eyes',
  'green eyes',
  'blue eyes',
];

/** Слова возраста, запрещённые в VEO */
const FORBIDDEN_AGE = ['year-old', 'years old', 'teenage', 'elderly', 'middle-aged'];

/** Валидация одного клипа */
export function validateClip(clip: Clip, allClips: Clip[]): ValidationError[] {
  const errors: ValidationError[] = [];
  const { clip_id } = clip;

  // 1. Дубликаты clip_id
  const dupes = allClips.filter((c) => c.clip_id === clip_id);
  if (dupes.length > 1) {
    errors.push({ clipId: clip_id, rule: 'duplicate_id', message: 'Дубликат clip_id', severity: 'error' });
  }

  // 3. Пустые поля
  if (!clip.nano_banana_ingredients.length) {
    errors.push({ clipId: clip_id, rule: 'empty_ingredients', message: 'Нет ингредиентов', severity: 'error' });
  }
  if (!clip.nano_banana_prompt_first) {
    errors.push({ clipId: clip_id, rule: 'empty_first', message: 'Пустой промпт first', severity: 'error' });
  }
  if (!clip.veo_prompt) {
    errors.push({ clipId: clip_id, rule: 'empty_veo', message: 'Пустой промпт VEO', severity: 'error' });
  }

  // 4. VEO длина
  if (clip.veo_prompt && clip.veo_prompt.length > VEO_MAX_LENGTH) {
    errors.push({
      clipId: clip_id,
      rule: 'veo_length',
      message: `VEO промпт ${clip.veo_prompt.length} символов (макс ${VEO_MAX_LENGTH})`,
      severity: 'error',
    });
  }

  // 5. Физическая внешность
  const allText = clip.nano_banana_prompt_first;
  for (const word of FORBIDDEN_APPEARANCE) {
    if (allText.toLowerCase().includes(word)) {
      errors.push({
        clipId: clip_id,
        rule: 'forbidden_appearance',
        message: `Запрещённое описание внешности: "${word}"`,
        severity: 'error',
      });
    }
  }

  // 6. Возраст в VEO
  for (const word of FORBIDDEN_AGE) {
    if (clip.veo_prompt.toLowerCase().includes(word)) {
      errors.push({
        clipId: clip_id,
        rule: 'forbidden_age',
        message: `Возраст в VEO промпте: "${word}"`,
        severity: 'error',
      });
    }
  }

  // 8. Pixar-style в VEO
  if (clip.veo_prompt && !clip.veo_prompt.toLowerCase().includes('pixar')) {
    errors.push({
      clipId: clip_id,
      rule: 'missing_pixar',
      message: 'VEO промпт без "Pixar-style"',
      severity: 'error',
    });
  }

  // 12. veo_mode
  if (clip.veo_mode !== 'frames') {
    errors.push({ clipId: clip_id, rule: 'wrong_veo_mode', message: `veo_mode="${clip.veo_mode}", должен быть "frames"`, severity: 'error' });
  }

  return errors;
}

/** Валидация всех клипов */
export function validateAllClips(clips: Clip[]): ValidationError[] {
  const errors: ValidationError[] = [];

  // 2. SC continuity
  const sceneIds = [...new Set(clips.map((c) => c.scene_id))].sort();
  for (let i = 1; i < sceneIds.length; i++) {
    const prev = parseInt(sceneIds[i - 1].replace('SC', ''), 10);
    const curr = parseInt(sceneIds[i].replace('SC', ''), 10);
    if (curr !== prev + 1) {
      errors.push({
        clipId: sceneIds[i],
        rule: 'sc_gap',
        message: `Пропуск SC: ${sceneIds[i - 1]} → ${sceneIds[i]}`,
        severity: 'warning',
      });
    }
  }

  // 10. Ингредиенты внутри SC одинаковые
  const byScene = new Map<string, Clip[]>();
  for (const clip of clips) {
    const arr = byScene.get(clip.scene_id) || [];
    arr.push(clip);
    byScene.set(clip.scene_id, arr);
  }
  for (const [sceneId, sceneClips] of byScene) {
    if (sceneClips.length < 2) continue;
    const refIngredients = JSON.stringify(sceneClips[0].nano_banana_ingredients.sort());
    for (let i = 1; i < sceneClips.length; i++) {
      const currentIngredients = JSON.stringify(sceneClips[i].nano_banana_ingredients.sort());
      if (currentIngredients !== refIngredients) {
        errors.push({
          clipId: sceneClips[i].clip_id,
          rule: 'sc_ingredients_mismatch',
          message: `Ингредиенты отличаются от ${sceneClips[0].clip_id} в ${sceneId}`,
          severity: 'warning',
        });
      }
    }
  }

  // Per-clip validation
  for (const clip of clips) {
    errors.push(...validateClip(clip, clips));
  }

  return errors;
}
