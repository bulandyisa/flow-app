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
  { id: 'wide_front', description: 'Wide establishing shot from the front', descriptionRu: 'Общий план спереди', type: 'wide' },
  { id: 'wide_left', description: 'Wide shot from the left side', descriptionRu: 'Общий план слева', type: 'wide' },
  { id: 'wide_right', description: 'Wide shot from the right side', descriptionRu: 'Общий план справа', type: 'wide' },
  { id: 'medium_from_door', description: 'Medium shot from the doorway', descriptionRu: 'Средний план от двери', type: 'medium' },
  { id: 'medium_from_window', description: 'Medium shot from the window side', descriptionRu: 'Средний план от окна', type: 'medium' },
  { id: 'medium_from_corner', description: 'Medium shot from the corner', descriptionRu: 'Средний план из угла', type: 'medium' },
  { id: 'closeup_detail_1', description: 'Close-up of a key detail', descriptionRu: 'Крупный план — деталь 1', type: 'closeup' },
  { id: 'closeup_detail_2', description: 'Close-up of another detail', descriptionRu: 'Крупный план — деталь 2', type: 'closeup' },
  { id: 'closeup_detail_3', description: 'Close-up of a third detail', descriptionRu: 'Крупный план — деталь 3', type: 'closeup' },
  { id: 'pov_inside_out', description: 'View from inside looking outward', descriptionRu: 'Вид изнутри наружу', type: 'pov' },
  { id: 'pov_outside_in', description: 'View from outside looking inward', descriptionRu: 'Вид снаружи внутрь', type: 'pov' },
  { id: 'low_angle', description: 'Low angle looking upward', descriptionRu: 'Нижний ракурс (снизу вверх)', type: 'detail' },
  { id: 'high_angle', description: 'High angle looking downward', descriptionRu: 'Верхний ракурс (сверху вниз)', type: 'detail' },
  { id: 'side_full', description: 'Full side view showing depth', descriptionRu: 'Полный боковой вид', type: 'wide' },
  { id: 'atmospheric', description: 'Atmospheric shot with dramatic lighting', descriptionRu: 'Атмосферный кадр с драматичным светом', type: 'detail' },
] as const;

/** Типы ракурсов для персонажей */
export const CHARACTER_ANGLE_TYPES = [
  { id: 'additional_1', description: 'Additional reference 1', descriptionRu: 'Дополнительный референс 1', type: 'wide' },
  { id: 'additional_2', description: 'Additional reference 2', descriptionRu: 'Дополнительный референс 2', type: 'wide' },
] as const;
