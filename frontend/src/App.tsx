import { BrowserRouter, Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import DashboardOverview from "./pages/DashboardOverview";
import PaperSearch from "./pages/PaperSearch";
import AuthorNetwork from "./pages/AuthorNetwork";
import PaperDetail from "./pages/PaperDetail";

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
            <Route path="/papers/:id" element={<PaperDetail />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
