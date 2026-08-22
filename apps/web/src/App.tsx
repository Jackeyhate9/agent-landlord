import { AdminPage } from './pages/AdminPage';
import { DemoPage } from './pages/DemoPage';
import { HallPage } from './pages/HallPage';
import { JoinPage } from './pages/JoinPage';
import { QueuePage } from './pages/QueuePage';
import { TablePage } from './pages/TablePage';
import type { ComponentType } from 'react';

export function App() {
  const routes: Record<string, ComponentType> = {
    '/table': TablePage,
    '/queue': QueuePage,
    '/hall': HallPage,
    '/join': JoinPage,
    '/admin': AdminPage,
    '/demo': DemoPage,
  };
  const path = location.pathname.replace(/\/$/, '') || '/table';
  const Route = routes[path] ?? TablePage;
  return <Route />;
}
