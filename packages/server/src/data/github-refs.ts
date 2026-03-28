import { existsSync, mkdirSync, writeFileSync, readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import type { AppConfig } from '../config.js';
import type { Character, Location } from '@flow-app/shared';

const REFS_REPO = 'genvid25/flow-app-refs';
const API_BASE = 'https://api.github.com';

interface GithubFile {
  name: string;
  path: string;
  type: 'file' | 'dir';
  download_url: string | null;
}

interface RefMetadata {
  name: string;
  nameRu: string;
  clothing?: string;
  description: string;
}

/** Делает запрос к GitHub API */
async function ghFetch(path: string, token?: string): Promise<unknown> {
  const headers: Record<string, string> = { Accept: 'application/vnd.github.v3+json' };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { headers });
  if (!res.ok) {
    if (res.status === 404) return null;
    throw new Error(`GitHub API ${res.status}: ${await res.text()}`);
  }
  return res.json();
}

/** Скачивает файл по URL */
async function downloadFile(url: string, destPath: string, token?: string): Promise<void> {
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(url, { headers });
  if (!res.ok) throw new Error(`Download failed: ${res.status}`);

  const buffer = Buffer.from(await res.arrayBuffer());
  const dir = dirname(destPath);
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
  writeFileSync(destPath, buffer);
}

/** Получает список доступных персонажей в библиотеке */
export async function listLibraryCharacters(config: AppConfig): Promise<string[]> {
  const data = await ghFetch(`/repos/${REFS_REPO}/contents/characters`, config.githubToken) as GithubFile[] | null;
  if (!data) return [];
  return data.filter((f) => f.type === 'dir').map((f) => f.name);
}

/** Получает список доступных локаций в библиотеке */
export async function listLibraryLocations(config: AppConfig): Promise<string[]> {
  const data = await ghFetch(`/repos/${REFS_REPO}/contents/locations`, config.githubToken) as GithubFile[] | null;
  if (!data) return [];
  return data.filter((f) => f.type === 'dir').map((f) => f.name);
}

/** Скачивает персонажа из библиотеки в проект */
export async function downloadCharacter(
  config: AppConfig,
  charId: string,
  destDir: string,
): Promise<Character | null> {
  const token = config.githubToken || undefined;

  // Метаданные
  const metaData = await ghFetch(`/repos/${REFS_REPO}/contents/characters/${charId}/metadata.json`, token) as GithubFile | null;
  if (!metaData?.download_url) return null;

  const metaRes = await fetch(metaData.download_url, token ? { headers: { Authorization: `Bearer ${token}` } } : {});
  const meta: RefMetadata = await metaRes.json();

  // Создаём директории
  const charDir = resolve(destDir, charId);
  mkdirSync(resolve(charDir, 'angles'), { recursive: true });
  mkdirSync(resolve(charDir, 'review'), { recursive: true });

  // Базовый образ
  const baseFiles = await ghFetch(`/repos/${REFS_REPO}/contents/characters/${charId}`, token) as GithubFile[] | null;
  const baseFile = baseFiles?.find((f) => f.name.startsWith('base.'));
  let baseImage: string | null = null;

  if (baseFile?.download_url) {
    const ext = baseFile.name.split('.').pop();
    const destPath = resolve(charDir, `base.${ext}`);
    await downloadFile(baseFile.download_url, destPath, token);
    baseImage = `references/characters/${charId}/base.${ext}`;
  }

  // Ракурсы
  const anglesData = await ghFetch(`/repos/${REFS_REPO}/contents/characters/${charId}/angles`, token) as GithubFile[] | null;
  const angles = [];

  if (anglesData) {
    for (const file of anglesData) {
      if (file.type === 'file' && file.download_url) {
        const destPath = resolve(charDir, 'angles', file.name);
        await downloadFile(file.download_url, destPath, token);
        const id = file.name.replace(/\.[^.]+$/, '');
        angles.push({
          id,
          file: `references/characters/${charId}/angles/${file.name}`,
          description: id.replace(/_/g, ' '),
          type: 'wide' as const,
          status: 'accepted' as const,
        });
      }
    }
  }

  // Метаданные сохраняем тоже
  writeFileSync(resolve(charDir, 'metadata.json'), JSON.stringify(meta, null, 2));

  return {
    id: charId,
    name: meta.name,
    nameRu: meta.nameRu,
    clothing: meta.clothing || '',
    description: meta.description,
    baseImage,
    angles,
    status: baseImage ? (angles.length > 0 ? 'ready' : 'base_review') : 'pending',
  };
}

/** Скачивает локацию из библиотеки в проект */
export async function downloadLocation(
  config: AppConfig,
  locId: string,
  destDir: string,
): Promise<Location | null> {
  const token = config.githubToken || undefined;

  // Метаданные
  const metaData = await ghFetch(`/repos/${REFS_REPO}/contents/locations/${locId}/metadata.json`, token) as GithubFile | null;
  if (!metaData?.download_url) return null;

  const metaRes = await fetch(metaData.download_url, token ? { headers: { Authorization: `Bearer ${token}` } } : {});
  const meta: RefMetadata = await metaRes.json();

  // Создаём директории
  const locDir = resolve(destDir, locId);
  mkdirSync(resolve(locDir, 'angles'), { recursive: true });
  mkdirSync(resolve(locDir, 'review'), { recursive: true });

  // Базовый образ
  const baseFiles = await ghFetch(`/repos/${REFS_REPO}/contents/locations/${locId}`, token) as GithubFile[] | null;
  const baseFile = baseFiles?.find((f) => f.name.startsWith('base.'));
  let baseImage: string | null = null;

  if (baseFile?.download_url) {
    const ext = baseFile.name.split('.').pop();
    const destPath = resolve(locDir, `base.${ext}`);
    await downloadFile(baseFile.download_url, destPath, token);
    baseImage = `references/locations/${locId}/base.${ext}`;
  }

  // Ракурсы
  const anglesData = await ghFetch(`/repos/${REFS_REPO}/contents/locations/${locId}/angles`, token) as GithubFile[] | null;
  const angles = [];

  if (anglesData) {
    for (const file of anglesData) {
      if (file.type === 'file' && file.download_url) {
        const destPath = resolve(locDir, 'angles', file.name);
        await downloadFile(file.download_url, destPath, token);
        const id = file.name.replace(/\.[^.]+$/, '');
        angles.push({
          id,
          file: `references/locations/${locId}/angles/${file.name}`,
          description: id.replace(/_/g, ' '),
          type: 'wide' as const,
          status: 'accepted' as const,
        });
      }
    }
  }

  writeFileSync(resolve(locDir, 'metadata.json'), JSON.stringify(meta, null, 2));

  return {
    id: locId,
    name: meta.name,
    nameRu: meta.nameRu,
    description: meta.description,
    baseImage,
    angles,
    status: baseImage ? (angles.length >= 15 ? 'ready' : 'angles_review') : 'pending',
  };
}

/** Проверяет библиотеку и скачивает совпадения для проекта */
export async function matchAndDownloadRefs(
  config: AppConfig,
  characterIds: string[],
  locationIds: string[],
  projectRefsDir: string,
): Promise<{ characters: Character[]; locations: Location[]; notFound: { characters: string[]; locations: string[] } }> {
  const libChars = await listLibraryCharacters(config);
  const libLocs = await listLibraryLocations(config);

  const characters: Character[] = [];
  const locations: Location[] = [];
  const notFoundChars: string[] = [];
  const notFoundLocs: string[] = [];

  // Персонажи
  for (const charId of characterIds) {
    if (libChars.includes(charId)) {
      const char = await downloadCharacter(config, charId, resolve(projectRefsDir, 'characters'));
      if (char) characters.push(char);
      else notFoundChars.push(charId);
    } else {
      notFoundChars.push(charId);
    }
  }

  // Локации
  for (const locId of locationIds) {
    if (libLocs.includes(locId)) {
      const loc = await downloadLocation(config, locId, resolve(projectRefsDir, 'locations'));
      if (loc) locations.push(loc);
      else notFoundLocs.push(locId);
    } else {
      notFoundLocs.push(locId);
    }
  }

  return {
    characters,
    locations,
    notFound: { characters: notFoundChars, locations: notFoundLocs },
  };
}
