#!/usr/bin/env node
/**
 * Regroup flat-format locations in an existing project.json so that different angles
 * of the same place collapse into one location with multiple angles.
 *
 * Safe to run only when the project has no uploaded images yet (all locations must
 * have baseImage=null and angles=[]). Refuses to run otherwise.
 *
 * Usage: node migrate-group-locations.mjs <path-to-project.json> [--write]
 */
import { readFileSync, writeFileSync, copyFileSync } from 'fs';
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

const LOC_RU = {
  garazh: 'Гараж',
  amin_room: 'Комната Амина',
  kabinet: 'Кабинет папы',
  kitchen: 'Кухня',
  tower: 'Водонапорная башня',
  tako_room: 'Комната Тако',
  wasteland: 'Пустырь',
  hallway: 'Коридор',
  road_to_tower: 'Дорога к башне',
  alley_dumpsters: 'Переулок с мусорными баками',
  warehouse_interior_bikes: 'Склад с велосипедами',
  school_yard_benches: 'Школьный двор со скамейками',
  dom_outside_front: 'Дом снаружи (фасад)',
};

function titleCase(id) {
  return id.charAt(0).toUpperCase() + id.slice(1).replace(/_/g, ' ');
}

function groupLocations(locations) {
  const byFirstToken = new Map();
  for (const loc of locations) {
    const firstToken = loc.id.split('_')[0];
    const bucket = byFirstToken.get(firstToken);
    if (bucket) bucket.push(loc);
    else byFirstToken.set(firstToken, [loc]);
  }
  const out = [];
  for (const items of byFirstToken.values()) {
    if (items.length === 1) {
      const l = items[0];
      const nameRu = LOC_RU[l.id] || l.nameRu || titleCase(l.id);
      out.push({ ...l, nameRu });
      continue;
    }
    const ids = items.map((i) => i.id);
    const root = longestCommonTokenPrefix(ids) || ids[0].split('_')[0];
    const nameRu = LOC_RU[root] || titleCase(root);
    out.push({
      ...items[0],
      id: root,
      name: titleCase(root),
      nameRu,
      description: `${items.length} ракурс(ов) из промптов`,
    });
  }
  return out;
}

const args = process.argv.slice(2);
const file = args[0];
const write = args.includes('--write');
if (!file) { console.error('Usage: migrate-group-locations.mjs <project.json> [--write]'); process.exit(1); }

const absPath = resolve(file);
const project = JSON.parse(readFileSync(absPath, 'utf-8'));
const locs = project.locations || [];

const dirty = locs.filter((l) => l.baseImage || (l.angles && l.angles.length > 0));
if (dirty.length > 0) {
  console.error(`Refusing: ${dirty.length} location(s) already have uploaded data. Migrate manually.`);
  for (const l of dirty) console.error(`  - ${l.id}`);
  process.exit(2);
}

const before = locs.length;
const grouped = groupLocations(locs);
const after = grouped.length;

console.log(`Before: ${before} locations`);
console.log(`After:  ${after} locations`);
console.log('');
for (const l of grouped) {
  console.log(`  ${l.id.padEnd(30)} — ${l.nameRu || l.name}`);
}

if (write) {
  const backup = absPath + '.bak';
  copyFileSync(absPath, backup);
  project.locations = grouped;
  writeFileSync(absPath, JSON.stringify(project, null, 2), 'utf-8');
  console.log(`\nWritten. Backup: ${backup}`);
} else {
  console.log('\nDry run. Add --write to apply.');
}
