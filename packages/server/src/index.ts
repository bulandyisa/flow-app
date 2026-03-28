import express from 'express';
import cors from 'cors';
import { createServer } from 'node:http';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { mkdirSync, existsSync } from 'node:fs';
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

// В production раздаём собранный клиент
if (config.nodeEnv === 'production') {
  const __dirname = dirname(fileURLToPath(import.meta.url));
  const clientDist = resolve(__dirname, '../../client/dist');
  app.use(express.static(clientDist));
  app.get('*', (_req, res) => {
    res.sendFile(resolve(clientDist, 'index.html'));
  });
}

// HTTP + WebSocket сервер
const server = createServer(app);
setupWebSocket(server);

server.listen(config.port, () => {
  console.log(`\n  Flow App запущен: http://localhost:${config.port}`);
  console.log(`  Данные: ${config.dataDir}`);
  console.log(`  Claude API: ${config.anthropicApiKey ? '✓ настроен' : '✗ нет ключа'}\n`);
});
