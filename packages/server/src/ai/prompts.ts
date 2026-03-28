import type { AppConfig } from '../config.js';
import { askClaudeJson } from './client.js';
import type { Clip } from '@flow-app/shared';
import type { Character, Location } from '@flow-app/shared';

const ROLE_PROMPT = `You are an expert at breaking screenplays into animation clips and writing prompts for 3D Pixar-style generation using NB Pro and VEO.

Your task: given a screenplay scene, characters, and locations with their angles, create a list of clips with prompts.

Each clip must have:
- clip_id: "SC{number}_{letter}" (e.g. SC001_A, SC001_B)
- scene_id: "SC{number}" (same SC = same camera angle/location/characters)
- scene_description_ru: brief scene description in Russian
- nano_banana_ingredients: array of file paths to character and location images
- nano_banana_prompt_first: prompt for the first frame (used as the basis for VEO video generation)
- veo_prompt: max 300 chars, describes the video action starting from the first frame
- veo_mode: always "frames"
- veo_variant_count: always 4

Follow ALL quality rules and cinematographic techniques from the provided specifications.

Return ONLY valid JSON array of clips.`;

/** Генерирует промпты для одной сцены — использует Opus */
export async function generateScenePrompts(
  config: AppConfig,
  sceneText: string,
  sceneNumber: number,
  characters: Character[],
  locations: Location[],
  startSC: number,
): Promise<Clip[]> {
  const charList = characters.map((c) => {
    const angles = c.angles.map((a) => a.file).join(', ');
    return `- ${c.nameRu} (${c.name}): clothing="${c.clothing}", base=${c.baseImage}, angles=[${angles}]`;
  }).join('\n');

  const locList = locations.map((l) => {
    const angles = l.angles.map((a) => `${a.id}: ${a.file}`).join(', ');
    return `- ${l.nameRu} (${l.name}): base=${l.baseImage}, angles=[${angles}]`;
  }).join('\n');

  const userMessage = `Scene ${sceneNumber}:
${sceneText}

Available characters:
${charList}

Available locations with angles:
${locList}

Start numbering from SC${String(startSC).padStart(3, '0')}.

Create clips for this scene. Use specific angle files from the available locations.
Alternate camera angles — NEVER two clips in a row from the same angle.
Add cutaway/insert shots every 4-6 dialogue clips.`;

  return askClaudeJson<Clip[]>(config, ROLE_PROMPT, userMessage, 'opus', true);
}
