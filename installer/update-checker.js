/**
 * Flow App Update Checker
 *
 * Проверяет наличие обновлений на GitHub и применяет их.
 * Запускается лаунчером перед стартом сервера.
 *
 * Exit codes:
 *   0 — нет обновлений
 *   1 — ошибка (не критичная, можно продолжать)
 *   2 — обновление применено, нужен перезапуск
 */

const https = require('https');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const APP_ROOT = process.argv[2] || path.dirname(__filename);
const APP_DIR = path.join(APP_ROOT, 'app');
const VERSION_FILE = path.join(APP_DIR, 'version.json');
const GITHUB_REPO = 'bulandyisa/flow-app';
const TEMP_DIR = path.join(APP_ROOT, '_update_temp');

function getCurrentVersion() {
  try {
    if (fs.existsSync(VERSION_FILE)) {
      const data = JSON.parse(fs.readFileSync(VERSION_FILE, 'utf8'));
      return data.version || '0.0.0';
    }
    // Fallback: читаем из package.json
    const pkgPath = path.join(APP_DIR, 'package.json');
    if (fs.existsSync(pkgPath)) {
      const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));
      return pkg.version || '0.0.0';
    }
  } catch (e) {
    // ignore
  }
  return '0.0.0';
}

function compareVersions(a, b) {
  const pa = a.replace(/^v/, '').split('.').map(Number);
  const pb = b.replace(/^v/, '').split('.').map(Number);
  for (let i = 0; i < 3; i++) {
    const na = pa[i] || 0;
    const nb = pb[i] || 0;
    if (na > nb) return 1;
    if (na < nb) return -1;
  }
  return 0;
}

function httpsGet(url) {
  return new Promise((resolve, reject) => {
    const options = {
      headers: {
        'User-Agent': 'FlowApp-Updater',
        'Accept': 'application/vnd.github.v3+json'
      }
    };

    const req = https.get(url, options, (res) => {
      // Follow redirects
      if (res.statusCode === 301 || res.statusCode === 302) {
        return httpsGet(res.headers.location).then(resolve).catch(reject);
      }

      if (res.statusCode !== 200) {
        reject(new Error(`HTTP ${res.statusCode}`));
        res.resume();
        return;
      }

      const chunks = [];
      res.on('data', (chunk) => chunks.push(chunk));
      res.on('end', () => resolve(Buffer.concat(chunks)));
      res.on('error', reject);
    });

    req.on('error', reject);
    req.setTimeout(15000, () => {
      req.destroy();
      reject(new Error('Timeout'));
    });
  });
}

function downloadFile(url, destPath) {
  return new Promise((resolve, reject) => {
    const options = {
      headers: {
        'User-Agent': 'FlowApp-Updater',
        'Accept': 'application/octet-stream'
      }
    };

    const req = https.get(url, options, (res) => {
      // Follow redirects
      if (res.statusCode === 301 || res.statusCode === 302) {
        return downloadFile(res.headers.location, destPath).then(resolve).catch(reject);
      }

      if (res.statusCode !== 200) {
        reject(new Error(`HTTP ${res.statusCode}`));
        res.resume();
        return;
      }

      const file = fs.createWriteStream(destPath);
      res.pipe(file);
      file.on('finish', () => {
        file.close();
        resolve();
      });
      file.on('error', (err) => {
        fs.unlinkSync(destPath);
        reject(err);
      });
    });

    req.on('error', reject);
    req.setTimeout(120000, () => {
      req.destroy();
      reject(new Error('Download timeout'));
    });
  });
}

function rmDir(dir) {
  if (fs.existsSync(dir)) {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

// Логирование в файл (для диагностики)
const LOG_FILE = path.join(APP_ROOT, 'update.log');
function log(msg) {
  const line = `[${new Date().toISOString()}] ${msg}`;
  process.stdout.write(line + '\n');
  try { fs.appendFileSync(LOG_FILE, line + '\n'); } catch(e) {}
}

async function main() {
  const currentVersion = getCurrentVersion();
  log(`Current version: ${currentVersion}, APP_ROOT: ${APP_ROOT}, APP_DIR: ${APP_DIR}`);

  // 1. Проверяем последний релиз на GitHub
  let release;
  try {
    const data = await httpsGet(`https://api.github.com/repos/${GITHUB_REPO}/releases/latest`);
    release = JSON.parse(data.toString());
  } catch (e) {
    log(`Нет подключения к серверу обновлений: ${e.message}`);
    process.exit(1);
  }

  const latestVersion = (release.tag_name || '').replace(/^v/, '');

  if (!latestVersion) {
    log(`  Релизы не найдены.`);
    process.exit(0);
  }

  // 2. Сравниваем версии
  if (compareVersions(latestVersion, currentVersion) <= 0) {
    log(`  Текущая версия: ${currentVersion}`);
    process.exit(0);
  }

  log(`  Доступно обновление: ${currentVersion} → ${latestVersion}`);

  // 3. Ищем code-bundle.zip в assets релиза
  const asset = (release.assets || []).find(a => a.name === 'code-bundle.zip');
  if (!asset) {
    log(`  Файл обновления не найден в релизе.`);
    process.exit(1);
  }

  // 4. Скачиваем
  log(`  Скачиваю обновление (${(asset.size / 1024 / 1024).toFixed(1)} МБ)...`);

  rmDir(TEMP_DIR);
  fs.mkdirSync(TEMP_DIR, { recursive: true });

  const zipPath = path.join(TEMP_DIR, 'code-bundle.zip');

  try {
    await downloadFile(asset.browser_download_url, zipPath);
  } catch (e) {
    log(`  Download error: ${e.message}`);
    rmDir(TEMP_DIR);
    process.exit(1);
  }

  // 4b. Verify downloaded file size matches expected
  const actualSize = fs.statSync(zipPath).size;
  if (asset.size && Math.abs(actualSize - asset.size) > 1024) {
    log(`  Incomplete download (${actualSize} vs ${asset.size} bytes). Skipping.`);
    rmDir(TEMP_DIR);
    process.exit(1);
  }

  // 5. Extract
  log(`  Extracting...`);

  const extractDir = path.join(TEMP_DIR, 'extracted');
  fs.mkdirSync(extractDir, { recursive: true });

  try {
    // Try tar first (built-in on Windows 10+, fast)
    execSync(
      `tar -xf "${zipPath}" -C "${extractDir}"`,
      { stdio: 'pipe', timeout: 120000 }
    );
  } catch (e1) {
    log(`  tar failed: ${e1.message}, trying PowerShell...`);
    try {
      execSync(
        `powershell -NoProfile -Command "Expand-Archive -Path '${zipPath}' -DestinationPath '${extractDir}' -Force"`,
        { stdio: 'pipe', timeout: 300000 }
      );
    } catch (e2) {
      log(`  Extract error: ${e2.message}`);
      rmDir(TEMP_DIR);
      process.exit(1);
    }
  }

  // 5b. Verify extracted code has the critical server file
  const serverEntry = path.join(extractDir, 'packages', 'server', 'dist', 'index.js');
  if (!fs.existsSync(serverEntry)) {
    log(`  Corrupted update: server entry point missing. Skipping.`);
    rmDir(TEMP_DIR);
    process.exit(1);
  }

  // 6. Replace app/ directory (atomic with rollback)
  log(`  Installing update...`);

  const appOld = APP_DIR + '.old';

  try {
    // Удаляем предыдущий .old если остался
    rmDir(appOld);

    // Переименовываем текущую app → app.old
    if (fs.existsSync(APP_DIR)) {
      fs.renameSync(APP_DIR, appOld);
    }

    // Переименовываем extracted → app
    fs.renameSync(extractDir, APP_DIR);

    // Переносим node_modules из старой версии если в новой их нет
    const oldServerNM = path.join(appOld, 'packages', 'server', 'node_modules');
    const newServerNM = path.join(APP_DIR, 'packages', 'server', 'node_modules');
    if (fs.existsSync(oldServerNM) && !fs.existsSync(newServerNM)) {
      log('  Preserving server node_modules from previous version...');
      fs.renameSync(oldServerNM, newServerNM);
    }

    // Записываем version.json
    fs.writeFileSync(
      path.join(APP_DIR, 'version.json'),
      JSON.stringify({ version: latestVersion, updatedAt: new Date().toISOString() }, null, 2)
    );

    // Удаляем старую версию
    rmDir(appOld);

    log(`  ✓ Обновлено до версии ${latestVersion}`);
  } catch (e) {
    // Откат: если не удалось — возвращаем старую версию
    log(`  Ошибка установки: ${e.message}`);
    if (!fs.existsSync(APP_DIR) && fs.existsSync(appOld)) {
      fs.renameSync(appOld, APP_DIR);
    }
    rmDir(TEMP_DIR);
    process.exit(1);
  }

  // 7. Чистим временные файлы
  rmDir(TEMP_DIR);

  process.exit(2); // 2 = обновление применено
}

main().catch((e) => {
  log(`  Ошибка проверки обновлений: ${e.message}`);
  process.exit(1);
});
