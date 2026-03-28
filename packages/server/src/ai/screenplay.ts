import type { AppConfig } from '../config.js';
import { askClaudeJson } from './client.js';

export interface ExtractedCharacter {
  name: string;
  nameRu: string;
  clothing: string;
  description: string;
}

export interface ExtractedLocation {
  name: string;
  nameRu: string;
  description: string;
}

export interface ScreenplayAnalysis {
  characters: ExtractedCharacter[];
  locations: ExtractedLocation[];
  sceneCount: number;
  summary: string;
}

const ROLE_PROMPT = `You are an expert screenplay analyst for animated 3D Pixar-style cartoons.
Analyze the screenplay and extract ALL characters and locations mentioned.

For each character provide:
- name: English name (lowercase, no spaces for ID)
- nameRu: Russian name from the screenplay
- clothing: distinctive clothing for identity locking (e.g. "in the grey hoodie")
- description: brief description

For each location provide:
- name: English name (lowercase, underscores for ID)
- nameRu: Russian name from the screenplay
- description: detailed visual description for image generation

Return ONLY valid JSON:
{
  "characters": [...],
  "locations": [...],
  "sceneCount": <number>,
  "summary": "<1-2 sentence summary in Russian>"
}`;

/** Анализирует сценарий — использует Opus (сложная задача) */
export async function analyzeScreenplay(
  config: AppConfig,
  screenplayText: string,
): Promise<ScreenplayAnalysis> {
  return askClaudeJson<ScreenplayAnalysis>(
    config,
    ROLE_PROMPT,
    `Проанализируй этот сценарий и извлеки всех персонажей и локации:\n\n${screenplayText}`,
    'opus',
    true,  // включить правила
  );
}
