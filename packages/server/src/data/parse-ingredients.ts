/**
 * Parse unique character and location references from all_prompts.json ingredients.
 *
 * Handles two path conventions:
 *
 * 1. Structured (flow-app native):
 *    - "references/characters/amin/base.jpeg"        -> character id "amin"
 *    - "references/locations/kitchen/angles/wide.jpg" -> location "kitchen", angle "wide"
 *    - "references/locations/kitchen/base.jpg"        -> location "kitchen", angle "base"
 *
 * 2. Flat (flow-automation legacy):
 *    - "персонажи_hq/char_amin_full.jpeg"            -> character id "amin"
 *    - "sosed_персонажи_hq/simba.jpg"                -> character id "simba"
 *    - "camera_локации_hq/loc_kitchen_wide.png"      -> location "kitchen", angle "wide"
 *    - "*_локации_hq/loc_*"                          -> location
 */

export interface ParsedCharacterRef {
  id: string;
  file: string;
}

export interface ParsedLocationRef {
  id: string;
  angleId: string;
  file: string;
}

export interface ParsedIngredients {
  characters: ParsedCharacterRef[];
  locations: ParsedLocationRef[];
}

interface ClipLike {
  nano_banana_ingredients?: string[];
}

/**
 * Extract character ID from a structured path like "references/characters/amin/base.jpeg"
 */
function parseStructuredCharacter(path: string): string | null {
  const match = path.match(/references\/characters\/([^/]+)\//);
  return match ? match[1] : null;
}

/**
 * Extract location ID and angle from a structured path like
 * "references/locations/kitchen/angles/wide_from_door.jpg" or
 * "references/locations/kitchen/base.jpg"
 */
function parseStructuredLocation(path: string): { id: string; angleId: string } | null {
  // angles path
  const anglesMatch = path.match(/references\/locations\/([^/]+)\/angles\/([^/]+)\.[^.]+$/);
  if (anglesMatch) {
    return { id: anglesMatch[1], angleId: anglesMatch[2] };
  }
  // base path
  const baseMatch = path.match(/references\/locations\/([^/]+)\/base\.[^.]+$/);
  if (baseMatch) {
    return { id: baseMatch[1], angleId: 'base' };
  }
  return null;
}

/**
 * Extract character ID from a flat legacy path like:
 *  "персонажи_hq/char_amin_full.jpeg"  -> "amin"
 *  "sosed_персонажи_hq/simba.jpg"       -> "simba"
 */
function parseFlatCharacter(path: string): string | null {
  // Match paths containing "персонажи" (cyrillic characters folder)
  if (!path.includes('персонажи')) return null;

  const filename = path.split('/').pop();
  if (!filename) return null;

  // Pattern: char_NAME_full.ext or char_NAME.ext
  const charMatch = filename.match(/^char_(.+?)(?:_full)?\.[^.]+$/);
  if (charMatch) {
    return charMatch[1];
  }

  // Pattern: just NAME.ext (e.g. simba.jpg, jamil.png)
  const simpleMatch = filename.match(/^([^.]+)\.[^.]+$/);
  if (simpleMatch) {
    return simpleMatch[1];
  }

  return null;
}

/**
 * Extract location ID and angle from a flat legacy path like:
 *  "camera_локации_hq/loc_amin_porch_from_gate.png" -> id "amin_porch", angle "from_gate"
 *  "camera_локации_hq/loc_kitchen_wide.png"          -> id "kitchen", angle "wide"
 *
 * For flat location paths, we extract the entire identifier as a single location + angle combo
 * since there's no clear separator between location name and angle name.
 */
function parseFlatLocation(path: string): { id: string; angleId: string } | null {
  // Match paths containing "локации" (cyrillic locations folder)
  if (!path.includes('локации')) return null;

  const filename = path.split('/').pop();
  if (!filename) return null;

  // Pattern: loc_LOCATION_ANGLE.ext
  const locMatch = filename.match(/^loc_(.+)\.[^.]+$/);
  if (locMatch) {
    const fullName = locMatch[1];
    // Use the full name as both the location id (for deduplication) and angle
    // The caller can later refine the mapping
    return { id: fullName, angleId: 'base' };
  }

  return null;
}

/**
 * Find the longest common prefix among IDs at underscore-token boundaries.
 * Example: ["amin_room_desk", "amin_room_full", "amin_room_bed"] -> "amin_room"
 */
function longestCommonTokenPrefix(ids: string[]): string {
  if (ids.length === 0) return '';
  if (ids.length === 1) return ids[0];

  const tokensList = ids.map((id) => id.split('_'));
  const minLen = Math.min(...tokensList.map((t) => t.length));
  const prefix: string[] = [];
  for (let i = 0; i < minLen; i++) {
    const token = tokensList[0][i];
    if (tokensList.every((t) => t[i] === token)) {
      prefix.push(token);
    } else {
      break;
    }
  }
  return prefix.join('_');
}

/**
 * Group flat-format locations so different angles of the same place collapse into one location.
 * Structured locations (already parsed with explicit angle) are returned unchanged.
 *
 * Algorithm: within each first-token bucket (size ≥ 2), find the longest common token prefix
 * and use it as the location id, with the remainder as the angle.
 */
function groupFlatLocations(locations: ParsedLocationRef[]): ParsedLocationRef[] {
  const flat: ParsedLocationRef[] = [];
  const structured: ParsedLocationRef[] = [];
  for (const loc of locations) {
    if (loc.file.includes('локации')) {
      flat.push(loc);
    } else {
      structured.push(loc);
    }
  }

  if (flat.length === 0) return structured;

  const byFirstToken = new Map<string, ParsedLocationRef[]>();
  for (const loc of flat) {
    const firstToken = loc.id.split('_')[0];
    const bucket = byFirstToken.get(firstToken);
    if (bucket) {
      bucket.push(loc);
    } else {
      byFirstToken.set(firstToken, [loc]);
    }
  }

  const regrouped: ParsedLocationRef[] = [];
  for (const items of byFirstToken.values()) {
    if (items.length === 1) {
      regrouped.push(items[0]);
      continue;
    }
    const ids = items.map((i) => i.id);
    let root = longestCommonTokenPrefix(ids);
    if (!root) root = ids[0].split('_')[0];
    for (const item of items) {
      const remainder = item.id.slice(root.length).replace(/^_/, '');
      regrouped.push({ id: root, angleId: remainder || 'base', file: item.file });
    }
  }

  return [...structured, ...regrouped];
}

/**
 * Parse all unique character and location references from an array of clips.
 */
export function parseIngredientsFromPrompts(clips: ClipLike[]): ParsedIngredients {
  const charMap = new Map<string, ParsedCharacterRef>();
  const locMap = new Map<string, ParsedLocationRef>();

  for (const clip of clips) {
    const ingredients = clip.nano_banana_ingredients;
    if (!ingredients || !Array.isArray(ingredients)) continue;

    for (const path of ingredients) {
      if (typeof path !== 'string') continue;

      // Try structured format first
      const structChar = parseStructuredCharacter(path);
      if (structChar) {
        const key = `char:${structChar}`;
        if (!charMap.has(key)) {
          charMap.set(key, { id: structChar, file: path });
        }
        continue;
      }

      const structLoc = parseStructuredLocation(path);
      if (structLoc) {
        const key = `loc:${structLoc.id}:${structLoc.angleId}`;
        if (!locMap.has(key)) {
          locMap.set(key, { id: structLoc.id, angleId: structLoc.angleId, file: path });
        }
        continue;
      }

      // Try flat/legacy format
      const flatChar = parseFlatCharacter(path);
      if (flatChar) {
        const key = `char:${flatChar}`;
        if (!charMap.has(key)) {
          charMap.set(key, { id: flatChar, file: path });
        }
        continue;
      }

      const flatLoc = parseFlatLocation(path);
      if (flatLoc) {
        const key = `loc:${flatLoc.id}:${flatLoc.angleId}`;
        if (!locMap.has(key)) {
          locMap.set(key, { id: flatLoc.id, angleId: flatLoc.angleId, file: path });
        }
        continue;
      }

      // Unknown format — skip silently
    }
  }

  return {
    characters: [...charMap.values()],
    locations: groupFlatLocations([...locMap.values()]),
  };
}
