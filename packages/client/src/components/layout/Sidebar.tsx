import { NavLink, useParams, useLocation } from 'react-router-dom';
import { FolderOpen, Image, FileText, Home, Scissors } from 'lucide-react';
import { GenerationPanel } from '../review/GenerationPanel';
import { UpdateNotice } from './UpdateNotice';
import { useGenerationStore } from '@/store/generation';

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-3 px-4 py-2.5 rounded-lg transition-colors ${
    isActive
      ? 'bg-accent text-white'
      : 'text-gray-400 hover:bg-surface-lighter hover:text-gray-200'
  }`;

export function Sidebar() {
  const { id } = useParams();
  const location = useLocation();
  const isOnReview = id && location.pathname.includes('/review');
  const { pendingPhotos, pendingVideos, isFixingPrompts, fixProgress } = useGenerationStore();

  return (
    <aside className="w-64 bg-surface-light border-r border-surface-lighter flex flex-col">
      {/* Лого */}
      <div className="px-4 py-5 border-b border-surface-lighter">
        <h1 className="text-xl font-bold text-white">Flow App</h1>
        <p className="text-xs text-gray-500 mt-1">Производство мультфильмов</p>
      </div>

      {/* Навигация */}
      <nav className="flex-1 p-3 space-y-1">
        <NavLink to="/" className={navLinkClass} end>
          <Home size={18} />
          <span>Проекты</span>
        </NavLink>

        {id && (
          <>
            <div className="pt-3 pb-1 px-4">
              <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">
                Проект
              </span>
            </div>
            <NavLink to={`/projects/${id}/setup`} className={navLinkClass}>
              <FolderOpen size={18} />
              <span>Настройка</span>
            </NavLink>
            <NavLink to={`/projects/${id}/clips`} className={navLinkClass}>
              <FileText size={18} />
              <span>Промпты</span>
            </NavLink>
            <NavLink to={`/projects/${id}/review`} className={navLinkClass}>
              <Image size={18} />
              <span>Производство</span>
            </NavLink>
            <NavLink to={`/projects/${id}/assembly`} className={navLinkClass}>
              <Scissors size={18} />
              <span>Сборка</span>
            </NavLink>

            {/* Панель генерации — только на странице ревью */}
            {isOnReview && (
              <div className="px-1 pt-2">
                <GenerationPanel
                  projectId={id}
                  pendingPhotos={pendingPhotos}
                  pendingVideos={pendingVideos}
                  isFixingPrompts={isFixingPrompts}
                  fixProgress={fixProgress}
                />
              </div>
            )}
          </>
        )}
      </nav>

      {/* Версия и обновления */}
      <div className="border-t border-surface-lighter">
        <UpdateNotice />
      </div>
    </aside>
  );
}
