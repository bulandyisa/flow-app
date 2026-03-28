import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/layout/Layout';
import { ProjectList } from './pages/ProjectList';
import { ProjectSetup } from './pages/ProjectSetup';
import { Review } from './pages/Review';
import { Clips } from './pages/Clips';
import { Assembly } from './pages/Assembly';
import { Activate } from './pages/Activate';
import { useAuthStatus } from './api/hooks';

function AuthenticatedApp() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<ProjectList />} />
        <Route path="/projects/:id/setup" element={<ProjectSetup />} />
        <Route path="/projects/:id/clips" element={<Clips />} />
        <Route path="/projects/:id/review" element={<Review />} />
        <Route path="/projects/:id/assembly" element={<Assembly />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

function AppContent() {
  const { data, isLoading } = useAuthStatus();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-surface">
        <div className="text-gray-400 text-lg">Загрузка...</div>
      </div>
    );
  }

  const status = data as { activated: boolean } | undefined;
  if (!status?.activated) {
    return <Activate />;
  }

  return <AuthenticatedApp />;
}

export function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  );
}
