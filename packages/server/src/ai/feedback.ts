import type { AppConfig } from '../config.js';
import { askClaudeJson } from './client.js';
import type { Clip } from '@flow-app/shared';

export interface PromptFix {
  clip_id: string;
  component: string;  // "nb_first", "veo"
  old_prompt: string;
  new_prompt: string;
  explanation: string;
}

export interface FixFailure {
  clip_id: string;
  component: string;
  error: string;
}

const ROLE_PROMPT = `You are an expert at writing prompts for 3D Pixar-style animation generation.
Your task: rewrite a prompt based on user feedback.

CRITICAL RULES:
- Follow ALL quality rules from the provided specifications
- NEVER describe character appearance — the model takes it from photo ingredients
- NEVER describe location interiors — the model takes it from photo ingredients
- Identity locking: always reference characters by ingredient number with clothing
- Always end with: "No text, no watermarks. 3D Pixar-style, family-friendly, cinematic."
- For VEO: max 300 characters, describe the video action starting from the first frame

Return ONLY valid JSON:
{
  "clip_id": "...",
  "component": "...",
  "old_prompt": "...",
  "new_prompt": "...",
  "explanation": "Brief explanation of what was changed and why (in Russian)"
}`;

/** Исправляет один промпт по фидбеку */
export async function fixPromptByFeedback(
  config: AppConfig,
  clip: Clip,
  component: string,
  feedback: string,
  sceneContext: string,
  model: 'opus' | 'sonnet' = 'sonnet',
): Promise<PromptFix> {
  const currentPrompt =
    component === 'nb_first' ? clip.nano_banana_prompt_first :
    clip.veo_prompt;

  const userMessage = `Clip: ${clip.clip_id}
Component: ${component}
Scene: ${clip.scene_description_ru}

Current prompt:
${currentPrompt}

Ingredients: ${clip.nano_banana_ingredients.join(', ')}

User feedback:
${feedback}

${sceneContext ? `Scene context:\n${sceneContext}` : ''}

Rewrite the prompt based on the feedback. Keep everything that works, fix what the user pointed out.`;

  return askClaudeJson<PromptFix>(config, ROLE_PROMPT, userMessage, model, true);
}

/** Исправляет несколько промптов пакетно, продолжая при ошибках отдельных промптов */
export async function fixPromptsBatch(
  config: AppConfig,
  fixes: Array<{
    clip: Clip;
    component: string;
    feedback: string;
    sceneContext: string;
  }>,
  model: 'opus' | 'sonnet' = 'sonnet',
  onProgress?: (done: number, total: number) => void,
): Promise<{ successes: PromptFix[]; failures: FixFailure[] }> {
  const successes: PromptFix[] = [];
  const failures: FixFailure[] = [];

  for (let i = 0; i < fixes.length; i++) {
    const { clip, component, feedback, sceneContext } = fixes[i];
    try {
      const fix = await fixPromptByFeedback(config, clip, component, feedback, sceneContext, model);
      successes.push(fix);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      failures.push({
        clip_id: clip.clip_id,
        component,
        error: message,
      });
    }
    onProgress?.(i + 1, fixes.length);
  }

  return { successes, failures };
}
