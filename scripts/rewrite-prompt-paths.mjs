#!/usr/bin/env node
/**
 * Rewrite ingredient paths in all_prompts.json from flat legacy format to the
 * structured format that flow-app parses with proper location/angle grouping.
 *
 * Flat:
 *   локации_hq/loc_amin_room_desk.jpg
 *   персонажи_hq/char_amin_full.jpeg
 *
 * Structured:
 *   references/locations/amin_room/angles/desk.jpg
 *   references/characters/amin/base.jpeg
 *
 * Locations with multiple files sharing a token prefix are grouped under that prefix.
 * Singletons keep their full name as location id with angle "base".
 *
 * Usage: node rewrite-prompt-paths.mjs <input.json> <output.json>
 */
import { readFileSync, writeFileSync } from 'fs';
import { resolve } from 'path';

function longestCommonTokenPrefix(ids) {
  if (ids.length === 0) return '';
  if (ids.length === 1) return ids[0];
  const tokensList = ids.map((id) => id.split('_'));
  const minLen = Math.min(...tokensList.map((t) => t.length));
  const prefix = [];
  for (let i = 0; i < minLen; i++) {
    const token = tokensList[0][i];
    if (tokensList.every((t) => t[i] === token)) prefix.push(token);
    else break;
  }
  return prefix.join('_');
}

/** First pass: collect all unique loc_NAME identifiers to decide roots. */
function collectLocationIds(clips) {
  const ids = new Set();
  for (const clip of clips) {
    for (const path of clip.nano_banana_ingredients || []) {
      if (typeof path !== 'string' || !path.includes('локации')) continue;
      const filename = path.split('/').pop();
      const m = filename && filename.match(/^loc_(.+)\.[^.]+$/);
      if (m) ids.add(m[1]);
    }
  }
  return [...ids];
}

/** Build mapping: full loc id -> { root, angle } */
function buildLocationMapping(ids) {
  const byFirst = new Map();
  for (const id of ids) {
    const first = id.split('_')[0];
    const bucket = byFirst.get(first);
    if (bucket) bucket.push(id);
    else byFirst.set(first, [id]);
  }
  const mapping = new Map();
  for (const bucket of byFirst.values()) {
    if (bucket.length === 1) {
      mapping.set(bucket[0], { root: bucket[0], angle: 'base' });
      continue;
    }
    const root = longestCommonTokenPrefix(bucket) || bucket[0].split('_')[0];
    for (const id of bucket) {
      const angle = id.slice(root.length).replace(/^_/, '') || 'base';
      mapping.set(id, { root, angle });
    }
  }
  return mapping;
}

function rewritePath(path, locMap) {
  if (typeof path !== 'string') return path;
  const filename = path.split('/').pop();
  const ext = filename.includes('.') ? filename.split('.').pop() : 'jpg';

  // Character path
  if (path.includes('персонажи')) {
    let charId;
    const m = filename.match(/^char_(.+?)(?:_full)?\.[^.]+$/);
    if (m) charId = m[1];
    else charId = filename.replace(/\.[^.]+$/, '');
    return `references/characters/${charId}/base.${ext}`;
  }

  // Location path
  if (path.includes('локации')) {
    const m = filename.match(/^loc_(.+)\.[^.]+$/);
    if (!m) return path;
    const entry = locMap.get(m[1]);
    if (!entry) return path;
    return `references/locations/${entry.root}/angles/${entry.angle}.${ext}`;
  }

  return path;
}

const [, , inPath, outPath] = process.argv;
if (!inPath || !outPath) {
  console.error('Usage: rewrite-prompt-paths.mjs <input.json> <output.json>');
  process.exit(1);
}

const clips = JSON.parse(readFileSync(resolve(inPath), 'utf-8'));
if (!Array.isArray(clips)) {
  console.error('Input must be an array of clips');
  process.exit(2);
}

const locIds = collectLocationIds(clips);
const locMap = buildLocationMapping(locIds);

const roots = new Map();
for (const { root, angle } of locMap.values()) {
  if (!roots.has(root)) roots.set(root, new Set());
  roots.get(root).add(angle);
}

console.log(`Found ${locIds.length} unique location files -> ${roots.size} grouped locations:`);
for (const [root, angles] of [...roots.entries()].sort()) {
  console.log(`  ${root}: [${[...angles].sort().join(', ')}]`);
}

let changed = 0;
for (const clip of clips) {
  const ing = clip.nano_banana_ingredients;
  if (!Array.isArray(ing)) continue;
  for (let i = 0; i < ing.length; i++) {
    const before = ing[i];
    const after = rewritePath(before, locMap);
    if (after !== before) {
      ing[i] = after;
      changed++;
    }
  }
}

writeFileSync(resolve(outPath), JSON.stringify(clips, null, 2), 'utf-8');
console.log(`\nRewrote ${changed} path(s). Wrote: ${outPath}`);
