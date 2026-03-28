import { Router } from 'express';
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { createCipheriv, createDecipheriv, randomBytes } from 'node:crypto';
import type { AppConfig } from '../config.js';

// Ключ шифрования (захардкожен в приложении, нужен для расшифровки API ключа из access.json)
const ENCRYPTION_KEY = 'f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6';  // 32 hex = 16 bytes
const IV_LENGTH = 16;

const ACCESS_URL = 'https://raw.githubusercontent.com/genvid25/flow-app-refs/main/access.json';

export interface ActivationData {
  code: string;
  activatedAt: string;
}

interface AccessEntry {
  name: string;
  active: boolean;
  encryptedConfig?: string;  // зашифрованный JSON с API ключами
}

interface AccessFile {
  codes: Record<string, AccessEntry>;
}

interface DecryptedConfig {
  anthropicApiKey?: string;
  githubToken?: string;
}

/** Шифрует строку (для утилиты генерации кодов) */
export function encrypt(text: string): string {
  const iv = randomBytes(IV_LENGTH);
  const cipher = createCipheriv('aes-128-cbc', Buffer.from(ENCRYPTION_KEY, 'hex'), iv);
  let encrypted = cipher.update(text, 'utf-8', 'hex');
  encrypted += cipher.final('hex');
  return iv.toString('hex') + ':' + encrypted;
}

/** Расшифровывает строку */
function decrypt(encrypted: string): string {
  const [ivHex, encHex] = encrypted.split(':');
  const iv = Buffer.from(ivHex, 'hex');
  const decipher = createDecipheriv('aes-128-cbc', Buffer.from(ENCRYPTION_KEY, 'hex'), iv);
  let decrypted = decipher.update(encHex, 'hex', 'utf-8');
  decrypted += decipher.final('utf-8');
  return decrypted;
}

/** Расшифровывает конфиг из access entry */
function decryptConfig(entry: AccessEntry): DecryptedConfig | null {
  if (!entry.encryptedConfig) return null;
  try {
    const json = decrypt(entry.encryptedConfig);
    return JSON.parse(json);
  } catch {
    return null;
  }
}

/** Fetch the remote access list */
async function fetchAccessList(): Promise<AccessFile | null> {
  try {
    const res = await fetch(ACCESS_URL, { signal: AbortSignal.timeout(10_000) });
    if (!res.ok) return null;
    return (await res.json()) as AccessFile;
  } catch {
    return null;
  }
}

/** Read local activation data */
function loadActivation(dataDir: string): ActivationData | null {
  const filePath = resolve(dataDir, 'activation.json');
  if (!existsSync(filePath)) return null;
  try {
    return JSON.parse(readFileSync(filePath, 'utf-8')) as ActivationData;
  } catch {
    return null;
  }
}

/** Save activation data locally */
function saveActivation(dataDir: string, data: ActivationData): void {
  writeFileSync(resolve(dataDir, 'activation.json'), JSON.stringify(data, null, 2), 'utf-8');
}

/** Save decrypted config to settings.json */
function saveConfig(dataDir: string, config: DecryptedConfig): void {
  const settingsPath = resolve(dataDir, 'settings.json');
  let settings: Record<string, unknown> = {};
  if (existsSync(settingsPath)) {
    try {
      settings = JSON.parse(readFileSync(settingsPath, 'utf-8'));
    } catch { /* ignore */ }
  }

  if (config.anthropicApiKey) settings.claudeApiKey = config.anthropicApiKey;
  if (config.githubToken) settings.githubToken = config.githubToken;

  writeFileSync(settingsPath, JSON.stringify(settings, null, 2), 'utf-8');
}

/** Shared activation state */
let _activated = false;

export function isActivated(): boolean {
  return _activated;
}

export function setActivated(value: boolean): void {
  _activated = value;
}

/** Check activation on startup */
export async function checkActivationOnStartup(config: AppConfig): Promise<boolean> {
  const activation = loadActivation(config.dataDir);
  if (!activation) {
    _activated = false;
    return false;
  }

  const access = await fetchAccessList();
  if (!access) {
    // Нет интернета — доверяем локальной активации
    _activated = true;
    return true;
  }

  const entry = access.codes[activation.code];
  if (entry && entry.active) {
    _activated = true;
    // Обновляем ключи при каждом запуске (могли измениться)
    const decrypted = decryptConfig(entry);
    if (decrypted) saveConfig(config.dataDir, decrypted);
    return true;
  }

  // Код деактивирован или удалён
  _activated = false;
  return false;
}

export function authRouter(config: AppConfig): Router {
  const router = Router();

  // GET /api/auth/status
  router.get('/status', (_req, res) => {
    const activation = loadActivation(config.dataDir);
    res.json({
      activated: _activated,
      code: activation?.code || null,
      activatedAt: activation?.activatedAt || null,
    });
  });

  // POST /api/auth/activate
  router.post('/activate', async (req, res) => {
    const { code } = req.body as { code?: string };

    if (!code || typeof code !== 'string' || code.trim().length === 0) {
      res.status(400).json({ error: 'Код активации обязателен' });
      return;
    }

    const trimmedCode = code.trim();
    const access = await fetchAccessList();

    if (!access) {
      res.status(502).json({ error: 'Не удалось проверить код. Попробуйте позже.' });
      return;
    }

    const entry = access.codes[trimmedCode];
    if (!entry) {
      res.status(403).json({ error: 'Неверный код активации' });
      return;
    }

    if (!entry.active) {
      res.status(403).json({ error: 'Код деактивирован. Обратитесь к администратору.' });
      return;
    }

    // Расшифровываем конфиг
    const decrypted = decryptConfig(entry);
    if (!decrypted || !decrypted.anthropicApiKey) {
      res.status(500).json({ error: 'Ошибка конфигурации. Обратитесь к администратору.' });
      return;
    }

    // Сохраняем активацию
    saveActivation(config.dataDir, {
      code: trimmedCode,
      activatedAt: new Date().toISOString(),
    });

    // Сохраняем расшифрованные ключи
    saveConfig(config.dataDir, decrypted);

    _activated = true;

    res.json({
      success: true,
      name: entry.name,
      message: `Добро пожаловать, ${entry.name}!`,
    });
  });

  // POST /api/auth/encrypt — утилита для администратора (зашифровать конфиг)
  router.post('/encrypt', (req, res) => {
    const { text } = req.body as { text: string };
    if (!text) {
      res.status(400).json({ error: 'text обязателен' });
      return;
    }
    res.json({ encrypted: encrypt(text) });
  });

  return router;
}
