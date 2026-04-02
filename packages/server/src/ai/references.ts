import { readFileSync, existsSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import type { AppConfig } from '../config.js';
import { getClient } from './client.js';

// Кешированные правила для ракурсов
let cachedAngleRules: string | null = null;

/** Загружает правила angle-generation.md + quality-rules.md */
function loadRefRules(): string {
  if (cachedAngleRules) return cachedAngleRules;

  const __dirname = dirname(fileURLToPath(import.meta.url));
  const rulesDir = resolve(__dirname, '../../../..', 'rules');
  const files = ['quality-rules.md', 'angle-generation.md', 'prompt-spec.md'];
  const parts: string[] = [];

  for (const file of files) {
    const filePath = resolve(rulesDir, file);
    if (existsSync(filePath)) {
      parts.push(`=== ${file} ===\n${readFileSync(filePath, 'utf-8')}`);
    }
  }

  cachedAngleRules = parts.join('\n\n');
  return cachedAngleRules;
}

// ─── System prompts ─────────────────────────────────────

const BASE_CHARACTER_SYSTEM = `You are an expert prompt writer for 3D Pixar-style character generation using Nano Banana Pro.

Your task: write a prompt for generating a BASE IMAGE of a character.

CRITICAL RULES:
- The prompt will be used in Nano Banana Pro to generate a full-body character reference image.
- NEVER describe physical appearance details (face shape, eye color, skin tone) — the model takes appearance from photo references if provided.
- Describe ONLY: pose, clothing details, expression, art style, and composition.
- Identity locking: always mention the character's signature clothing.
- Always end with: "No text, no watermarks. 3D Pixar-style, family-friendly, cinematic."
- Keep it concise but descriptive (2-4 sentences).
- Output ONLY the prompt text, nothing else. No quotes, no prefixes, no explanation.`;

const BASE_LOCATION_SYSTEM = `You are an expert prompt writer for 3D Pixar-style location generation using Nano Banana Pro.

Your task: write a prompt for generating a BASE IMAGE of a location.

CRITICAL RULES:
- The prompt will be used in Nano Banana Pro to generate a wide establishing shot of the location.
- Describe the location's atmosphere, lighting, key architectural features, and mood.
- Do NOT describe specific furniture placement in detail — the model will create its own consistent interior.
- Focus on: overall style, lighting mood, color palette, architectural style, time of day.
- Always end with: "No text, no watermarks. 3D Pixar-style, family-friendly, cinematic."
- Keep it concise but evocative (2-4 sentences).
- Output ONLY the prompt text, nothing else. No quotes, no prefixes, no explanation.`;

const ANGLE_CHARACTER_SYSTEM = `You are an expert prompt writer for 3D Pixar-style character angle generation using Nano Banana Pro.

Your task: write a prompt for generating a specific ANGLE/POSE of a character.
The base image of the character is provided as Image 1 (ingredient). Your prompt must ensure the generated image is IDENTICAL to the base in every way except the camera angle/pose.

CRITICAL RULES:
- Start with: "The EXACT same character from Image 1 — same face, same body proportions, same clothing, same hairstyle, same accessories. IDENTICAL appearance."
- Then describe ONLY the new camera angle or pose.
- NEVER add new details, accessories, or clothing not in the base image.
- NEVER use words like "similar", "like", "inspired by" — only "EXACT same", "IDENTICAL".
- Always end with: "No text, no watermarks. 3D Pixar-style, family-friendly, cinematic."
- Output ONLY the prompt text, nothing else. No quotes, no prefixes, no explanation.`;

const ANGLE_LOCATION_SYSTEM = `You are an expert prompt writer for 3D Pixar-style location angle generation using Nano Banana Pro.

Your task: write a prompt for generating a specific CAMERA ANGLE of a location.
The base image of the location is provided as Image 1 (ingredient). Your prompt must ensure the generated image reproduces the EXACT same location with only the camera position changed.

CRITICAL RULES:
- Start with: "Reproduce the EXACT same location from Image 1 — same walls, same floor, same furniture, same objects, same colors, same textures, same lighting. NOTHING added, NOTHING removed, NOTHING changed."
- Then describe the specific camera angle/position.
- Emphasize: "The location must be IDENTICAL to Image 1 in every detail. Only the camera position and angle change."
- NEVER add new objects, change lighting, or alter any detail.
- NEVER use words like "similar", "like", "inspired by" — only "EXACT same", "IDENTICAL".
- Always end with: "No text, no watermarks. 3D Pixar-style, family-friendly, cinematic."
- Output ONLY the prompt text, nothing else. No quotes, no prefixes, no explanation.`;

const FEEDBACK_SYSTEM = `You are an expert prompt writer for 3D Pixar-style generation using Nano Banana Pro.

Your task: rewrite a prompt based on user feedback. The user rejected the generated image and provided specific feedback on what needs to change.

CRITICAL RULES:
- Keep everything that works in the original prompt.
- Fix ONLY what the user pointed out in their feedback.
- Maintain the same format and style as the original prompt.
- NEVER describe physical appearance — the model takes it from photo ingredients.
- NEVER describe location interiors in detail — the model takes it from the base image ingredient.
- Always keep the ending: "No text, no watermarks. 3D Pixar-style, family-friendly, cinematic."
- For angle prompts, always maintain consistency instructions ("EXACT same", "IDENTICAL").
- Output ONLY the rewritten prompt text, nothing else. No quotes, no prefixes, no explanation.`;

// ─── Public API ─────────────────────────────────────────

type ModelChoice = 'opus' | 'sonnet';

/** Проверяет доступен ли Claude API */
export function isClaudeAvailable(config: AppConfig): boolean {
  return getClient(config) !== null;
}

/** Генерация промпта для базового образа через Claude */
export async function generateBasePrompt(
  config: AppConfig,
  type: 'characters' | 'locations',
  name: string,
  description: string,
  model: ModelChoice = 'sonnet',
): Promise<string> {
  const system = type === 'characters' ? BASE_CHARACTER_SYSTEM : BASE_LOCATION_SYSTEM;
  const rules = loadRefRules();

  const userMessage = type === 'characters'
    ? `Character name: ${name}\nDescription: ${description}\n\nWrite the generation prompt for this character's base image (full body, front view, neutral pose).`
    : `Location name: ${name}\nDescription: ${description}\n\nWrite the generation prompt for this location's base image (wide establishing shot).`;

  const result = await askClaudeWithRefRules(config, system, rules, userMessage, model);
  return result.trim();
}

/** Генерация промпта для ракурса через Claude */
export async function generateAnglePrompt(
  config: AppConfig,
  type: 'characters' | 'locations',
  name: string,
  angleDescription: string,
  model: ModelChoice = 'sonnet',
): Promise<string> {
  const system = type === 'characters' ? ANGLE_CHARACTER_SYSTEM : ANGLE_LOCATION_SYSTEM;
  const rules = loadRefRules();

  const userMessage = type === 'characters'
    ? `Character: ${name}\nAngle/Pose to generate: ${angleDescription}\n\nWrite the prompt. Remember: Image 1 contains the base image of this character.`
    : `Location: ${name}\nCamera angle to generate: ${angleDescription}\n\nWrite the prompt. Remember: Image 1 contains the base image of this location.`;

  const result = await askClaudeWithRefRules(config, system, rules, userMessage, model);
  return result.trim();
}

/** Переписать промпт с учётом фидбека */
export async function rewritePromptWithFeedback(
  config: AppConfig,
  originalPrompt: string,
  feedback: string,
  type: 'characters' | 'locations',
  model: ModelChoice = 'sonnet',
): Promise<string> {
  const rules = loadRefRules();

  const userMessage = `Type: ${type}

Original prompt:
${originalPrompt}

User feedback (reason for rejection):
${feedback}

Rewrite the prompt addressing the feedback. Keep everything that works, fix what was pointed out.`;

  const result = await askClaudeWithRefRules(config, FEEDBACK_SYSTEM, rules, userMessage, model);
  return result.trim();
}

// ─── Internal helper ────────────────────────────────────

/** Вызов Claude API с правилами референсов (prompt caching) */
async function askClaudeWithRefRules(
  config: AppConfig,
  rolePrompt: string,
  rules: string,
  userMessage: string,
  model: ModelChoice,
): Promise<string> {
  const ai = getClient(config);
  if (!ai) throw new Error('Claude API key not configured');

  const modelId = model === 'opus'
    ? 'claude-opus-4-6-latest'
    : 'claude-sonnet-4-5-20241022';

  const response = await ai.messages.create({
    model: modelId,
    max_tokens: 4096,
    system: [
      { type: 'text', text: rolePrompt },
      {
        type: 'text',
        text: rules,
        cache_control: { type: 'ephemeral' },
      },
    ],
    messages: [{ role: 'user', content: userMessage }],
  });

  const textBlock = response.content.find((b) => b.type === 'text');
  return textBlock ? textBlock.text : '';
}
