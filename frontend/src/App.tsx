// src/App.tsx
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import DashboardOverview from "./pages/DashboardOverview";

// Mock
const PaperSearch = () => (
  <div className="p-8">
    <h2 className="text-2xl font-bold">Search Papers</h2>
  </div>
);
const AuthorNetwork = () => (
  <div className="p-8">
    <h2 className="text-2xl font-bold">Author Network</h2>
  </div>
);

function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-slate-50 font-sans text-slate-900">
        <Sidebar />
        <main className="flex-1 overflow-auto">
          <Routes>
            <Route path="/" element={<DashboardOverview />} />
            <Route path="/papers" element={<PaperSearch />} />
            <Route path="/authors" element={<AuthorNetwork />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
