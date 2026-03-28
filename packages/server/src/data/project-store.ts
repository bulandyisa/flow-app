import { readFileSync, writeFileSync, existsSync, mkdirSync, readdirSync } from 'node:fs';
import { resolve } from 'node:path';
import { v4 as uuid } from 'uuid';
import type { Project } from '@flow-app/shared';

export class ProjectStore {
  private baseDir: string;

  constructor(dataDir: string) {
    this.baseDir = resolve(dataDir, 'projects');
    if (!existsSync(this.baseDir)) mkdirSync(this.baseDir, { recursive: true });
  }

  /** Путь к директории проекта */
  projectDir(projectId: string): string {
    return resolve(this.baseDir, projectId);
  }

  /** Путь к project.json */
  private projectFile(projectId: string): string {
    return resolve(this.projectDir(projectId), 'project.json');
  }

  /** Список всех проектов */
  list(): Project[] {
    if (!existsSync(this.baseDir)) return [];
    const dirs = readdirSync(this.baseDir, { withFileTypes: true })
      .filter((d) => d.isDirectory());

    const projects: Project[] = [];
    for (const dir of dirs) {
      const file = resolve(this.baseDir, dir.name, 'project.json');
      if (existsSync(file)) {
        projects.push(JSON.parse(readFileSync(file, 'utf-8')));
      }
    }
    return projects.sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
  }

  /** Получить проект по ID */
  get(projectId: string): Project | null {
    const file = this.projectFile(projectId);
    if (!existsSync(file)) return null;
    return JSON.parse(readFileSync(file, 'utf-8'));
  }

  /** Создать новый проект */
  create(name: string, nameRu: string): Project {
    const id = uuid();
    const now = new Date().toISOString();
    const project: Project = {
      id,
      name,
      nameRu,
      style: '3D Pixar-style',
      phase: 'screenplay',
      characters: [],
      locations: [],
      seating: {},
      screenplayFile: null,
      createdAt: now,
      updatedAt: now,
    };

    // Создаём структуру директорий
    const dir = this.projectDir(id);
    const subdirs = [
      'prompts', 'references/characters', 'references/locations',
      'review', 'frames', 'clips',
    ];
    for (const sub of subdirs) {
      mkdirSync(resolve(dir, sub), { recursive: true });
    }

    this.save(project);
    return project;
  }

  /** Сохранить проект */
  save(project: Project): void {
    project.updatedAt = new Date().toISOString();
    const file = this.projectFile(project.id);
    writeFileSync(file, JSON.stringify(project, null, 2), 'utf-8');
  }
}
