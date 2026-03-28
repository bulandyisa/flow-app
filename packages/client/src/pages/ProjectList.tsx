import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, FolderOpen } from 'lucide-react';
import { useProjects, useCreateProject } from '@/api/hooks';

export function ProjectList() {
  const navigate = useNavigate();
  const { data: projects, isLoading } = useProjects();
  const createProject = useCreateProject();
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState('');

  const handleCreate = async () => {
    if (!name.trim()) return;
    const project = await createProject.mutateAsync({
      name: name.trim(),
      nameRu: name.trim(),
    });
    setShowCreate(false);
    setName('');
    navigate(`/projects/${(project as { id: string }).id}/setup`);
  };

  if (isLoading) {
    return <div className="text-gray-400">Загрузка...</div>;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Проекты</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 bg-accent hover:bg-accent-hover rounded-lg transition-colors"
        >
          <Plus size={18} />
          <span>Новый проект</span>
        </button>
      </div>

      {/* Диалог создания */}
      {showCreate && (
        <div className="mb-6 p-4 bg-surface-light rounded-lg border border-surface-lighter">
          <h3 className="text-lg font-medium mb-3">Новый проект</h3>
          <div className="space-y-3">
            <input
              type="text"
              placeholder="Название проекта"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 bg-surface rounded-lg border border-surface-lighter focus:border-accent outline-none"
              autoFocus
            />
            <div className="flex gap-2">
              <button
                onClick={handleCreate}
                disabled={!name.trim()}
                className="px-4 py-2 bg-accent hover:bg-accent-hover rounded-lg transition-colors disabled:opacity-50"
              >
                Создать
              </button>
              <button
                onClick={() => setShowCreate(false)}
                className="px-4 py-2 bg-surface-lighter hover:bg-gray-600 rounded-lg transition-colors"
              >
                Отмена
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Список проектов */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {(projects as Array<{ id: string; nameRu: string; phase: string; updatedAt: string }>)?.map(
          (project) => (
            <button
              key={project.id}
              onClick={() => navigate(`/projects/${project.id}/setup`)}
              className="p-4 bg-surface-light rounded-lg border border-surface-lighter hover:border-accent transition-colors text-left"
            >
              <div className="flex items-center gap-3 mb-2">
                <FolderOpen size={20} className="text-accent" />
                <h3 className="font-medium">{project.nameRu}</h3>
              </div>
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <span className="px-2 py-0.5 bg-surface rounded text-xs">
                  {project.phase}
                </span>
                <span>{new Date(project.updatedAt).toLocaleDateString('ru')}</span>
              </div>
            </button>
          ),
        )}

        {!projects?.length && !showCreate && (
          <p className="text-gray-500 col-span-full">
            Нет проектов. Нажмите "Новый проект" чтобы начать.
          </p>
        )}
      </div>
    </div>
  );
}
