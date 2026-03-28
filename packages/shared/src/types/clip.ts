/** Один клип — минимальная единица мультфильма */
export interface Clip {
  clip_id: string;         // e.g. "SC001_A"
  scene_id: string;        // e.g. "SC001"
  scene_description_ru: string;
  nano_banana_ingredients: string[];  // пути к файлам референсов
  nano_banana_prompt_first: string;
  veo_prompt: string;
  veo_mode: 'frames' | 'image';
  veo_variant_count: number;
}

/** Статус компонента клипа */
export type ComponentStatus =
  | 'pending'      // ожидает генерации
  | 'generating'   // бот генерирует прямо сейчас
  | 'generated'    // варианты готовы, ждёт ревью
  | 'accepted'     // вариант принят
  | 'rejected'     // все варианты отклонены
  | 'skipped';     // пропущен

/** Названия компонентов */
export type ComponentName = 'nb_first' | 'veo';
