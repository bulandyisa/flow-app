import { existsSync, mkdirSync, readdirSync, statSync } from 'node:fs';
import { resolve, extname } from 'node:path';

/** Обеспечивает существование директории */
export function ensureDir(dir: string): void {
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
}

/** Возвращает список файлов в директории (не рекурсивно) */
export function listFiles(dir: string, extensions?: string[]): string[] {
  if (!existsSync(dir)) return [];
  return readdirSync(dir)
    .filter((f) => {
      if (extensions) {
        return extensions.includes(extname(f).toLowerCase());
      }
      return !statSync(resolve(dir, f)).isDirectory();
    })
    .sort();
}

/** Пути внутри проекта */
export function projectPaths(dataDir: string, projectId: string) {
  const root = resolve(dataDir, 'projects', projectId);
  return {
    root,
    screenplay: resolve(root, 'screenplay.docx'),
    prompts: resolve(root, 'prompts', 'all_prompts.json'),
    characters: resolve(root, 'references', 'characters'),
    locations: resolve(root, 'references', 'locations'),
    review: resolve(root, 'review'),
    frames: resolve(root, 'frames'),
    clips: resolve(root, 'clips'),
    characterDir: (charId: string) => resolve(root, 'references', 'characters', charId),
    locationDir: (locId: string) => resolve(root, 'references', 'locations', locId),
  };
}
