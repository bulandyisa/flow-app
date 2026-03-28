/** Компоненты в порядке chain workflow */
export const CHAIN_ORDER = ['nb_first', 'veo'] as const;

/** Количество вариантов по умолчанию */
export const DEFAULT_VARIANT_COUNT = 4;

/** Максимальная длина VEO промпта */
export const VEO_MAX_LENGTH = 350;

/** Клипов на страницу в ревью */
export const CLIPS_PER_PAGE = 40;

/** Минимум ракурсов на локацию */
export const MIN_LOCATION_ANGLES = 15;

/** Типы ракурсов для генерации локаций */
export const LOCATION_ANGLE_TYPES = [
  { id: 'wide_front', description: 'Wide establishing shot from the front', type: 'wide' },
  { id: 'wide_left', description: 'Wide shot from the left side', type: 'wide' },
  { id: 'wide_right', description: 'Wide shot from the right side', type: 'wide' },
  { id: 'medium_from_door', description: 'Medium shot from the doorway', type: 'medium' },
  { id: 'medium_from_window', description: 'Medium shot from the window side', type: 'medium' },
  { id: 'medium_from_corner', description: 'Medium shot from the corner', type: 'medium' },
  { id: 'closeup_detail_1', description: 'Close-up of a key detail', type: 'closeup' },
  { id: 'closeup_detail_2', description: 'Close-up of another detail', type: 'closeup' },
  { id: 'closeup_detail_3', description: 'Close-up of a third detail', type: 'closeup' },
  { id: 'pov_inside_out', description: 'View from inside looking outward', type: 'pov' },
  { id: 'pov_outside_in', description: 'View from outside looking inward', type: 'pov' },
  { id: 'low_angle', description: 'Low angle looking upward', type: 'detail' },
  { id: 'high_angle', description: 'High angle looking downward', type: 'detail' },
  { id: 'side_full', description: 'Full side view showing depth', type: 'wide' },
  { id: 'atmospheric', description: 'Atmospheric shot with dramatic lighting', type: 'detail' },
] as const;

/** Типы ракурсов для персонажей */
export const CHARACTER_ANGLE_TYPES = [
  { id: 'full_front', description: 'Full body, front view', type: 'wide' },
  { id: 'full_profile', description: 'Full body, profile (3/4 view)', type: 'wide' },
  { id: 'face_closeup', description: 'Face close-up, front', type: 'closeup' },
  { id: 'sitting', description: 'Sitting pose', type: 'medium' },
  { id: 'walking', description: 'Walking/in motion', type: 'medium' },
] as const;
