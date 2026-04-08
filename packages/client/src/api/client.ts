const BASE_URL = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(error.error || `HTTP ${res.status}`);
  }

  return res.json();
}

export const api = {
  // Проекты
  getProjects: () => request<unknown[]>('/projects'),
  getProject: (id: string) => request<unknown>(`/projects/${id}`),
  createProject: (name: string, nameRu: string) =>
    request<unknown>('/projects', {
      method: 'POST',
      body: JSON.stringify({ name, nameRu }),
    }),
  updateProject: (id: string, data: unknown) =>
    request<unknown>(`/projects/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  // Клипы и ревью
  getClips: (projectId: string) => request<unknown[]>(`/projects/${projectId}/clips`),
  getReview: (projectId: string, page = 1, limit = 40, filter = 'all', search = '') =>
    request<unknown>(`/projects/${projectId}/review?page=${page}&limit=${limit}&filter=${encodeURIComponent(filter)}&search=${encodeURIComponent(search)}`),
  submitReview: (projectId: string, decisions: unknown[], model: 'sonnet' | 'opus' = 'sonnet') =>
    request<unknown>(`/projects/${projectId}/review/submit`, {
      method: 'POST',
      body: JSON.stringify({ decisions, model }),
    }),
  revokeAccepted: (projectId: string, clipId: string, component: string, feedback?: string) =>
    request<{ success: boolean; fixResult?: { explanation?: string; error?: string } }>(
      `/projects/${projectId}/review/revoke`,
      {
        method: 'POST',
        body: JSON.stringify({ clipId, component, feedback }),
      },
    ),

  // Настройки
  getSettings: () => request<unknown>('/settings'),
  updateSettings: (data: unknown) =>
    request<unknown>('/settings', {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  // Настройка проекта
  uploadScreenplay: async (projectId: string, file: File) => {
    const form = new FormData();
    form.append('file', file);
    const res = await fetch(`${BASE_URL}/setup/${projectId}/screenplay`, { method: 'POST', body: form });
    if (!res.ok) throw new Error((await res.json()).error);
    return res.json();
  },
  getScreenplay: (projectId: string) => request<{ text: string; paragraphs: string[] }>(`/setup/${projectId}/screenplay`),

  addCharacter: async (projectId: string, data: { name: string; nameRu: string; clothing: string; description: string }, image?: File) => {
    const form = new FormData();
    form.append('name', data.name);
    form.append('nameRu', data.nameRu);
    form.append('clothing', data.clothing);
    form.append('description', data.description);
    if (image) form.append('image', image);
    const res = await fetch(`${BASE_URL}/setup/${projectId}/characters`, { method: 'POST', body: form });
    if (!res.ok) throw new Error((await res.json()).error);
    return res.json();
  },
  updateCharacter: (projectId: string, charId: string, data: unknown) =>
    request<unknown>(`/setup/${projectId}/characters/${charId}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteCharacter: (projectId: string, charId: string) =>
    request<unknown>(`/setup/${projectId}/characters/${charId}`, { method: 'DELETE' }),
  uploadCharacterImage: async (projectId: string, charId: string, image: File) => {
    const form = new FormData();
    form.append('image', image);
    const res = await fetch(`${BASE_URL}/setup/${projectId}/characters/${charId}/image`, { method: 'POST', body: form });
    if (!res.ok) throw new Error((await res.json()).error);
    return res.json();
  },

  uploadCharacterAngle: async (projectId: string, charId: string, angleId: string, image: File) => {
    const form = new FormData();
    form.append('image', image);
    form.append('angleId', angleId);
    const res = await fetch(`${BASE_URL}/setup/${projectId}/characters/${charId}/angles`, { method: 'POST', body: form });
    if (!res.ok) throw new Error((await res.json()).error);
    return res.json();
  },
  uploadLocationAngle: async (projectId: string, locId: string, angleId: string, image: File) => {
    const form = new FormData();
    form.append('image', image);
    form.append('angleId', angleId);
    const res = await fetch(`${BASE_URL}/setup/${projectId}/locations/${locId}/angles`, { method: 'POST', body: form });
    if (!res.ok) throw new Error((await res.json()).error);
    return res.json();
  },

  addLocation: async (projectId: string, data: { name: string; nameRu: string; description: string }, image?: File) => {
    const form = new FormData();
    form.append('name', data.name);
    form.append('nameRu', data.nameRu);
    form.append('description', data.description);
    if (image) form.append('image', image);
    const res = await fetch(`${BASE_URL}/setup/${projectId}/locations`, { method: 'POST', body: form });
    if (!res.ok) throw new Error((await res.json()).error);
    return res.json();
  },
  updateLocation: (projectId: string, locId: string, data: unknown) =>
    request<unknown>(`/setup/${projectId}/locations/${locId}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteLocation: (projectId: string, locId: string) =>
    request<unknown>(`/setup/${projectId}/locations/${locId}`, { method: 'DELETE' }),
  uploadLocationImage: async (projectId: string, locId: string, image: File) => {
    const form = new FormData();
    form.append('image', image);
    const res = await fetch(`${BASE_URL}/setup/${projectId}/locations/${locId}/image`, { method: 'POST', body: form });
    if (!res.ok) throw new Error((await res.json()).error);
    return res.json();
  },

  analyzeScreenplay: (projectId: string) =>
    request<{ success: boolean; analysis: unknown; characters: unknown[]; locations: unknown[] }>(
      `/setup/${projectId}/analyze`, { method: 'POST' },
    ),

  uploadPrompts: async (projectId: string, file: File) => {
    const form = new FormData();
    form.append('file', file);
    const res = await fetch(`${BASE_URL}/setup/${projectId}/upload-prompts`, { method: 'POST', body: form });
    if (!res.ok) throw new Error((await res.json()).error);
    return res.json();
  },

  advancePhase: (projectId: string) =>
    request<{ phase: string }>(`/setup/${projectId}/advance`, { method: 'POST' }),

  // Референсы — генерация и ревью
  generateReferences: (
    projectId: string,
    type: 'characters' | 'locations',
    itemId: string,
    target: 'base' | 'angles',
    model: 'sonnet' | 'opus' = 'sonnet',
  ) =>
    request<{
      success: boolean;
      message: string;
      botImplemented: boolean;
      aiGenerated?: boolean;
      model?: string;
      reviewDir?: string;
      angles?: string[];
    }>(`/references/${projectId}/references/generate`, {
      method: 'POST',
      body: JSON.stringify({ type, itemId, target, model }),
    }),

  getReferencesReview: (projectId: string) =>
    request<{
      items: Array<{
        itemId: string;
        type: 'characters' | 'locations';
        name: string;
        nameRu: string;
        target: 'base' | 'angle';
        angleId?: string;
        angleDescription?: string;
        manifest: {
          itemId: string;
          type: string;
          target: string;
          status: string;
          feedback: string;
          attempts: Array<{
            attempt: number;
            prompt: string;
            variants: Array<{ file: string; scores: Record<string, number> | null; avg: number | null }>;
          }>;
          selected_variant: { attempt: number; variant: number } | null;
        };
        variantPaths: string[];
      }>;
    }>(`/references/${projectId}/references/review`),

  startRefBot: (projectId: string, botCount = 1, accounts: number[] = [1], filter?: { characters: string[]; locations: string[]; angles: string[] }) =>
    request<{ success: boolean; botIds: number[]; message: string; errors?: string[] }>(
      `/references/${projectId}/references/start-bot`,
      {
        method: 'POST',
        body: JSON.stringify({ botCount, accounts, filter }),
      },
    ),

  rewriteRejected: (projectId: string, filter?: { characters: string[]; locations: string[] }) =>
    request<{ success: boolean; rewrittenCount: number }>(
      `/references/${projectId}/references/rewrite-rejected`,
      {
        method: 'POST',
        body: JSON.stringify({ filter }),
      },
    ),

  stopRefBot: (projectId: string) =>
    request<{ success: boolean; stopped: number; message: string }>(
      `/references/${projectId}/references/stop-bot`,
      { method: 'POST' },
    ),

  getRefBotStatus: (projectId: string) =>
    request<{
      bots: Array<{
        botId: number;
        running: boolean;
        account: number;
        currentAction: string | null;
        currentClip: string | null;
        completedCount: number;
        errorCount: number;
        startedAt: string | null;
        exitCode: number | null;
      }>;
      running: boolean;
      started: boolean;
      totalCompleted: number;
      totalErrors: number;
    }>(`/references/${projectId}/references/bot-status`),

  submitReferencesReview: (
    projectId: string,
    decisions: Array<{
      itemId: string;
      type: 'characters' | 'locations';
      target: 'base' | 'angle';
      angleId?: string;
      action: 'accept' | 'reject';
      attempt?: number;
      variant?: number;
      feedback?: string;
    }>,
    model: 'sonnet' | 'opus' = 'sonnet',
  ) =>
    request<{
      results: Array<{ itemId: string; target: string; success: boolean; error?: string }>;
      accepted: number;
      rejected: number;
      allReady: boolean;
    }>(`/references/${projectId}/references/review/submit`, {
      method: 'POST',
      body: JSON.stringify({ decisions, model }),
    }),

  // Прямое редактирование промпта
  updateClipPrompt: (projectId: string, clipId: string, component: 'nb_first' | 'veo', prompt: string) =>
    request<{ success: boolean }>('/clips/update', {
      method: 'PATCH',
      body: JSON.stringify({ projectId, clipId, component, prompt }),
    }),

  // Боты
  getBotStatus: () => request<{
    bots: Array<{
      id: number; account: number; isRunning: boolean;
      currentClip: string | null; currentAction: string | null;
      completedCount: number; errorCount: number;
      startedAt: string | null; exitCode: number | null;
    }>;
    pythonFound: boolean;
    botScriptFound: boolean;
    pythonPath: string | null;
    botScriptPath: string | null;
  }>('/bot/status'),

  startBot: (projectId: string, botId: number, account: number) =>
    request<{ success: boolean }>('/bot/start', {
      method: 'POST',
      body: JSON.stringify({ projectId, botId, account }),
    }),

  stopBot: (botId?: number) =>
    request<{ success: boolean }>('/bot/stop', {
      method: 'POST',
      body: JSON.stringify({ botId }),
    }),

  getBotLog: (botId: number, last = 100) =>
    request<{ log: Array<{ timestamp: string; stream: string; text: string }> }>(
      `/bot/log/${botId}?last=${last}`,
    ),

  // Сборка видео
  getAssemblyClips: (projectId: string) =>
    request<{
      clips: Array<{
        clipId: string;
        sceneId: string;
        filename: string;
        filePath: string;
        duration: number | null;
        thumbnail: string | null;
        descriptionRu: string;
      }>;
    }>(`/assembly/${projectId}/clips`),

  exportAssembly: (
    projectId: string,
    timeline: Array<{ filePath: string; startSec: number; endSec: number }>,
    name?: string,
  ) =>
    request<{
      success: boolean;
      export: {
        name: string;
        path: string;
        duration: number;
        clipCount: number;
      };
    }>(`/assembly/${projectId}/export`, {
      method: 'POST',
      body: JSON.stringify({ timeline, name }),
    }),

  getAssemblyExports: (projectId: string) =>
    request<{
      exports: Array<{
        name: string;
        filename: string;
        path: string;
        size: number;
        duration: number | null;
        clipCount: number;
        createdAt: string;
      }>;
    }>(`/assembly/${projectId}/exports`),

  getFFmpegStatus: (projectId: string) =>
    request<{ available: boolean; ffmpeg?: string; ffprobe?: string; error?: string }>(
      `/assembly/${projectId}/ffmpeg-status`,
    ),

  // Медиа URL
  mediaUrl: (projectId: string, path: string) =>
    `${BASE_URL}/media/${projectId}/${path}`,

  // Обновления
  getVersion: () => request<{ version: string; isInstalled: boolean }>('/update/version'),
  checkUpdate: () => request<{
    currentVersion: string;
    latestVersion?: string;
    updateAvailable: boolean;
    releaseName?: string;
    releaseNotes?: string;
    releaseDate?: string;
    releaseUrl?: string;
    message?: string;
  }>('/update/check'),

  // Авторизация
  getAuthStatus: () => request<{ activated: boolean; code: string | null; activatedAt: string | null }>('/auth/status'),
  activate: (code: string) =>
    request<{ success: boolean; name: string; message: string }>('/auth/activate', {
      method: 'POST',
      body: JSON.stringify({ code }),
    }),
};
