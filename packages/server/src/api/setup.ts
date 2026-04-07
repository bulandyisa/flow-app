import { Router } from 'express';
import multer from 'multer';
import { copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve, extname, join } from 'node:path';
import { tmpdir } from 'node:os';
import type { AppConfig } from '../config.js';
import { ProjectStore } from '../data/project-store.js';
import { parseDocx } from '../data/docx-parser.js';
import { projectPaths, ensureDir } from '../data/file-manager.js';
import { LOC_RU } from '../data/location-names.js';
import { analyzeScreenplay } from '../ai/screenplay.js';
import { generateScenePrompts } from '../ai/prompts.js';
import { matchAndDownloadRefs } from '../data/github-refs.js';
import { parseIngredientsFromPrompts } from '../data/parse-ingredients.js';
import type { Character, Location, Clip } from '@flow-app/shared';

const upload = multer({ dest: join(tmpdir(), 'flow-app-uploads') });

export function setupRouter(config: AppConfig): Router {
  const router = Router();
  const store = new ProjectStore(config.dataDir);

  // ─── СЦЕНАРИЙ ──────────────────────────────────────────

  // POST /api/projects/:id/screenplay — загрузить .docx
  router.post('/:id/screenplay', upload.single('file'), async (req, res) => {
    const project = store.get(req.params.id as string);
    if (!project) { res.status(404).json({ error: 'Проект не найден' }); return; }
    if (!req.file) { res.status(400).json({ error: 'Файл не загружен' }); return; }

    const paths = projectPaths(config.dataDir, project.id);

    // Копируем файл в директорию проекта
    copyFileSync(req.file.path, paths.screenplay);

    // Парсим
    const parsed = await parseDocx(paths.screenplay);

    // Обновляем проект
    project.screenplayFile = 'screenplay.docx';
    project.phase = 'references';
    store.save(project);

    res.json({
      success: true,
      text: parsed.text,
      paragraphs: parsed.paragraphs,
      paragraphCount: parsed.paragraphs.length,
    });
  });

  // GET /api/projects/:id/screenplay — получить текст сценария
  router.get('/:id/screenplay', async (req, res) => {
    const project = store.get(req.params.id as string);
    if (!project) { res.status(404).json({ error: 'Проект не найден' }); return; }

    const paths = projectPaths(config.dataDir, project.id);
    if (!existsSync(paths.screenplay)) {
      res.status(404).json({ error: 'Сценарий не загружен' });
      return;
    }

    const parsed = await parseDocx(paths.screenplay);
    res.json({ text: parsed.text, paragraphs: parsed.paragraphs });
  });

  // ─── ПЕРСОНАЖИ ─────────────────────────────────────────

  // POST /api/projects/:id/characters — добавить персонажа
  router.post('/:id/characters', upload.single('image'), (req, res) => {
    const project = store.get(req.params.id as string);
    if (!project) { res.status(404).json({ error: 'Проект не найден' }); return; }

    const { name, nameRu, clothing, description } = req.body;
    if (!name) { res.status(400).json({ error: 'Имя персонажа обязательно' }); return; }

    const charId = name.toLowerCase().replace(/\s+/g, '_');
    const paths = projectPaths(config.dataDir, project.id);
    const charDir = paths.characterDir(charId);
    ensureDir(charDir);
    ensureDir(resolve(charDir, 'angles'));
    ensureDir(resolve(charDir, 'review'));

    // Сохраняем изображение если загружено
    let baseImage: string | null = null;
    if (req.file) {
      const ext = extname(req.file.originalname) || '.png';
      const destFile = `${charId}_base${ext}`;
      copyFileSync(req.file.path, resolve(charDir, destFile));
      baseImage = `references/characters/${charId}/${destFile}`;
    }

    const character: Character = {
      id: charId,
      name: name,
      nameRu: nameRu || name,
      clothing: clothing || '',
      description: description || '',
      baseImage,
      angles: [],
      status: baseImage ? 'base_review' : 'pending',
    };

    // Добавляем или обновляем в проекте
    const idx = project.characters.findIndex((c) => c.id === charId);
    if (idx >= 0) {
      project.characters[idx] = { ...project.characters[idx], ...character };
    } else {
      project.characters.push(character);
    }
    store.save(project);

    res.status(201).json(character);
  });

  // DELETE /api/projects/:id/characters/:charId
  router.delete('/:id/characters/:charId', (req, res) => {
    const project = store.get(req.params.id as string);
    if (!project) { res.status(404).json({ error: 'Проект не найден' }); return; }

    project.characters = project.characters.filter((c) => c.id !== req.params.charId as string);
    store.save(project);

    res.json({ success: true });
  });

  // PATCH /api/projects/:id/characters/:charId — обновить данные персонажа
  router.patch('/:id/characters/:charId', (req, res) => {
    const project = store.get(req.params.id as string);
    if (!project) { res.status(404).json({ error: 'Проект не найден' }); return; }

    const char = project.characters.find((c) => c.id === req.params.charId as string);
    if (!char) { res.status(404).json({ error: 'Персонаж не найден' }); return; }

    const { name, nameRu, clothing, description } = req.body;
    if (name !== undefined) char.name = name;
    if (nameRu !== undefined) char.nameRu = nameRu;
    if (clothing !== undefined) char.clothing = clothing;
    if (description !== undefined) char.description = description;

    store.save(project);
    res.json(char);
  });

  // POST /api/projects/:id/characters/:charId/image — загрузить/обновить фото
  router.post('/:id/characters/:charId/image', upload.single('image'), (req, res) => {
    const project = store.get(req.params.id as string);
    if (!project) { res.status(404).json({ error: 'Проект не найден' }); return; }
    if (!req.file) { res.status(400).json({ error: 'Файл не загружен' }); return; }

    const char = project.characters.find((c) => c.id === req.params.charId as string);
    if (!char) { res.status(404).json({ error: 'Персонаж не найден' }); return; }

    const paths = projectPaths(config.dataDir, project.id);
    const charDir = paths.characterDir(char.id);
    ensureDir(charDir);

    const ext = extname(req.file.originalname) || '.png';
    const destFile = `${char.id}_base${ext}`;
    copyFileSync(req.file.path, resolve(charDir, destFile));

    char.baseImage = `references/characters/${char.id}/${destFile}`;
    char.status = 'base_review';
    store.save(project);

    res.json({ success: true, baseImage: char.baseImage });
  });

  // ─── ЛОКАЦИИ ───────────────────────────────────────────

  // POST /api/projects/:id/locations — добавить локацию
  router.post('/:id/locations', upload.single('image'), (req, res) => {
    const project = store.get(req.params.id as string);
    if (!project) { res.status(404).json({ error: 'Проект не найден' }); return; }

    const { name, nameRu, description } = req.body;
    if (!name) { res.status(400).json({ error: 'Название локации обязательно' }); return; }

    const locId = name.toLowerCase().replace(/\s+/g, '_');
    const paths = projectPaths(config.dataDir, project.id);
    const locDir = paths.locationDir(locId);
    ensureDir(locDir);
    ensureDir(resolve(locDir, 'angles'));
    ensureDir(resolve(locDir, 'review'));

    let baseImage: string | null = null;
    if (req.file) {
      const ext = extname(req.file.originalname) || '.png';
      const destFile = `base${ext}`;
      copyFileSync(req.file.path, resolve(locDir, destFile));
      baseImage = `references/locations/${locId}/${destFile}`;
    }

    const location: Location = {
      id: locId,
      name,
      nameRu: nameRu || name,
      description: description || '',
      baseImage,
      angles: [],
      status: baseImage ? 'base_review' : 'pending',
    };

    const idx = project.locations.findIndex((l) => l.id === locId);
    if (idx >= 0) {
      project.locations[idx] = { ...project.locations[idx], ...location };
    } else {
      project.locations.push(location);
    }
    store.save(project);

    res.status(201).json(location);
  });

  // DELETE /api/projects/:id/locations/:locId
  router.delete('/:id/locations/:locId', (req, res) => {
    const project = store.get(req.params.id as string);
    if (!project) { res.status(404).json({ error: 'Проект не найден' }); return; }

    project.locations = project.locations.filter((l) => l.id !== req.params.locId as string);
    store.save(project);

    res.json({ success: true });
  });

  // PATCH /api/projects/:id/locations/:locId
  router.patch('/:id/locations/:locId', (req, res) => {
    const project = store.get(req.params.id as string);
    if (!project) { res.status(404).json({ error: 'Проект не найден' }); return; }

    const loc = project.locations.find((l) => l.id === req.params.locId as string);
    if (!loc) { res.status(404).json({ error: 'Локация не найдена' }); return; }

    const { name, nameRu, description } = req.body;
    if (name !== undefined) loc.name = name;
    if (nameRu !== undefined) loc.nameRu = nameRu;
    if (description !== undefined) loc.description = description;

    store.save(project);
    res.json(loc);
  });

  // POST /api/projects/:id/locations/:locId/image — загрузить фото
  router.post('/:id/locations/:locId/image', upload.single('image'), (req, res) => {
    const project = store.get(req.params.id as string);
    if (!project) { res.status(404).json({ error: 'Проект не найден' }); return; }
    if (!req.file) { res.status(400).json({ error: 'Файл не загружен' }); return; }

    const loc = project.locations.find((l) => l.id === req.params.locId as string);
    if (!loc) { res.status(404).json({ error: 'Локация не найдена' }); return; }

    const paths = projectPaths(config.dataDir, project.id);
    const locDir = paths.locationDir(loc.id);
    ensureDir(locDir);

    const ext = extname(req.file.originalname) || '.png';
    const destFile = `${loc.id}_base${ext}`;
    copyFileSync(req.file.path, resolve(locDir, destFile));

    loc.baseImage = `references/locations/${loc.id}/${destFile}`;
    loc.status = 'base_review';
    store.save(project);

    res.json({ success: true, baseImage: loc.baseImage });
  });

  // POST /api/projects/:id/characters/:charId/angles — загрузить ракурс персонажа
  router.post('/:id/characters/:charId/angles', upload.single('image'), (req, res) => {
    const project = store.get(req.params.id as string);
    if (!project) { res.status(404).json({ error: 'Проект не найден' }); return; }
    if (!req.file) { res.status(400).json({ error: 'Файл не загружен' }); return; }

    const char = project.characters.find((c) => c.id === req.params.charId as string);
    if (!char) { res.status(404).json({ error: 'Персонаж не найден' }); return; }

    const angleId = req.body.angleId as string;
    if (!angleId) { res.status(400).json({ error: 'angleId обязателен' }); return; }

    const paths = projectPaths(config.dataDir, project.id);
    const anglesDir = resolve(paths.characterDir(char.id), 'angles');
    ensureDir(anglesDir);

    const ext = extname(req.file.originalname) || '.png';
    const destFile = `${angleId}${ext}`;
    copyFileSync(req.file.path, resolve(anglesDir, destFile));

    const anglePath = `references/characters/${char.id}/angles/${destFile}`;
    const existing = char.angles.findIndex((a) => a.id === angleId);
    if (existing >= 0) {
      char.angles[existing].file = anglePath;
      char.angles[existing].status = 'accepted';
    } else {
      char.angles.push({ id: angleId, file: anglePath, description: angleId, type: 'detail', status: 'accepted' });
    }
    store.save(project);

    res.json({ success: true, anglePath });
  });

  // POST /api/projects/:id/locations/:locId/angles — загрузить ракурс локации
  router.post('/:id/locations/:locId/angles', upload.single('image'), (req, res) => {
    const project = store.get(req.params.id as string);
    if (!project) { res.status(404).json({ error: 'Проект не найден' }); return; }
    if (!req.file) { res.status(400).json({ error: 'Файл не загружен' }); return; }

    const loc = project.locations.find((l) => l.id === req.params.locId as string);
    if (!loc) { res.status(404).json({ error: 'Локация не найдена' }); return; }

    const angleId = req.body.angleId as string;
    if (!angleId) { res.status(400).json({ error: 'angleId обязателен' }); return; }

    const paths = projectPaths(config.dataDir, project.id);
    const anglesDir = resolve(paths.locationDir(loc.id), 'angles');
    ensureDir(anglesDir);

    const ext = extname(req.file.originalname) || '.png';
    const destFile = `${angleId}${ext}`;
    copyFileSync(req.file.path, resolve(anglesDir, destFile));

    const anglePath = `references/locations/${loc.id}/angles/${destFile}`;
    const existing = loc.angles.findIndex((a) => a.id === angleId);
    if (existing >= 0) {
      loc.angles[existing].file = anglePath;
      loc.angles[existing].status = 'accepted';
    } else {
      loc.angles.push({ id: angleId, file: anglePath, description: angleId, type: 'detail', status: 'accepted' });
    }
    store.save(project);

    res.json({ success: true, anglePath });
  });

  // ─── АНАЛИЗ СЦЕНАРИЯ (Claude API) ───────────────────────

  // POST /api/setup/:id/analyze — Claude анализирует сценарий
  router.post('/:id/analyze', async (req, res) => {
    const project = store.get(req.params.id as string);
    if (!project) { res.status(404).json({ error: 'Проект не найден' }); return; }

    const paths = projectPaths(config.dataDir, project.id);
    if (!existsSync(paths.screenplay)) {
      res.status(400).json({ error: 'Сценарий не загружен' });
      return;
    }

    try {
      const parsed = await parseDocx(paths.screenplay);
      const analysis = await analyzeScreenplay(config, parsed.text);

      // Добавляем извлечённых персонажей (если ещё нет)
      for (const char of analysis.characters) {
        const charId = char.name.toLowerCase().replace(/\s+/g, '_');
        if (!project.characters.find((c) => c.id === charId)) {
          const charDir = paths.characterDir(charId);
          ensureDir(charDir);
          ensureDir(resolve(charDir, 'angles'));
          ensureDir(resolve(charDir, 'review'));

          project.characters.push({
            id: charId,
            name: char.name,
            nameRu: char.nameRu,
            clothing: char.clothing,
            description: char.description,
            baseImage: null,
            angles: [],
            status: 'pending',
          });
        }
      }

      // Добавляем извлечённые локации (если ещё нет)
      for (const loc of analysis.locations) {
        const locId = loc.name.toLowerCase().replace(/\s+/g, '_');
        if (!project.locations.find((l) => l.id === locId)) {
          const locDir = paths.locationDir(locId);
          ensureDir(locDir);
          ensureDir(resolve(locDir, 'angles'));
          ensureDir(resolve(locDir, 'review'));

          project.locations.push({
            id: locId,
            name: loc.name,
            nameRu: loc.nameRu,
            description: loc.description,
            baseImage: null,
            angles: [],
            status: 'pending',
          });
        }
      }

      // Проверяем библиотеку GitHub и скачиваем совпадения
      const charIds = project.characters.filter((c) => !c.baseImage).map((c) => c.id);
      const locIds = project.locations.filter((l) => !l.baseImage).map((l) => l.id);
      let libraryResult = { characters: [] as Character[], locations: [] as Location[], notFound: { characters: charIds, locations: locIds } };

      if (config.githubToken) {
        try {
          libraryResult = await matchAndDownloadRefs(config, charIds, locIds, resolve(paths.root, 'references'));

          // Обновляем персонажей, найденных в библиотеке
          for (const libChar of libraryResult.characters) {
            const idx = project.characters.findIndex((c) => c.id === libChar.id);
            if (idx >= 0) {
              project.characters[idx] = libChar;
            }
          }

          // Обновляем локации, найденные в библиотеке
          for (const libLoc of libraryResult.locations) {
            const idx = project.locations.findIndex((l) => l.id === libLoc.id);
            if (idx >= 0) {
              project.locations[idx] = libLoc;
            }
          }
        } catch (libErr) {
          console.error('GitHub library check failed:', libErr);
          // Не критично — продолжаем без библиотеки
        }
      }

      project.phase = 'references';
      store.save(project);

      res.json({
        success: true,
        analysis,
        characters: project.characters,
        locations: project.locations,
        fromLibrary: {
          characters: libraryResult.characters.map((c) => c.id),
          locations: libraryResult.locations.map((l) => l.id),
        },
        notFound: libraryResult.notFound,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      res.status(500).json({ error: message });
    }
  });

  // ─── ГЕНЕРАЦИЯ ПРОМПТОВ (Claude API) ──────────────────────

  // POST /api/setup/:id/generate-prompts — генерация промптов из сценария
  router.post('/:id/generate-prompts', async (req, res) => {
    const project = store.get(req.params.id as string);
    if (!project) { res.status(404).json({ error: 'Проект не найден' }); return; }

    if (!config.anthropicApiKey) {
      res.status(400).json({ error: 'Claude API ключ не настроен. Добавьте его в настройках.' });
      return;
    }

    const paths = projectPaths(config.dataDir, project.id);
    if (!existsSync(paths.screenplay)) {
      res.status(400).json({ error: 'Сценарий не загружен' });
      return;
    }

    if (project.characters.length === 0) {
      res.status(400).json({ error: 'Нет персонажей. Добавьте персонажей перед генерацией.' });
      return;
    }

    if (project.locations.length === 0) {
      res.status(400).json({ error: 'Нет локаций. Добавьте локации перед генерацией.' });
      return;
    }

    try {
      const parsed = await parseDocx(paths.screenplay);

      // Разделяем на сцены по двойным переносам строк или заголовкам
      const sceneTexts = splitIntoScenes(parsed.text);
      const allClips: Clip[] = [];
      let nextSC = 1;

      for (let i = 0; i < sceneTexts.length; i++) {
        const sceneText = sceneTexts[i];
        if (!sceneText.trim()) continue;

        const clips = await generateScenePrompts(
          config,
          sceneText,
          i + 1,
          project.characters,
          project.locations,
          nextSC,
        );

        allClips.push(...clips);

        // Обновляем следующий номер SC
        if (clips.length > 0) {
          const lastClipId = clips[clips.length - 1].scene_id;
          const match = lastClipId.match(/SC(\d+)/);
          if (match) {
            nextSC = parseInt(match[1], 10) + 1;
          }
        }
      }

      // Сохраняем промпты
      const promptsDir = resolve(paths.root, 'prompts');
      ensureDir(promptsDir);
      writeFileSync(
        resolve(promptsDir, 'all_prompts.json'),
        JSON.stringify(allClips, null, 2),
        'utf-8',
      );

      // Переходим к фазе production
      project.phase = 'production';
      store.save(project);

      res.json({
        success: true,
        clipCount: allClips.length,
        sceneCount: sceneTexts.length,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      res.status(500).json({ error: `Ошибка генерации промптов: ${message}` });
    }
  });

  // ─── ЗАГРУЗКА ПРОМПТОВ (файл от пользователя) ──────────

  // POST /api/setup/:id/upload-prompts — загрузить готовый all_prompts.json
  // Auto-parses ingredients to populate characters and locations
  router.post('/:id/upload-prompts', upload.single('file'), async (req, res) => {
    const project = store.get(req.params.id as string);
    if (!project) { res.status(404).json({ error: 'Проект не найден' }); return; }
    if (!req.file) { res.status(400).json({ error: 'Файл не загружен' }); return; }

    try {
      const content = readFileSync(req.file.path, 'utf-8');
      const clips = JSON.parse(content);

      if (!Array.isArray(clips)) {
        res.status(400).json({ error: 'Файл должен содержать массив клипов' });
        return;
      }

      if (clips.length === 0) {
        res.status(400).json({ error: 'Файл пуст — нет клипов' });
        return;
      }

      // Проверяем базовую структуру первого клипа
      const first = clips[0];
      if (!first.clip_id || !first.nano_banana_prompt_first) {
        res.status(400).json({ error: 'Неверный формат. Каждый клип должен иметь clip_id и nano_banana_prompt_first' });
        return;
      }

      // Сохраняем
      const paths = projectPaths(config.dataDir, project.id);
      const promptsDir = resolve(paths.root, 'prompts');
      ensureDir(promptsDir);
      writeFileSync(resolve(promptsDir, 'all_prompts.json'), JSON.stringify(clips, null, 2), 'utf-8');

      // ─── Auto-parse ingredients ─────────────────────
      const parsed = parseIngredientsFromPrompts(clips);

      // Known character names and clothing (Russian + identity locking)
      const CHAR_RU: Record<string, { nameRu: string; clothing: string }> = {
        amin: { nameRu: 'Амин', clothing: 'in the grey hoodie' },
        aya: { nameRu: 'Ая', clothing: 'in the pink dress and dark navy striped hijab' },
        tako: { nameRu: 'Тако', clothing: 'in the red-and-white striped shirt and red cap' },
        karim: { nameRu: 'Карим', clothing: 'in the black hoodie' },
        papa: { nameRu: 'Папа', clothing: 'in the black turtleneck sweater and glasses' },
        mama: { nameRu: 'Мама', clothing: 'in the black hijab and black abaya' },
        jamil: { nameRu: 'Джамиль', clothing: 'in the light shirt with glasses on his forehead' },
        simba: { nameRu: 'Симба', clothing: '' },
      };

      // Add detected characters (if not already present)
      for (const charRef of parsed.characters) {
        const charId = charRef.id;
        if (!project.characters.find((c) => c.id === charId)) {
          const charDir = paths.characterDir(charId);
          ensureDir(charDir);
          ensureDir(resolve(charDir, 'angles'));
          ensureDir(resolve(charDir, 'review'));

          const known = CHAR_RU[charId.toLowerCase()];
          const displayName = charId.charAt(0).toUpperCase() + charId.slice(1).replace(/_/g, ' ');

          project.characters.push({
            id: charId,
            name: displayName,
            nameRu: known?.nameRu || displayName,
            clothing: known?.clothing || '',
            description: '',
            baseImage: null,
            angles: [],
            status: 'pending',
          });
        }
      }

      // Add detected locations (if not already present)
      // Group location refs by location id to collect all angles
      const locAnglesMap = new Map<string, string[]>();
      for (const locRef of parsed.locations) {
        if (!locAnglesMap.has(locRef.id)) {
          locAnglesMap.set(locRef.id, []);
        }
        const angles = locAnglesMap.get(locRef.id)!;
        if (!angles.includes(locRef.angleId)) {
          angles.push(locRef.angleId);
        }
      }

      for (const [locId, angleIds] of locAnglesMap.entries()) {
        if (!project.locations.find((l) => l.id === locId)) {
          const locDir = paths.locationDir(locId);
          ensureDir(locDir);
          ensureDir(resolve(locDir, 'angles'));
          ensureDir(resolve(locDir, 'review'));

          const displayName = locId.charAt(0).toUpperCase() + locId.slice(1).replace(/_/g, ' ');
          const nameRu = LOC_RU[locId] || displayName;

          project.locations.push({
            id: locId,
            name: displayName,
            nameRu: nameRu,
            description: `${angleIds.length} ракурс(ов) из промптов`,
            baseImage: null,
            angles: [],
            status: 'pending',
          });
        }
      }

      // ─── Check GitHub library for matching refs ────
      const charIdsToCheck = project.characters.filter((c) => !c.baseImage).map((c) => c.id);
      const locIdsToCheck = project.locations.filter((l) => !l.baseImage).map((l) => l.id);
      let libraryResult = {
        characters: [] as Character[],
        locations: [] as Location[],
        notFound: { characters: charIdsToCheck, locations: locIdsToCheck },
      };

      if (config.githubToken) {
        try {
          libraryResult = await matchAndDownloadRefs(
            config,
            charIdsToCheck,
            locIdsToCheck,
            resolve(paths.root, 'references'),
          );

          // Update characters found in library
          for (const libChar of libraryResult.characters) {
            const idx = project.characters.findIndex((c) => c.id === libChar.id);
            if (idx >= 0) {
              project.characters[idx] = libChar;
            }
          }

          // Update locations found in library
          for (const libLoc of libraryResult.locations) {
            const idx = project.locations.findIndex((l) => l.id === libLoc.id);
            if (idx >= 0) {
              project.locations[idx] = libLoc;
            }
          }
        } catch (libErr) {
          console.error('GitHub library check failed (non-critical):', libErr);
        }
      }

      // Переходим к референсам
      project.phase = 'references';
      store.save(project);

      res.json({
        success: true,
        clipCount: clips.length,
        parsed: {
          characters: parsed.characters.length,
          locations: parsed.locations.length,
        },
        fromLibrary: {
          characters: libraryResult.characters.map((c) => c.id),
          locations: libraryResult.locations.map((l) => l.id),
        },
        notFound: libraryResult.notFound,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      res.status(400).json({ error: `Ошибка чтения файла: ${message}` });
    }
  });

  // ─── ФАЗА ─────────────────────────────────────────────

  // POST /api/projects/:id/advance — перейти к следующей фазе
  router.post('/:id/advance', (req, res) => {
    const project = store.get(req.params.id as string);
    if (!project) { res.status(404).json({ error: 'Проект не найден' }); return; }

    const phases = ['screenplay', 'prompts', 'references', 'production', 'complete'] as const;
    const currentIdx = phases.indexOf(project.phase as typeof phases[number]);
    if (currentIdx < phases.length - 1) {
      project.phase = phases[currentIdx + 1];
      store.save(project);
    }

    res.json({ phase: project.phase });
  });

  return router;
}

/** Разделяет текст сценария на сцены */
function splitIntoScenes(text: string): string[] {
  // Попытка разделить по паттернам вроде "Сцена 1", "СЦЕНА 1", "Scene 1" и т.д.
  const scenePattern = /(?:^|\n)(?:сцена|scene|СЦЕНА|SCENE)\s+\d+/gi;
  const matches = [...text.matchAll(scenePattern)];

  if (matches.length >= 2) {
    const scenes: string[] = [];
    for (let i = 0; i < matches.length; i++) {
      const start = matches[i].index!;
      const end = i < matches.length - 1 ? matches[i + 1].index! : text.length;
      scenes.push(text.slice(start, end).trim());
    }
    return scenes;
  }

  // Если не нашли паттерн сцен — разделяем по двойным переносам строк
  const chunks = text.split(/\n{3,}/);
  if (chunks.length > 1) return chunks.filter((c) => c.trim().length > 100);

  // Если всё ещё одним куском — возвращаем как одну сцену
  return [text];
}
