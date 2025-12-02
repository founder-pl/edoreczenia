import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth.jsx';
import { foldersApi } from '../services/api.jsx';
import { 
  Inbox, Send, FileText, Trash2, Archive, Settings, 
  LogOut, Menu, X, PenSquare, Mail, User, Bell, BookOpen, Link2
} from 'lucide-react';
import { useState, useEffect } from 'react';

const navigationConfig = [
  { name: 'Odebrane', href: '/inbox', icon: Inbox, folderId: 'inbox' },
  { name: 'Wysłane', href: '/sent', icon: Send, folderId: 'sent' },
  { name: 'Robocze', href: '/drafts', icon: FileText, folderId: 'drafts' },
  { name: 'Kosz', href: '/trash', icon: Trash2, folderId: 'trash' },
  { name: 'Archiwum', href: '/archive', icon: Archive, folderId: 'archive' },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [folderCounts, setFolderCounts] = useState({});

  useEffect(() => {
    loadFolderCounts();
  }, []);

  const loadFolderCounts = async () => {
    try {
      const response = await foldersApi.getAll();
      const counts = {};
      response.data.forEach(folder => {
        counts[folder.id] = folder.unread_count || 0;
      });
      setFolderCounts(counts);
    } catch (error) {
      console.error('Error loading folder counts:', error);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-pp-dark text-white sticky top-0 z-50">
        <div className="flex items-center justify-between px-4 py-3">
          {/* Logo & Mobile menu */}
          <div className="flex items-center gap-4">
            <button 
              className="lg:hidden p-2 hover:bg-white/10 rounded-lg"
              onClick={() => setSidebarOpen(!sidebarOpen)}
            >
              {sidebarOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
            <Link to="/" className="flex items-center gap-3">
              <div className="w-10 h-10 bg-pp-red rounded-lg flex items-center justify-center">
                <Mail size={24} />
              </div>
              <div className="hidden sm:block">
                <span className="text-pp-red font-bold text-xl">e-</span>
                <span className="font-bold text-xl">Doręczenia</span>
                <span className="text-xs text-gray-400 block">SaaS Panel</span>
              </div>
            </Link>
          </div>

          {/* Search */}
          <div className="hidden md:flex flex-1 max-w-xl mx-8">
            <input
              type="search"
              placeholder="Szukaj wiadomości..."
              className="w-full px-4 py-2 rounded-full bg-white/10 border border-white/20 
                         text-white placeholder-gray-400 focus:outline-none focus:bg-white/20"
            />
          </div>

          {/* User menu */}
          <div className="flex items-center gap-4">
            <button className="p-2 hover:bg-white/10 rounded-lg relative">
              <Bell size={20} />
              <span className="absolute top-1 right-1 w-2 h-2 bg-pp-red rounded-full"></span>
            </button>
            <div className="hidden sm:flex items-center gap-3">
              <div className="text-right">
                <div className="font-medium text-sm">{user?.name}</div>
                <div className="text-xs text-gray-400">{user?.address}</div>
              </div>
              <div className="w-10 h-10 bg-pp-red rounded-full flex items-center justify-center">
                <User size={20} />
              </div>
            </div>
            <button 
              onClick={handleLogout}
              className="p-2 hover:bg-white/10 rounded-lg"
              title="Wyloguj"
            >
              <LogOut size={20} />
            </button>
          </div>
        </div>
      </header>

      <div className="flex">
        {/* Sidebar */}
        <aside className={`
          fixed lg:static inset-y-0 left-0 z-40 w-64 bg-white border-r border-gray-200
          transform transition-transform duration-300 ease-in-out
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
          pt-16 lg:pt-0
        `}>
          <div className="p-4">
            {/* Compose button */}
            <Link
              to="/compose"
              className="flex items-center justify-center gap-2 w-full btn-primary py-3 mb-6"
            >
              <PenSquare size={20} />
              <span>Nowa wiadomość</span>
            </Link>

            {/* Navigation */}
            <nav className="space-y-1">
              {navigationConfig.map((item) => {
                const isActive = location.pathname === item.href;
                const unreadCount = folderCounts[item.folderId] || 0;
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    onClick={() => setSidebarOpen(false)}
                    className={`
                      flex items-center gap-3 px-4 py-3 rounded-xl transition-colors
                      ${isActive 
                        ? 'bg-pp-red/10 text-pp-red font-medium' 
                        : 'text-gray-700 hover:bg-gray-100'
                      }
                    `}
                  >
                    <item.icon size={20} />
                    <span className="flex-1">{item.name}</span>
                    {unreadCount > 0 && (
                      <span className="bg-pp-red text-white text-xs px-2 py-0.5 rounded-full">
                        {unreadCount}
                      </span>
                    )}
                  </Link>
                );
              })}
            </nav>

            {/* Settings & Guide links */}
            <div className="mt-8 pt-4 border-t border-gray-200 space-y-1">
              <Link
                to="/integrations"
                onClick={() => setSidebarOpen(false)}
                className={`
                  flex items-center gap-3 px-4 py-3 rounded-xl transition-colors
                  ${location.pathname === '/integrations'
                    ? 'bg-pp-red/10 text-pp-red font-medium'
                    : 'text-gray-700 hover:bg-gray-100'
                  }
                `}
              >
                <Link2 size={20} />
                <span>Integracje</span>
              </Link>
              <Link
                to="/guide"
                onClick={() => setSidebarOpen(false)}
                className={`
                  flex items-center gap-3 px-4 py-3 rounded-xl transition-colors
                  ${location.pathname === '/guide'
                    ? 'bg-pp-red/10 text-pp-red font-medium'
                    : 'text-gray-700 hover:bg-gray-100'
                  }
                `}
              >
                <BookOpen size={20} />
                <span>Przewodnik</span>
              </Link>
              <Link
                to="/settings"
                onClick={() => setSidebarOpen(false)}
                className={`
                  flex items-center gap-3 px-4 py-3 rounded-xl transition-colors
                  ${location.pathname === '/settings'
                    ? 'bg-pp-red/10 text-pp-red font-medium'
                    : 'text-gray-700 hover:bg-gray-100'
                  }
                `}
              >
                <Settings size={20} />
                <span>Ustawienia</span>
              </Link>
            </div>

            {/* Integration status */}
            <div className="mt-8 p-4 bg-gray-50 rounded-xl">
              <h4 className="text-xs font-semibold text-gray-500 uppercase mb-3">
                Status integracji
              </h4>
              <div className="space-y-2 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">Proxy IMAP</span>
                  <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">Sync</span>
                  <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">DSL</span>
                  <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                </div>
              </div>
            </div>
          </div>
        </aside>

        {/* Overlay for mobile */}
        {sidebarOpen && (
          <div 
            className="fixed inset-0 bg-black/50 z-30 lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        {/* Main content */}
        <main className="flex-1 min-h-[calc(100vh-64px)]">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
