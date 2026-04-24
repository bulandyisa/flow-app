import { existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { execSync } from 'node:child_process';
import { BotRunner } from './runner.js';
import { parseBotOutput, type BotProgress } from './parser.js';
import { broadcast } from '../ws/events.js';
import type { AppConfig } from '../config.js';
import { ProjectStore } from '../data/project-store.js';
import { gaForBot } from '@flow-app/shared';

const FLOW_PROJECT_REGISTERED_RE = /\[FLOW_PROJECT_REGISTERED\]\s+([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/i;
const FLOW_ACCOUNT_EMAIL_RE = /\[FLOW_ACCOUNT_EMAIL\]\s+(\S+@\S+)/i;

const isWindows = process.platform === 'win32';

export interface ManagedBot {
  id: number;
  account: number;
  runner: BotRunner;
  currentClip: string | null;
  currentAction: string | null;
  completedCount: number;
  errorCount: number;
}

/**
 * Управление несколькими ботами.
 * Запускает/останавливает, парсит вывод, рассылает статус через WebSocket.
 */
export class BotManager {
  private bots: Map<number, ManagedBot> = new Map();
  private config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** Проверяет что команда доступна (bare command, не абсолютный путь) */
  private commandExists(cmd: string): boolean {
    try {
      const check = isWindows ? `where ${cmd}` : `which ${cmd}`;
      execSync(check, { stdio: 'ignore' });
      return true;
    } catch {
      return false;
    }
  }

  /** Находит Python с Playwright */
  findPython(): string | null {
    // 0. Installer mode: embedded Python рядом с приложением
    if (this.config.appRootDir) {
      const installerPython = resolve(this.config.appRootDir, 'python', 'python.exe');
      if (existsSync(installerPython)) return installerPython;
    }

    // Явный путь из переменной окружения (задаётся лаунчером)
    if (process.env.PYTHON_PATH && existsSync(process.env.PYTHON_PATH)) {
      return process.env.PYTHON_PATH;
    }

    // 1. VIRTUAL_ENV из окружения
    if (process.env.VIRTUAL_ENV) {
      const venvPython = isWindows
        ? resolve(process.env.VIRTUAL_ENV, 'Scripts', 'python.exe')
        : resolve(process.env.VIRTUAL_ENV, 'bin', 'python3');
      if (existsSync(venvPython)) return venvPython;
    }

    if (isWindows) {
      // Windows-specific candidates
      const winCandidates = [
        resolve(this.config.dataDir, 'venv', 'Scripts', 'python.exe'),        // venv в data/
      ];

      // Common Windows Python install paths
      const drives = ['C:', 'D:'];
      for (const drive of drives) {
        for (const ver of ['Python312', 'Python311', 'Python310', 'Python39', 'Python3']) {
          winCandidates.push(resolve(drive, ver, 'python.exe'));
        }
      }

      // %LOCALAPPDATA%\Programs\Python\PythonXX\python.exe
      const localAppData = process.env.LOCALAPPDATA;
      if (localAppData) {
        for (const ver of ['Python312', 'Python311', 'Python310', 'Python39']) {
          winCandidates.push(resolve(localAppData, 'Programs', 'Python', ver, 'python.exe'));
        }
      }

      // Check absolute paths first
      for (const p of winCandidates) {
        if (existsSync(p)) return p;
      }

      // Try bare commands via PATH
      for (const cmd of ['python', 'py', 'python3']) {
        if (this.commandExists(cmd)) return cmd;
      }
    } else {
      // Unix-specific candidates
      const candidates = [
        resolve(this.config.dataDir, 'venv', 'bin', 'python3'),       // venv в data/
        resolve(process.env.HOME || '', 'FlowData', 'pw_venv', 'bin', 'python3'),  // FlowData venv
        '/usr/local/bin/python3',
        '/usr/bin/python3',
      ];

      for (const p of candidates) {
        if (existsSync(p)) return p;
      }

      // Try bare command
      if (this.commandExists('python3')) return 'python3';
    }

    return null;
  }

  /** Находит скрипт бота */
  findBotScript(): string | null {
    // Installer mode: бот в app/bot/
    if (this.config.appRootDir) {
      const installerBot = resolve(this.config.appRootDir, 'app', 'bot', 'flow_bot.py');
      if (existsSync(installerBot)) return installerBot;
    }

    // Ищем от корня проекта (3 уровня вверх от dataDir: data/ → server/ → packages/ → flow-app/)
    const projectRoot = resolve(this.config.dataDir, '..', '..', '..');
    const candidates = [
      resolve(projectRoot, 'bot', 'flow_bot.py'),        // flow-app/bot/flow_bot.py
      resolve(this.config.dataDir, '..', 'bot', 'flow_bot.py'),  // fallback
    ];
    for (const p of candidates) {
      if (existsSync(p)) return p;
    }
    return null;
  }

  /** Запускает бота */
  startBot(
    botId: number,
    account: number,
    projectDir: string,
    promptsFile: string,
    extraArgs: string[] = [],
    projectId?: string,
  ): { success: boolean; error?: string } {
    if (this.bots.has(botId)) {
      const existing = this.bots.get(botId)!;
      if (existing.runner.isRunning) {
        return { success: false, error: `Bot ${botId} is already running` };
      }
    }

    const pythonPath = this.findPython();
    if (!pythonPath) return { success: false, error: 'Python not found' };

    const botScript = this.findBotScript();
    if (!botScript) return { success: false, error: 'Bot script not found' };

    const runner = new BotRunner();
    const managed: ManagedBot = {
      id: botId,
      account,
      runner,
      currentClip: null,
      currentAction: null,
      completedCount: 0,
      errorCount: 0,
    };

    const projectStore = projectId ? new ProjectStore(this.config.dataDir) : null;

    // Парсим вывод для статуса
    runner.on('log', ({ text }: { stream: string; text: string }) => {
      // Если бот сообщил, в каком проекте Flow он оказался — сохраняем UUID в слот GA
      if (projectStore && projectId) {
        const m = text.match(FLOW_PROJECT_REGISTERED_RE);
        if (m) {
          const uuid = m[1].toLowerCase();
          const proj = projectStore.get(projectId);
          if (proj) {
            const ga = gaForBot(account);
            if (!proj.flowProjectIdByGA) proj.flowProjectIdByGA = {};
            if (proj.flowProjectIdByGA[ga] !== uuid) {
              proj.flowProjectIdByGA[ga] = uuid;
              projectStore.save(proj);
              broadcast({
                type: 'bot_status',
                data: { botId, action: 'flow_project_registered', ga, flowProjectId: uuid },
              });
            }
          }
        }

        // Если бот сообщил email залогиненного Google-аккаунта — сохраняем в слот GA
        const em = text.match(FLOW_ACCOUNT_EMAIL_RE);
        if (em) {
          const email = em[1].trim();
          const proj = projectStore.get(projectId);
          if (proj) {
            const ga = gaForBot(account);
            if (!proj.flowAccountEmailByGA) proj.flowAccountEmailByGA = {};
            if (proj.flowAccountEmailByGA[ga] !== email) {
              proj.flowAccountEmailByGA[ga] = email;
              projectStore.save(proj);
              broadcast({
                type: 'bot_status',
                data: { botId, action: 'flow_account_email', ga, email },
              });
            }
          }
        }
      }

      const progress = parseBotOutput(text);
      if (progress) {
        if (progress.clipId) managed.currentClip = progress.clipId;
        if (progress.action) managed.currentAction = progress.action;
        if (progress.action === 'done') managed.completedCount++;
        if (progress.action === 'error') managed.errorCount++;

        broadcast({
          type: 'bot_status',
          data: {
            botId,
            ...progress,
            completedCount: managed.completedCount,
            errorCount: managed.errorCount,
          },
        });
      }

      // Всегда рассылаем лог
      broadcast({
        type: 'generation_progress',
        data: { botId, text },
      });
    });

    runner.on('exit', ({ code }: { code: number | null }) => {
      managed.currentAction = code === 0 ? 'finished' : 'stopped';
      broadcast({
        type: 'bot_status',
        data: {
          botId,
          action: managed.currentAction,
          exitCode: code,
          completedCount: managed.completedCount,
        },
      });
    });

    this.bots.set(botId, managed);

    const args = [
      '--chain',
      '--account', String(account),
      '--chromium',
      '--prompts', promptsFile,
      '--output-dir', projectDir,
      ...extraArgs,
    ];

    // Формируем env для бота
    const botEnv: Record<string, string> = {
      SESSIONS_DIR: resolve(this.config.dataDir, 'sessions'),
    };
    if (this.config.appRootDir) {
      const chromiumDir = resolve(this.config.appRootDir, 'chromium');
      if (existsSync(chromiumDir)) {
        botEnv.PLAYWRIGHT_BROWSERS_PATH = chromiumDir;
      }
    } else if (process.env.PLAYWRIGHT_BROWSERS_PATH) {
      botEnv.PLAYWRIGHT_BROWSERS_PATH = process.env.PLAYWRIGHT_BROWSERS_PATH;
    }

    runner.start({
      pythonPath,
      botScript,
      args,
      cwd: resolve(botScript, '..', '..'),
      env: botEnv,
      timeoutMs: 3600_000, // 1 час
    });

    return { success: true };
  }

  /** Запускает одного бота для генерации референсов */
  private startSingleRefBot(
    botId: number,
    account: number,
    projectDir: string,
    botIndex: number,
    botCount: number,
    filter?: { characters: string[]; locations: string[]; angles: string[] },
  ): { success: boolean; error?: string } {
    if (this.bots.has(botId)) {
      const existing = this.bots.get(botId)!;
      if (existing.runner.isRunning) {
        return { success: false, error: `Bot ${botId} is already running` };
      }
    }

    const pythonPath = this.findPython();
    if (!pythonPath) return { success: false, error: 'Python not found' };

    const botScript = this.findBotScript();
    if (!botScript) return { success: false, error: 'Bot script not found' };

    const runner = new BotRunner();
    const managed: ManagedBot = {
      id: botId,
      account,
      runner,
      currentClip: null,
      currentAction: null,
      completedCount: 0,
      errorCount: 0,
    };

    // Парсим вывод для статуса (REF-specific patterns)
    runner.on('log', ({ text }: { stream: string; text: string }) => {
      const progress = parseBotOutput(text);
      if (progress) {
        if (progress.action) managed.currentAction = progress.action;
        if (progress.action === 'done') managed.completedCount++;
        if (progress.action === 'error') managed.errorCount++;
      }

      // Parse [REF] lines for status
      const refMatch = text.match(/\[REF\]\s*\[(\d+)\/(\d+)\]\s*(OK|FAIL|ERROR)/);
      if (refMatch) {
        const action = refMatch[3] === 'OK' ? 'done' : 'error';
        if (action === 'done') managed.completedCount++;
        if (action === 'error') managed.errorCount++;
        managed.currentAction = action;
      }

      const refGenerating = text.match(/\[REF\].*Generating\s+(.+)/);
      if (refGenerating) {
        managed.currentClip = refGenerating[1].substring(0, 60);
        managed.currentAction = 'generating';
      }

      broadcast({
        type: 'bot_status',
        data: {
          botId,
          action: managed.currentAction,
          completedCount: managed.completedCount,
          errorCount: managed.errorCount,
        },
      });

      broadcast({
        type: 'generation_progress',
        data: { botId, text },
      });
    });

    runner.on('exit', ({ code }: { code: number | null }) => {
      managed.currentAction = code === 0 ? 'finished' : 'stopped';
      broadcast({
        type: 'bot_status',
        data: {
          botId,
          action: managed.currentAction,
          exitCode: code,
          completedCount: managed.completedCount,
        },
      });
    });

    this.bots.set(botId, managed);

    const args = [
      '--generate-refs',
      '--project-dir', projectDir,
      '--account', String(account),
      '--chromium',
      '--bot-index', String(botIndex),
      '--bot-count', String(botCount),
    ];

    if (filter) {
      args.push('--filter', JSON.stringify(filter));
    }

    // Формируем env для бота
    const botEnv: Record<string, string> = {
      SESSIONS_DIR: resolve(this.config.dataDir, 'sessions'),
    };
    if (this.config.appRootDir) {
      const chromiumDir = resolve(this.config.appRootDir, 'chromium');
      if (existsSync(chromiumDir)) {
        botEnv.PLAYWRIGHT_BROWSERS_PATH = chromiumDir;
      }
    } else if (process.env.PLAYWRIGHT_BROWSERS_PATH) {
      botEnv.PLAYWRIGHT_BROWSERS_PATH = process.env.PLAYWRIGHT_BROWSERS_PATH;
    }

    runner.start({
      pythonPath,
      botScript,
      args,
      cwd: resolve(botScript, '..', '..'),
      env: botEnv,
      timeoutMs: 3600_000, // 1 час
    });

    return { success: true };
  }

  /** Запускает бота для генерации референсов (обратная совместимость) */
  startRefGeneration(
    botId: number,
    account: number,
    projectDir: string,
    filter?: { characters: string[]; locations: string[]; angles: string[] },
  ): { success: boolean; error?: string } {
    return this.startSingleRefBot(botId, account, projectDir, 0, 1, filter);
  }

  /** Запускает несколько ботов для генерации референсов */
  startMultiRefGeneration(
    botCount: number,
    accounts: number[],
    projectDir: string,
    filter?: { characters: string[]; locations: string[]; angles: string[] },
  ): { success: boolean; botIds: number[]; errors: string[] } {
    const REF_BOT_BASE_ID = 99;
    const botIds: number[] = [];
    const errors: string[] = [];

    for (let i = 0; i < botCount; i++) {
      const botId = REF_BOT_BASE_ID - i;
      const account = accounts[i % accounts.length];
      const result = this.startSingleRefBot(botId, account, projectDir, i, botCount, filter);
      if (result.success) {
        botIds.push(botId);
      } else {
        errors.push(`Bot ${botId}: ${result.error}`);
      }
    }

    return {
      success: botIds.length > 0,
      botIds,
      errors,
    };
  }

  /** Возвращает статус всех ref-ботов (IDs 90-99) */
  getRefBotStatuses(): Array<{
    botId: number;
    running: boolean;
    account: number;
    currentAction: string | null;
    currentClip: string | null;
    completedCount: number;
    errorCount: number;
    startedAt: string | null;
    exitCode: number | null;
  }> {
    const results = [];
    for (const [, managed] of this.bots) {
      if (managed.id >= 90 && managed.id <= 99) {
        results.push({
          botId: managed.id,
          running: managed.runner.isRunning,
          account: managed.account,
          currentAction: managed.currentAction,
          currentClip: managed.currentClip,
          completedCount: managed.completedCount,
          errorCount: managed.errorCount,
          startedAt: managed.runner.startedAt,
          exitCode: managed.runner.exitCode,
        });
      }
    }
    return results;
  }

  /** Останавливает бота */
  stopBot(botId: number): void {
    const managed = this.bots.get(botId);
    if (managed?.runner.isRunning) {
      managed.runner.stop();
    }
  }

  /** Останавливает всех ботов */
  stopAll(): void {
    for (const [, managed] of this.bots) {
      if (managed.runner.isRunning) {
        managed.runner.stop();
      }
    }
  }

  /** Статус всех ботов */
  getStatus(): Array<{
    id: number;
    account: number;
    isRunning: boolean;
    currentClip: string | null;
    currentAction: string | null;
    completedCount: number;
    errorCount: number;
    startedAt: string | null;
    exitCode: number | null;
  }> {
    const statuses = [];
    for (const [, managed] of this.bots) {
      statuses.push({
        id: managed.id,
        account: managed.account,
        isRunning: managed.runner.isRunning,
        currentClip: managed.currentClip,
        currentAction: managed.currentAction,
        completedCount: managed.completedCount,
        errorCount: managed.errorCount,
        startedAt: managed.runner.startedAt,
        exitCode: managed.runner.exitCode,
      });
    }
    return statuses;
  }

  /** Лог конкретного бота */
  getBotLog(botId: number, lastN?: number) {
    const managed = this.bots.get(botId);
    if (!managed) return [];
    return managed.runner.getLog(lastN);
  }
}

// Синглтон
let instance: BotManager | null = null;
export function getBotManager(config: AppConfig): BotManager {
  if (!instance) instance = new BotManager(config);
  return instance;
}
