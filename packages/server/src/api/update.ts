import { Router } from 'express';
import { readFileSync, existsSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import type { AppConfig } from '../config.js';

interface GitHubRelease {
  tag_name: string;
  name: string;
  body: string;
  published_at: string;
  html_url: string;
  assets?: Array<{ name: string; browser_download_url: string; size: number }>;
}

/** Читает текущую версию из version.json (installer) или package.json */
function getCurrentVersion(config: AppConfig): string {
  // 1. version.json в installer mode
  if (config.appRootDir) {
    const versionFile = resolve(config.appRootDir, 'app', 'version.json');
    if (existsSync(versionFile)) {
      try {
        const data = JSON.parse(readFileSync(versionFile, 'utf-8'));
        if (data.version) return data.version;
      } catch { /* fallthrough */ }
    }
  }

  // 2. package.json
  const __dirname = dirname(fileURLToPath(import.meta.url));
  const pkgPath = resolve(__dirname, '../../../..', 'package.json');
  if (existsSync(pkgPath)) {
    try {
      return JSON.parse(readFileSync(pkgPath, 'utf-8')).version || '0.0.0';
    } catch { /* fallthrough */ }
  }

  return '0.0.0';
}

export function updateRouter(config: AppConfig): Router {
  const router = Router();

  // GET /api/update/version — текущая версия
  router.get('/version', (_req, res) => {
    const version = getCurrentVersion(config);
    const isInstalled = !!config.appRootDir;
    res.json({ version, isInstalled });
  });

  // GET /api/update/check — проверить наличие обновлений через HTML-редирект
  // (не api.github.com — у того анонимный лимит 60 req/hour на IP, легко исчерпывается
  // в офисе с общим NAT + UpdateNotice бьёт каждые 30 мин у каждого).
  const TAG_FROM_URL_RE = /\/releases\/tag\/(v?\d+\.\d+\.\d+)/;
  router.get('/check', async (_req, res) => {
    try {
      const currentVersion = getCurrentVersion(config);

      if (!config.githubRepo) {
        res.json({ currentVersion, updateAvailable: false, message: 'GitHub repo not configured' });
        return;
      }

      // github.com/<repo>/releases/latest → 302 → /releases/tag/<tag>
      const response = await fetch(
        `https://github.com/${config.githubRepo}/releases/latest`,
        { redirect: 'manual', headers: { 'User-Agent': 'FlowApp' } },
      );

      let latestVersion: string | null = null;
      if (response.status === 301 || response.status === 302) {
        const loc = response.headers.get('location') || '';
        const m = loc.match(TAG_FROM_URL_RE);
        if (m) latestVersion = m[1].replace(/^v/, '');
      } else if (response.ok) {
        const body = await response.text();
        const m = body.match(TAG_FROM_URL_RE);
        if (m) latestVersion = m[1].replace(/^v/, '');
      }

      if (!latestVersion) {
        res.json({ currentVersion, updateAvailable: false, message: `Нет данных о последнем релизе (HTTP ${response.status})` });
        return;
      }

      const updateAvailable = latestVersion !== currentVersion && compareVersions(latestVersion, currentVersion) > 0;

      res.json({
        currentVersion,
        latestVersion,
        updateAvailable,
        releaseUrl: `https://github.com/${config.githubRepo}/releases/tag/v${latestVersion}`,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      res.json({ currentVersion: getCurrentVersion(config), updateAvailable: false, message: `Error: ${message}` });
    }
  });

  return router;
}

/** Сравнивает версии: возвращает >0 если a > b */
function compareVersions(a: string, b: string): number {
  const pa = a.split('.').map(Number);
  const pb = b.split('.').map(Number);
  for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
    const na = pa[i] || 0;
    const nb = pb[i] || 0;
    if (na !== nb) return na - nb;
  }
  return 0;
}
