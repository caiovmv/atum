import type React from 'react';
import { lazy, Suspense } from 'react';
import { BrowserRouter, Navigate, Routes, Route } from 'react-router-dom';
import { DownloadsEventsProvider } from './contexts/DownloadsEventsContext';
import { ToastProvider } from './contexts/ToastContext';
import { NowPlayingProvider } from './contexts/NowPlayingContext';
import { FavoritesProvider } from './contexts/FavoritesContext';
import { ErrorBoundary } from './components/ErrorBoundary';
import { Layout } from './components/Layout';
import { PWAUpdatePrompt } from './components/PWAUpdatePrompt';
import { AuthProvider, useAuth } from './contexts/AuthContext';

const Home = lazy(() => import('./pages/Home').then(m => ({ default: m.Home })));
const Search = lazy(() => import('./pages/Search').then(m => ({ default: m.Search })));
const Detail = lazy(() => import('./pages/Detail').then(m => ({ default: m.Detail })));
const Downloads = lazy(() => import('./pages/Downloads').then(m => ({ default: m.Downloads })));
const Wishlist = lazy(() => import('./pages/Wishlist').then(m => ({ default: m.Wishlist })));
const Feeds = lazy(() => import('./pages/Feeds').then(m => ({ default: m.Feeds })));
const Library = lazy(() => import('./pages/Library').then(m => ({ default: m.Library })));
const Radio = lazy(() => import('./pages/Radio').then(m => ({ default: m.Radio })));
const Playlists = lazy(() => import('./pages/Playlists').then(m => ({ default: m.Playlists })));
const PlaylistDetail = lazy(() => import('./pages/PlaylistDetail').then(m => ({ default: m.PlaylistDetail })));
const Settings = lazy(() => import('./pages/Settings').then(m => ({ default: m.Settings })));
const Player = lazy(() => import('./pages/Player').then(m => ({ default: m.Player })));
const ReceiverPlayer = lazy(() => import('./pages/ReceiverPlayer').then(m => ({ default: m.ReceiverPlayer })));
const Login = lazy(() => import('./pages/Login'));
const Register = lazy(() => import('./pages/Register'));
const Account = lazy(() => import('./pages/Account'));

/** Guard: redireciona para /login se não autenticado. */
function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) {
    return <div className="app-loading-fallback"><div className="app-loading-spinner" /></div>;
  }
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <DownloadsEventsProvider>
          <ToastProvider>
            <NowPlayingProvider>
              <FavoritesProvider>
                <ErrorBoundary>
                  <PWAUpdatePrompt />
                  <Suspense fallback={<div className="app-loading-fallback"><div className="app-loading-spinner" /></div>}>
                    <Routes>
                      {/* Rotas públicas de auth */}
                      <Route path="/login" element={<Login />} />
                      <Route path="/register" element={<Register />} />

                      {/* Rotas protegidas */}
                      <Route path="/play-receiver/:id" element={
                        <RequireAuth><ReceiverPlayer /></RequireAuth>
                      } />
                      <Route path="/account" element={
                        <RequireAuth><Account /></RequireAuth>
                      } />

                      <Route path="/" element={
                        <RequireAuth><Layout /></RequireAuth>
                      }>
                        <Route index element={<Home />} />
                        <Route path="search" element={<Search />} />
                        <Route path="detail" element={<Detail />} />
                        <Route path="downloads" element={<Downloads />} />
                        <Route path="wishlist" element={<Wishlist />} />
                        <Route path="feeds" element={<Feeds />} />
                        <Route path="library" element={<Library />} />
                        <Route path="radio" element={<Radio />} />
                        <Route path="playlists" element={<Playlists />} />
                        <Route path="playlists/:id" element={<PlaylistDetail />} />
                        <Route path="settings" element={<Settings />} />
                        <Route path="play/:id" element={<Player />} />
                      </Route>
                    </Routes>
                  </Suspense>
                </ErrorBoundary>
              </FavoritesProvider>
            </NowPlayingProvider>
          </ToastProvider>
        </DownloadsEventsProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
