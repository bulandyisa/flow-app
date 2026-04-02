import Anthropic from '@anthropic-ai/sdk';
import { readFileSync, existsSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import type { AppConfig } from '../config.js';

let client: Anthropic | null = null;

// Кешированные правила
let cachedRules: string | null = null;

/** Получить или создать клиент Anthropic */
export function getClient(config: AppConfig): Anthropic | null {
  if (!config.anthropicApiKey) return null;
  if (!client) {
    client = new Anthropic({ apiKey: config.anthropicApiKey });
  }
  return client;
}

/** Загружает и кеширует файлы правил с диска */
export function loadRules(): string {
  if (cachedRules) return cachedRules;

  const __dirname = dirname(fileURLToPath(import.meta.url));
  const rulesDir = resolve(__dirname, '../../../..', 'rules');
  const files = ['quality-rules.md', 'prompt-spec.md', 'veo-prompt-spec.md'];
  const parts: string[] = [];

  for (const file of files) {
    const filePath = resolve(rulesDir, file);
    if (existsSync(filePath)) {
      parts.push(`=== ${file} ===\n${readFileSync(filePath, 'utf-8')}`);
    }
  }

  cachedRules = parts.join('\n\n');
  return cachedRules;
}

/** Сбросить кеш правил (если файлы обновились) */
export function clearRulesCache(): void {
  cachedRules = null;
}

type ModelChoice = 'opus' | 'sonnet';

function modelId(choice: ModelChoice): string {
  return choice === 'opus'
    ? 'claude-opus-4-6'
    : 'claude-sonnet-4-6';
}

/** Вызов Claude API с prompt caching */
export async function askClaude(
  config: AppConfig,
  rolePrompt: string,
  userMessage: string,
  model: ModelChoice = 'sonnet',
  includeRules = true,
): Promise<string> {
  const ai = getClient(config);
  if (!ai) throw new Error('Claude API key not configured');

  // Системный промпт с кешированием
  const systemBlocks: Array<{ type: 'text'; text: string; cache_control?: { type: 'ephemeral' } }> = [
    { type: 'text', text: rolePrompt },
  ];

  if (includeRules) {
    const rules = loadRules();
    systemBlocks.push({
      type: 'text',
      text: rules,
      cache_control: { type: 'ephemeral' },  // Кешируется на 5 мин
    });
  }

  const response = await ai.messages.create({
    model: modelId(model),
    max_tokens: 16000,
    system: systemBlocks,
    messages: [{ role: 'user', content: userMessage }],
  });

  const textBlock = response.content.find((b) => b.type === 'text');
  return textBlock ? textBlock.text : '';
}

/** Вызов Claude API с JSON-ответом */
export async function askClaudeJson<T>(
  config: AppConfig,
  rolePrompt: string,
  userMessage: string,
  model: ModelChoice = 'sonnet',
  includeRules = true,
): Promise<T> {
  const text = await askClaude(config, rolePrompt, userMessage, model, includeRules);

  const jsonMatch = text.match(/```json\s*([\s\S]*?)\s*```/) || text.match(/(\[[\s\S]*\]|\{[\s\S]*\})/);
  if (!jsonMatch) throw new Error('Claude did not return valid JSON');

  return JSON.parse(jsonMatch[1]) as T;
}
