/** Состояние одного бота */
export type BotState = 'idle' | 'running' | 'error' | 'stopped';

/** Тип задания бота */
export type BotTaskType = 'reference_base' | 'reference_angles' | 'nb_first' | 'veo';

/** Текущее задание бота */
export interface BotTask {
  type: BotTaskType;
  clipId?: string;
  characterId?: string;
  locationId?: string;
  angleId?: string;
  progress: string;       // "Uploading ingredients..." / "Polling 45%"
}

/** Конфигурация аккаунта */
export interface BotAccount {
  id: number;             // 1-6
  email: string;
  sessionDir: string;
  maxBots: number;
}

/** Статус одного бота */
export interface BotStatus {
  id: number;
  account: BotAccount;
  state: BotState;
  currentTask: BotTask | null;
  completedTasks: number;
  failedTasks: number;
  startedAt: string | null;
  lastError: string | null;
}

/** Конфигурация запуска ботов */
export interface BotRunConfig {
  projectId: string;
  taskType: BotTaskType;
  accounts: number[];     // какие аккаунты использовать
  maxBots: number;
}
