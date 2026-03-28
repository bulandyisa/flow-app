import type { ComponentName, ComponentStatus } from './clip.js';

/** Один вариант генерации */
export interface Variant {
  file: string;
  scores: Record<string, number> | null;
  avg: number | null;
}

/** Одна попытка генерации (4 варианта) */
export interface Attempt {
  attempt: number;
  prompt: string;
  variants: Variant[];
  best_variant: number | null;
  best_avg: number | null;
}

/** Выбранный вариант */
export interface SelectedVariant {
  attempt: number;
  variant: number;
}

/** Состояние одного компонента клипа */
export interface ComponentState {
  attempts: Attempt[];
  selected_variant_a: SelectedVariant | null;
  status: ComponentStatus;
  feedback: string;
}

/** Манифест клипа — полное состояние генерации */
export interface Manifest {
  clip_id: string;
  components: Record<ComponentName, ComponentState>;
}
