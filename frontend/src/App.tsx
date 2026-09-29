import { useEffect, useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { LandingPage } from './components/LandingPage';
import { Workspace } from './components/Workspace';

const queryClient = new QueryClient();

export function App() {
  const [currentPath, setCurrentPath] = useState<string>(window.location.pathname);

  useEffect(() => {
    const onLocationChange = () => {
      setCurrentPath(window.location.pathname);
    };

    window.addEventListener('popstate', onLocationChange);
    return () => window.removeEventListener('popstate', onLocationChange);
  }, []);

  const navigateTo = (path: string) => {
    window.history.pushState(null, '', path);
    setCurrentPath(path);
  };

  return (
    <QueryClientProvider client={queryClient}>
      {currentPath === '/workspace' || window.location.search.includes('project=') ? (
        <Workspace />
      ) : (
        <LandingPage onGetStarted={() => navigateTo('/workspace')} />
      )}
    </QueryClientProvider>
  );
}

export default App;
