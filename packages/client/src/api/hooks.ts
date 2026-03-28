import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from './client';

/** Список проектов */
export function useProjects() {
  return useQuery({
    queryKey: ['projects'],
    queryFn: api.getProjects,
  });
}

/** Один проект */
export function useProject(id: string) {
  return useQuery({
    queryKey: ['project', id],
    queryFn: () => api.getProject(id),
    enabled: !!id,
  });
}

/** Создание проекта */
export function useCreateProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ name, nameRu }: { name: string; nameRu: string }) =>
      api.createProject(name, nameRu),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['projects'] }),
  });
}

/** Данные ревью */
export function useReview(projectId: string) {
  return useQuery({
    queryKey: ['review', projectId],
    queryFn: () => api.getReview(projectId),
    enabled: !!projectId,
    refetchInterval: 30_000,  // обновлять каждые 30 сек
  });
}

/** Отправка решений по ревью */
export function useSubmitReview(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ decisions, model }: { decisions: unknown[]; model: 'sonnet' | 'opus' }) =>
      api.submitReview(projectId, decisions, model),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['review'] }),
  });
}

/** Настройки */
export function useSettings() {
  return useQuery({
    queryKey: ['settings'],
    queryFn: api.getSettings,
  });
}

/** Статус активации */
export function useAuthStatus() {
  return useQuery({
    queryKey: ['auth-status'],
    queryFn: api.getAuthStatus,
  });
}

/** Активация приложения */
export function useActivate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (code: string) => api.activate(code),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['auth-status'] }),
  });
}
