/** Ракурс (для локации или персонажа) */
export interface Angle {
  id: string;           // e.g. "wide_front"
  file: string;         // путь к принятому файлу
  description: string;  // "Wide shot from the front"
  type: 'wide' | 'medium' | 'closeup' | 'detail' | 'pov';
  status: 'pending' | 'generating' | 'review' | 'accepted';
}

/** Персонаж проекта */
export interface Character {
  id: string;           // e.g. "amin"
  name: string;         // "Amin"
  nameRu: string;       // "Амин"
  clothing: string;     // "in the grey hoodie"
  description: string;  // описание для Claude
  baseImage: string | null;  // путь к принятому базовому образу
  angles: Angle[];
  status: 'pending' | 'base_review' | 'angles_review' | 'ready';
}

/** Локация проекта */
export interface Location {
  id: string;           // e.g. "porch"
  name: string;         // "Old porch"
  nameRu: string;       // "Крыльцо"
  description: string;  // описание для Claude
  baseImage: string | null;  // путь к принятой базовой локации
  angles: Angle[];      // 15+ ракурсов
  status: 'pending' | 'base_review' | 'angles_review' | 'ready';
}

/** Мизансцена — кто где сидит/стоит */
export interface Seating {
  [locationId: string]: {
    [characterName: string]: string;  // "at the head of the table"
  };
}

/** Этап проекта */
export type ProjectPhase =
  | 'screenplay'     // загрузка сценария
  | 'references'     // генерация/ревью референсов
  | 'prompts'        // генерация/проверка промптов
  | 'production'     // генерация кадров/видео
  | 'complete';      // всё готово

/** Проект — один мультфильм */
export interface Project {
  id: string;
  name: string;
  nameRu: string;
  style: string;          // "3D Pixar-style"
  phase: ProjectPhase;
  characters: Character[];
  locations: Location[];
  seating: Seating;
  screenplayFile: string | null;
  createdAt: string;      // ISO date
  updatedAt: string;
}
