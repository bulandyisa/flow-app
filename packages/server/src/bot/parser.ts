/** Парсинг stdout бота для извлечения прогресса */

export interface BotProgress {
  clipId?: string;
  component?: string;
  action?: string;     // "uploading", "generating", "polling", "downloading", "done", "error"
  detail?: string;     // "45%", "variant_1.png", etc.
  percentage?: number; // 0-100 если есть
}

/** Паттерны для парсинга вывода бота */
const PATTERNS = [
  // Клип и компонент
  { regex: /Processing\s+(SC\d+_\w+)\s+(\w+)/i, extract: (m: RegExpMatchArray): BotProgress => ({ clipId: m[1], component: m[2], action: 'processing' }) },
  // Загрузка ингредиентов
  { regex: /upload.*ingredient/i, extract: (): BotProgress => ({ action: 'uploading', detail: 'ingredients' }) },
  // Заполнение промпта
  { regex: /fill.*prompt/i, extract: (): BotProgress => ({ action: 'filling', detail: 'prompt' }) },
  // Генерация
  { regex: /click.*generate/i, extract: (): BotProgress => ({ action: 'generating' }) },
  // Polling с процентами
  { regex: /(\d+)%/i, extract: (m: RegExpMatchArray): BotProgress => ({ action: 'polling', percentage: parseInt(m[1], 10), detail: `${m[1]}%` }) },
  // Скачивание варианта
  { regex: /Saved.*variant[_\s]?(\d+)/i, extract: (m: RegExpMatchArray): BotProgress => ({ action: 'downloading', detail: `variant_${m[1]}` }) },
  // Ошибки
  { regex: /error|failed|exception/i, extract: (m: RegExpMatchArray): BotProgress => ({ action: 'error', detail: m[0] }) },
  // Завершение клипа
  { regex: /completed?\s+(SC\d+_\w+)/i, extract: (m: RegExpMatchArray): BotProgress => ({ clipId: m[1], action: 'done' }) },
  // Chain-блокировка
  { regex: /chain.?blocked|no pending/i, extract: (): BotProgress => ({ action: 'blocked', detail: 'chain-blocked' }) },
  // Закрытие
  { regex: /all.*done|closing|shutdown/i, extract: (): BotProgress => ({ action: 'finished' }) },
  // Reference generation progress
  { regex: /\[REF\]\s*\[(\d+)\/(\d+)\]\s*(OK)/i, extract: (m: RegExpMatchArray): BotProgress => ({ action: 'done', detail: `ref ${m[1]}/${m[2]}` }) },
  { regex: /\[REF\]\s*\[(\d+)\/(\d+)\]\s*(FAIL|ERROR)/i, extract: (m: RegExpMatchArray): BotProgress => ({ action: 'error', detail: `ref ${m[1]}/${m[2]}` }) },
  { regex: /\[REF\]\s*Generating\s+(.+)/i, extract: (m: RegExpMatchArray): BotProgress => ({ action: 'generating', detail: m[1].substring(0, 60) }) },
  { regex: /\[REF\]\s*Done\.\s*Generated\s+(\d+)/i, extract: (m: RegExpMatchArray): BotProgress => ({ action: 'finished', detail: `${m[1]} items` }) },
];

/** Строки которые игнорируем полностью — это шум из консоли браузера, не ошибки бота */
const IGNORED_PREFIXES = [
  '[CONSOLE ERROR]',
  '[CONSOLE WARNING]',
  '[CONSOLE INFO]',
  '[CONSOLE LOG]',
];

/** Парсит строку stdout бота и извлекает прогресс */
export function parseBotOutput(line: string): BotProgress | null {
  const trimmed = line.trim();
  // Игнорируем эхо консоли Chromium — это внутренние ошибки Google Flow, не бага бота
  for (const prefix of IGNORED_PREFIXES) {
    if (trimmed.startsWith(prefix)) return null;
  }
  for (const pattern of PATTERNS) {
    const match = line.match(pattern.regex);
    if (match) {
      const result = pattern.extract(match);
      // Для ошибок сохраняем полную строку лога, а не только совпавшее слово
      if (result.action === 'error') {
        result.detail = trimmed.substring(0, 300);
      }
      return result;
    }
  }
  return null;
}
