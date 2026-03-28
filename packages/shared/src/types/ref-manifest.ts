import type { Variant, SelectedVariant } from './manifest.js';

/** Статус референса */
export type RefStatus = 'pending' | 'generating' | 'generated' | 'accepted' | 'rejected';

/** Попытка генерации референса (4 варианта) */
export interface RefAttempt {
  attempt: number;
  prompt: string;
  variants: Variant[];
}

/** Манифест для базового образа или одного ракурса */
export interface RefManifest {
  /** ID сущности (charId или locId) */
  itemId: string;
  /** "characters" | "locations" */
  type: 'characters' | 'locations';
  /** "base" для базового образа, или ID ракурса (e.g. "wide_front") */
  target: string;
  status: RefStatus;
  feedback: string;
  attempts: RefAttempt[];
  selected_variant: SelectedVariant | null;
}

/** Элемент для ревью на клиенте */
export interface RefReviewItem {
  itemId: string;
  type: 'characters' | 'locations';
  name: string;
  nameRu: string;
  target: 'base' | 'angle';
  angleId?: string;
  angleDescription?: string;
  manifest: RefManifest;
  variantPaths: string[];  // URL-пути к файлам вариантов
}

/** Решение по ревью референса */
export interface RefReviewDecision {
  itemId: string;
  type: 'characters' | 'locations';
  target: 'base' | 'angle';
  angleId?: string;
  action: 'accept' | 'reject';
  attempt?: number;
  variant?: number;
  feedback?: string;
}
