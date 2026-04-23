import { Router } from 'express';
import { resolve } from 'node:path';
import { existsSync } from 'node:fs';
import type { AppConfig } from '../config.js';
import { ProjectStore } from '../data/project-store.js';
import { getBotManager } from '../bot/manager.js';

export function botRouter(config: AppConfig): Router {
  const router = Router();
  const store = new ProjectStore(config.dataDir);
  const manager = getBotManager(config);

  // GET /api/bot/status — статус всех ботов
  router.get('/status', (_req, res) => {
    res.json({
      bots: manager.getStatus(),
      pythonFound: !!manager.findPython(),
      botScriptFound: !!manager.findBotScript(),
      pythonPath: manager.findPython(),
      botScriptPath: manager.findBotScript(),
    });
  });

  // POST /api/bot/start — запустить бота
  router.post('/start', (req, res) => {
    const { projectId, botId, account, numBots } = req.body as {
      projectId: string;
      botId: number;
      account: number;
      numBots?: number;
    };

    if (!projectId || botId == null || account == null) {
      res.status(400).json({ error: 'projectId, botId и account обязательны' });
      return;
    }

    const project = store.get(projectId);
    if (!project) {
      res.status(404).json({ error: 'Проект не найден' });
      return;
    }

    const projectDir = store.projectDir(projectId);
    const promptsFile = resolve(projectDir, 'prompts', 'all_prompts.json');

    if (!existsSync(promptsFile)) {
      res.status(400).json({ error: 'Файл промптов не найден. Сначала сгенерируйте промпты.' });
      return;
    }

    const extraArgs: string[] = [];
    if (project.flowProjectId) {
      extraArgs.push('--project', project.flowProjectId);
    }
    if (numBots) extraArgs.push('--num-bots', String(numBots));
    const result = manager.startBot(botId, account, projectDir, promptsFile, extraArgs, projectId);
    if (result.success) {
      res.json({ success: true, message: `Бот ${botId} запущен на аккаунте ${account}` });
    } else {
      res.status(400).json({ error: result.error });
    }
  });

  // POST /api/bot/stop — остановить бота
  router.post('/stop', (req, res) => {
    const { botId } = req.body as { botId: number };

    if (botId != null) {
      manager.stopBot(botId);
      res.json({ success: true, message: `Запрос на остановку бота ${botId} отправлен` });
    } else {
      // Остановить всех
      manager.stopAll();
      res.json({ success: true, message: 'Запрос на остановку всех ботов отправлен' });
    }
  });

  // GET /api/bot/log/:botId — лог конкретного бота
  router.get('/log/:botId', (req, res) => {
    const botId = parseInt(req.params.botId as string, 10);
    const lastN = req.query.last ? parseInt(req.query.last as string, 10) : 100;
    const log = manager.getBotLog(botId, lastN);
    res.json({ log });
  });

  return router;
}
