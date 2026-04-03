import express from 'express';
import cors from 'cors';
import { createServer } from 'node:http';
import { resolve, dirname, extname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { mkdirSync, existsSync, writeFileSync, unlinkSync, renameSync, readdirSync, readFileSync } from 'node:fs';
import { loadConfig } from './config.js';
import { projectsRouter } from './api/projects.js';
import { mediaRouter } from './api/media.js';
import { settingsRouter } from './api/settings.js';
import { setupRouter } from './api/setup.js';
import { botRouter } from './api/bot.js';
import { clipsRouter } from './api/clips.js';
import { referencesRouter } from './api/references.js';
import { updateRouter } from './api/update.js';
import { assemblyRouter } from './api/assembly.js';
import { authRouter, checkActivationOnStartup } from './api/auth.js';
import { requireActivation } from './middleware/auth.js';
import { setupWebSocket } from './ws/events.js';

const config = loadConfig();

// Создаём необходимые директории
const dirs = [
  config.dataDir,
  resolve(config.dataDir, 'projects'),
  resolve(config.dataDir, 'sessions'),
];
for (const dir of dirs) {
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
}

// Миграция: переименовать base.* → {id}_base.* для уникальных имён
{
  const projectsDir = resolve(config.dataDir, 'projects');
  if (existsSync(projectsDir)) {
    for (const projDir of readdirSync(projectsDir, { withFileTypes: true })) {
      if (!projDir.isDirectory()) continue;
      const pjPath = resolve(projectsDir, projDir.name, 'project.json');
      if (!existsSync(pjPath)) continue;

      try {
        const project = JSON.parse(readFileSync(pjPath, 'utf-8'));
        let changed = false;

        for (const type of ['characters', 'locations'] as const) {
          for (const item of project[type] || []) {
            const refsDir = resolve(projectsDir, projDir.name, 'references', type, item.id);
            if (!existsSync(refsDir)) continue;

            // Find base.* files (old format)
            for (const file of readdirSync(refsDir)) {
              const match = file.match(/^base\.(png|jpg|jpeg|webp)$/);
              if (match) {
                const newName = `${item.id}_base.${match[1]}`;
                const oldPath = resolve(refsDir, file);
                const newPath = resolve(refsDir, newName);
                if (!existsSync(newPath)) {
                  renameSync(oldPath, newPath);
                  // Update project.json path
                  const newRelPath = `references/${type}/${item.id}/${newName}`;
                  if (item.baseImage && item.baseImage.includes(`/base.${match[1]}`)) {
                    item.baseImage = newRelPath;
                    changed = true;
                  }
                }
              }
            }
          }
        }

        if (changed) {
          writeFileSync(pjPath, JSON.stringify(project, null, 2), 'utf-8');
        }
      } catch { /* skip broken projects */ }
    }
  }
}

// Проверяем активацию при старте
const activated = await checkActivationOnStartup(config);
console.log(`  Активация: ${activated ? '✓ активировано' : '✗ не активировано'}`);

const app = express();
app.use(cors());
app.use(express.json({ limit: '50mb' }));

// Auth routes — доступны без активации
app.use('/api/auth', authRouter(config));

// Middleware: блокирует все остальные API без активации
app.use('/api', requireActivation);

// API маршруты
app.use('/api/projects', projectsRouter(config));
app.use('/api/setup', setupRouter(config));
app.use('/api/references', referencesRouter(config));
app.use('/api/bot', botRouter(config));
app.use('/api/clips', clipsRouter(config));
app.use('/api/media', mediaRouter(config));
app.use('/api/update', updateRouter(config));
app.use('/api/assembly', assemblyRouter(config));
app.use('/api/settings', settingsRouter(config));

// Раздаём собранный клиент (если dist существует)
{
  const __dirname = dirname(fileURLToPath(import.meta.url));
  const clientDist = resolve(__dirname, '../../client/dist');
  if (existsSync(resolve(clientDist, 'index.html'))) {
    app.use(express.static(clientDist));
    app.get('*', (_req, res) => {
      res.sendFile(resolve(clientDist, 'index.html'));
    });
  }
}

// HTTP + WebSocket сервер
const server = createServer(app);
setupWebSocket(server);

server.listen(config.port, () => {
  console.log(`\n  Flow App запущен: http://localhost:${config.port}`);
  console.log(`  Данные: ${config.dataDir}`);
  console.log(`  Claude API: ${config.anthropicApiKey ? '✓ настроен' : '✗ нет ключа'}\n`);

  // Save PID for launcher cleanup
  const pidFile = resolve(config.dataDir, 'server.pid');
  writeFileSync(pidFile, String(process.pid));
  const cleanup = () => { try { unlinkSync(pidFile); } catch {} };
  process.on('exit', cleanup);
  process.on('SIGTERM', () => { cleanup(); process.exit(0); });
  process.on('SIGINT', () => { cleanup(); process.exit(0); });
});
