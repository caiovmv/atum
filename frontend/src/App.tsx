import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { DownloadsEventsProvider } from './contexts/DownloadsEventsContext';
import { ToastProvider } from './contexts/ToastContext';
import { Layout } from './components/Layout';

const Home = lazy(() => import('./pages/Home').then(m => ({ default: m.Home })));
const Search = lazy(() => import('./pages/Search').then(m => ({ default: m.Search })));
const Detail = lazy(() => import('./pages/Detail').then(m => ({ default: m.Detail })));
const Downloads = lazy(() => import('./pages/Downloads').then(m => ({ default: m.Downloads })));
const Wishlist = lazy(() => import('./pages/Wishlist').then(m => ({ default: m.Wishlist })));
const Feeds = lazy(() => import('./pages/Feeds').then(m => ({ default: m.Feeds })));
const Library = lazy(() => import('./pages/Library').then(m => ({ default: m.Library })));
const Radio = lazy(() => import('./pages/Radio').then(m => ({ default: m.Radio })));
const Settings = lazy(() => import('./pages/Settings').then(m => ({ default: m.Settings })));
const Player = lazy(() => import('./pages/Player').then(m => ({ default: m.Player })));
const ReceiverPlayer = lazy(() => import('./pages/ReceiverPlayer').then(m => ({ default: m.ReceiverPlayer })));

function App() {
  return (
    <BrowserRouter>
      <DownloadsEventsProvider>
        <ToastProvider>
          <Suspense fallback={null}>
            <Routes>
              <Route path="/play-receiver/:id" element={<ReceiverPlayer />} />
              <Route path="/" element={<Layout />}>
                <Route index element={<Home />} />
                <Route path="search" element={<Search />} />
                <Route path="detail" element={<Detail />} />
                <Route path="downloads" element={<Downloads />} />
                <Route path="wishlist" element={<Wishlist />} />
                <Route path="feeds" element={<Feeds />} />
                <Route path="library" element={<Library />} />
                <Route path="radio" element={<Radio />} />
                <Route path="settings" element={<Settings />} />
                <Route path="play/:id" element={<Player />} />
              </Route>
            </Routes>
          </Suspense>
        </ToastProvider>
      </DownloadsEventsProvider>
    </BrowserRouter>
  );
}

export default App;
