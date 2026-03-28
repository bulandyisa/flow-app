import { create } from 'zustand';

interface GenerationState {
  /** Количество pending фото */
  pendingPhotos: number;
  /** Количество pending видео */
  pendingVideos: number;
  /** Идёт исправление промптов */
  isFixingPrompts: boolean;
  /** Прогресс: [готово, всего] */
  fixProgress: [number, number];

  setPending: (photos: number, videos: number) => void;
  startFixing: (total: number) => void;
  updateFixProgress: (done: number) => void;
  finishFixing: () => void;
}

export const useGenerationStore = create<GenerationState>((set) => ({
  pendingPhotos: 0,
  pendingVideos: 0,
  isFixingPrompts: false,
  fixProgress: [0, 0],

  setPending: (photos, videos) => set({ pendingPhotos: photos, pendingVideos: videos }),

  startFixing: (total) => set({ isFixingPrompts: true, fixProgress: [0, total] }),

  updateFixProgress: (done) => set((s) => ({ fixProgress: [done, s.fixProgress[1]] })),

  finishFixing: () => set({ isFixingPrompts: false, fixProgress: [0, 0] }),
}));
