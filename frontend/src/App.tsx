import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { Detail } from './pages/Detail';
import { Downloads } from './pages/Downloads';
import { Search } from './pages/Search';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Search />} />
          <Route path="detail" element={<Detail />} />
          <Route path="downloads" element={<Downloads />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
