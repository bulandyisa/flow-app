import { Router } from 'express';
import { resolve, normalize } from 'node:path';
import { existsSync, realpathSync } from 'node:fs';
import type { AppConfig } from '../config.js';

export function mediaRouter(config: AppConfig): Router {
  const router = Router();

  // GET /api/media/:projectId/* — раздача картинок/видео
  // Пример: /api/media/abc-123/review/SC001_A/nb_first/attempt_1/variant_1.png
  // Пример: /api/media/abc-123/references/locations/porch/angles/wide_front.png
  router.get('/:projectId/*', (req, res) => {
    const projectDir = resolve(config.dataDir, 'projects', req.params.projectId);
    const wildcard = req.params[0 as unknown as keyof typeof req.params] as string;
    const filePath = resolve(projectDir, wildcard);

    // Первичная проверка по нормализованному пути (до resolve symlinks)
    const normalizedPath = normalize(filePath);
    const normalizedProjectDir = normalize(projectDir);
    if (!normalizedPath.startsWith(normalizedProjectDir)) {
      res.status(403).json({ error: 'Доступ запрещён' });
      return;
    }

    if (!existsSync(filePath)) {
      res.status(404).json({ error: 'Файл не найден' });
      return;
    }

    // Проверка реального пути после resolve symlinks
    try {
      const realFilePath = realpathSync(filePath);
      const realProjectDir = realpathSync(projectDir);
      if (!realFilePath.startsWith(realProjectDir)) {
        res.status(403).json({ error: 'Доступ запрещён' });
        return;
      }
    } catch {
      res.status(404).json({ error: 'Файл не найден' });
      return;
    }

    // Кеширование на 1 час (варианты не меняются после создания)
    res.set('Cache-Control', 'public, max-age=3600');
    res.sendFile(filePath);
  });

  return router;
}
