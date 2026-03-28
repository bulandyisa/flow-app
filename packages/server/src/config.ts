import { readFileSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';

export interface AppConfig {
  port: number;
  dataDir: string;
  anthropicApiKey: string;
  githubToken: string;
  githubRepo: string;
  nodeEnv: string;
  /** Корень установки (Windows installer). Содержит node/, python/, ffmpeg/, chromium/, app/ */
  appRootDir: string | null;
}

/** Определяет корень установки (Windows installer) */
function detectAppRoot(): string | null {
  // APP_ROOT_DIR задаётся лаунчером
  if (process.env.APP_ROOT_DIR) {
    const root = resolve(process.env.APP_ROOT_DIR);
    if (existsSync(resolve(root, 'node')) && existsSync(resolve(root, 'app'))) {
      return root;
    }
  }
  return null;
}

/** Загрузка конфигурации из .env + settings.json */
export function loadConfig(): AppConfig {
  const appRootDir = detectAppRoot();
  const dataDir = resolve(process.env.DATA_DIR || './data');

  // Попытка прочитать settings.json
  let settings: Record<string, unknown> = {};
  const settingsPath = resolve(dataDir, 'settings.json');
  if (existsSync(settingsPath)) {
    settings = JSON.parse(readFileSync(settingsPath, 'utf-8'));
  }

  return {
    port: parseInt(process.env.PORT || '3000', 10),
    dataDir,
    anthropicApiKey: (process.env.ANTHROPIC_API_KEY || settings.claudeApiKey || '') as string,
    githubToken: (process.env.GITHUB_TOKEN || settings.githubToken || '') as string,
    githubRepo: (process.env.GITHUB_REPO || settings.updateRepo || 'genvid25/flow-app') as string,
    nodeEnv: process.env.NODE_ENV || 'development',
    appRootDir,
  };
}
