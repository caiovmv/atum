import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { DownloadsEventsProvider } from './contexts/DownloadsEventsContext';
import { ToastProvider } from './contexts/ToastContext';
import { Layout } from './components/Layout';
import { Detail } from './pages/Detail';
import { Downloads } from './pages/Downloads';
import { Feeds } from './pages/Feeds';
import { Home } from './pages/Home';
import { Library } from './pages/Library';
import { Player } from './pages/Player';
import { ReceiverPlayer } from './pages/ReceiverPlayer';
import { Radio } from './pages/Radio';
import { Search } from './pages/Search';
import { Wishlist } from './pages/Wishlist';

function App() {
  return (
    <BrowserRouter>
      <DownloadsEventsProvider>
        <ToastProvider>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="search" element={<Search />} />
          <Route path="detail" element={<Detail />} />
          <Route path="downloads" element={<Downloads />} />
          <Route path="wishlist" element={<Wishlist />} />
          <Route path="feeds" element={<Feeds />} />
          <Route path="library" element={<Library />} />
          <Route path="radio" element={<Radio />} />
          <Route path="play/:id" element={<Player />} />
          <Route path="play-receiver/:id" element={<ReceiverPlayer />} />
        </Route>
      </Routes>
        </ToastProvider>
      </DownloadsEventsProvider>
    </BrowserRouter>
  );
}

export default App;
