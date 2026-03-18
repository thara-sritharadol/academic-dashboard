import {
  BrowserRouter,
  Routes,
  Route,
  Link,
  useLocation,
} from "react-router-dom";
import { LayoutDashboard, BookOpen, Users } from "lucide-react";

function Sidebar() {
  const location = useLocation();
  const menuItems = [
    { path: "/", name: "Overview", icon: LayoutDashboard },
    { path: "/papers", name: "Paper Search", icon: BookOpen },
    { path: "/authors", name: "Author Network", icon: Users },
  ];

  return (
    <nav className="w-64 bg-white border-r border-slate-200 min-h-screen p-4 flex flex-col">
      <div className="mb-8 px-4">
        <h1 className="text-2xl font-bold text-blue-600">Topic Dash</h1>
        <p className="text-sm text-slate-500">Research Analytics</p>
      </div>
      <ul className="space-y-2 flex-1">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path;
          return (
            <li key={item.path}>
              <Link
                to={item.path}
                className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                  isActive
                    ? "bg-blue-50 text-blue-700 font-medium"
                    : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                }`}
              >
                <Icon size={20} />
                {item.name}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

// Blank Page for Test
const DashboardOverview = () => (
  <div className="p-8">
    <h2 className="text-2xl font-bold">Dashboard Overview</h2>
  </div>
);
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

        {/* The main area for displaying each page. */}
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
