import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Chat from '@/pages/Chat';
import Search from '@/pages/Search';
import Index from '@/pages/Index';
import About from '@/pages/About';
import NotFound from '@/pages/NotFound';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Index />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/search" element={<Search />} />
        <Route path="/about" element={<About />} />
        {/* Catch all routes and show NotFound page which redirects to home */}
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Router>
  );
}

export default App;