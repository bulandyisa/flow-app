import { spawn, exec, ChildProcess } from 'node:child_process';
import { existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { EventEmitter } from 'node:events';

const isWindows = process.platform === 'win32';

export interface BotRunnerOptions {
  pythonPath: string;
  botScript: string;
  args: string[];
  cwd: string;
  env?: Record<string, string>;
  timeoutMs?: number;
}

export interface BotLogLine {
  timestamp: string;
  stream: 'stdout' | 'stderr';
  text: string;
}

/**
 * Запуск и управление одним Python-процессом бота.
 * Эмитит события: 'log', 'status', 'exit', 'error'
 */
export class BotRunner extends EventEmitter {
  private process: ChildProcess | null = null;
  private _isRunning = false;
  private _exitCode: number | null = null;
  private _startedAt: string | null = null;
  private _log: BotLogLine[] = [];
  private timeoutTimer: ReturnType<typeof setTimeout> | null = null;

  get isRunning(): boolean { return this._isRunning; }
  get exitCode(): number | null { return this._exitCode; }
  get startedAt(): string | null { return this._startedAt; }
  get log(): BotLogLine[] { return this._log; }

  /** Запускает бот-процесс */
  start(options: BotRunnerOptions): void {
    if (this._isRunning) {
      this.emit('error', 'Bot is already running');
      return;
    }

    // Проверяем что Python и скрипт существуют
    // Bare commands (e.g. 'python', 'py', 'python3') won't have path separators
    const isBareCommand = !options.pythonPath.includes('/') && !options.pythonPath.includes('\\');
    if (!isBareCommand && !existsSync(options.pythonPath)) {
      this.emit('error', `Python not found: ${options.pythonPath}`);
      return;
    }
    if (!existsSync(options.botScript)) {
      this.emit('error', `Bot script not found: ${options.botScript}`);
      return;
    }

    this._log = [];
    this._exitCode = null;
    this._startedAt = new Date().toISOString();
    this._isRunning = true;

    const allArgs = [options.botScript, ...options.args];
    this.addLog('stdout', `Starting: ${options.pythonPath} ${allArgs.join(' ')}`);

    this.process = spawn(options.pythonPath, allArgs, {
      cwd: options.cwd,
      env: { ...process.env, PYTHONUNBUFFERED: '1', ...options.env },
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    // stdout
    this.process.stdout?.on('data', (data: Buffer) => {
      const lines = data.toString().split('\n').filter((l) => l.trim());
      for (const line of lines) {
        this.addLog('stdout', line);
        this.emit('log', { stream: 'stdout', text: line });
      }
    });

    // stderr
    this.process.stderr?.on('data', (data: Buffer) => {
      const lines = data.toString().split('\n').filter((l) => l.trim());
      for (const line of lines) {
        this.addLog('stderr', line);
        this.emit('log', { stream: 'stderr', text: line });
      }
    });

    // exit
    this.process.on('exit', (code, signal) => {
      this._isRunning = false;
      this._exitCode = code;
      this.clearTimeout();
      const msg = signal ? `Killed by signal ${signal}` : `Exited with code ${code}`;
      this.addLog('stdout', msg);
      this.emit('exit', { code, signal });
    });

    // error
    this.process.on('error', (err) => {
      this._isRunning = false;
      this.clearTimeout();
      this.addLog('stderr', `Process error: ${err.message}`);
      this.emit('error', err.message);
    });

    // Таймаут
    if (options.timeoutMs) {
      this.timeoutTimer = setTimeout(() => {
        if (this._isRunning) {
          this.addLog('stderr', `Timeout after ${options.timeoutMs}ms, killing...`);
          this.stop();
        }
      }, options.timeoutMs);
    }

    this.emit('status', 'running');
  }

  /** Принудительно завершает процесс по PID (Windows: taskkill, Unix: SIGKILL) */
  private forceKill(): void {
    if (!this.process || !this.process.pid) return;

    if (isWindows) {
      // taskkill /pid <pid> /f /t — force kill process tree on Windows
      exec(`taskkill /pid ${this.process.pid} /f /t`, (err) => {
        if (err) {
          this.addLog('stderr', `taskkill failed: ${err.message}`);
        }
      });
    } else {
      this.process.kill('SIGKILL');
    }
  }

  /** Останавливает бот-процесс */
  stop(): void {
    if (!this.process || !this._isRunning) return;

    this.clearTimeout();
    this.addLog('stdout', 'Stopping bot...');

    if (isWindows) {
      // On Windows, SIGTERM is not reliably supported.
      // Try graceful kill first, then force kill after 5 seconds.
      this.process.kill();
      const killTimer = setTimeout(() => {
        if (this._isRunning && this.process) {
          this.addLog('stderr', 'Force killing (taskkill)...');
          this.forceKill();
        }
      }, 5000);
      this.process.on('exit', () => clearTimeout(killTimer));
    } else {
      // Unix: SIGTERM, then SIGKILL after 5 seconds
      this.process.kill('SIGTERM');
      const killTimer = setTimeout(() => {
        if (this._isRunning && this.process) {
          this.addLog('stderr', 'Force killing (SIGKILL)...');
          this.process!.kill('SIGKILL');
        }
      }, 5000);
      this.process.on('exit', () => clearTimeout(killTimer));
    }
  }

  /** Получить последние N строк лога */
  getLog(lastN?: number): BotLogLine[] {
    if (!lastN) return this._log;
    return this._log.slice(-lastN);
  }

  private addLog(stream: 'stdout' | 'stderr', text: string): void {
    const entry: BotLogLine = {
      timestamp: new Date().toISOString(),
      stream,
      text,
    };
    this._log.push(entry);
    // Ограничиваем лог 1000 строками
    if (this._log.length > 1000) {
      this._log = this._log.slice(-800);
    }
  }

  private clearTimeout(): void {
    if (this.timeoutTimer) {
      clearTimeout(this.timeoutTimer);
      this.timeoutTimer = null;
    }
  }
}
