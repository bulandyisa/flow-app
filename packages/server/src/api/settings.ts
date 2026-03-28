import { Router } from 'express';
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';
import type { AppConfig } from '../config.js';

export interface UserSettings {
  claudeApiKey: string;
  animationStyle: string;
  defaultVariantCount: number;
  accounts: Array<{
    email: string;
    sessionDir: string;
    maxBots: number;
  }>;
  githubToken: string;
  updateRepo: string;
}

const DEFAULT_SETTINGS: UserSettings = {
  claudeApiKey: '',
  animationStyle: '3D Pixar-style',
  defaultVariantCount: 4,
  accounts: [],
  githubToken: '',
  updateRepo: 'bulandyisa/flow-app',
};

export function settingsRouter(config: AppConfig): Router {
  const router = Router();
  const settingsFile = resolve(config.dataDir, 'settings.json');

  function load(): UserSettings {
    if (!existsSync(settingsFile)) return { ...DEFAULT_SETTINGS };
    return { ...DEFAULT_SETTINGS, ...JSON.parse(readFileSync(settingsFile, 'utf-8')) };
  }

  function save(settings: UserSettings): void {
    writeFileSync(settingsFile, JSON.stringify(settings, null, 2), 'utf-8');
  }

  // GET /api/settings
  router.get('/', (_req, res) => {
    const settings = load();
    // Маскируем ключи в ответе
    res.json({
      ...settings,
      claudeApiKey: settings.claudeApiKey ? '***' + settings.claudeApiKey.slice(-4) : '',
      githubToken: settings.githubToken ? '***' + settings.githubToken.slice(-4) : '',
    });
  });

  // PATCH /api/settings
  router.patch('/', (req, res) => {
    const current = load();
    const updates = req.body;

    // Не перезаписываем ключи маскированными значениями
    if (updates.claudeApiKey?.startsWith('***')) delete updates.claudeApiKey;
    if (updates.githubToken?.startsWith('***')) delete updates.githubToken;

    Object.assign(current, updates);
    save(current);
    res.json({ success: true });
  });

  return router;
}
