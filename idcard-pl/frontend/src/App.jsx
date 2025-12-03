import { BrowserRouter, Routes, Route, Navigate, Link, useLocation, useParams } from 'react-router-dom';
import { useState, useEffect, createContext, useContext } from 'react';
import { 
  Home, Mail, FileText, Settings, LogOut, Menu, X, Bell,
  Link2, CheckCircle, Clock, AlertCircle, ChevronRight,
  Building, User, CreditCard, Shield
} from 'lucide-react';

// ═══════════════════════════════════════════════════════════════
// API SERVICE
// ═══════════════════════════════════════════════════════════════

const API_URL = '/api';

const api = {
  async request(endpoint, options = {}) {
    const token = localStorage.getItem('idcard_token');
    const headers = {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers
    };
    
    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Błąd API');
    }
    
    return response.json();
  },
  
  auth: {
    login: (email, password) => api.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    }),
    register: (data) => api.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data)
    }),
    me: () => api.request('/auth/me')
  },
  
  services: {
    list: () => api.request('/services'),
    connections: () => api.request('/services/connections'),
    connect: (data) => api.request('/services/connect', {
      method: 'POST',
      body: JSON.stringify(data)
    }),
    disconnect: (id) => api.request(`/services/connections/${id}`, { method: 'DELETE' })
  },
  
  dashboard: {
    get: () => api.request('/dashboard'),
    unifiedInbox: () => api.request('/dashboard/unified-inbox')
  },
  
  notifications: {
    list: () => api.request('/notifications'),
    markRead: (id) => api.request(`/notifications/${id}/read`, { method: 'POST' })
  }
};

// ═══════════════════════════════════════════════════════════════
// AUTH CONTEXT
// ═══════════════════════════════════════════════════════════════

const AuthContext = createContext(null);

function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    const token = localStorage.getItem('idcard_token');
    if (token) {
      api.auth.me()
        .then(setUser)
        .catch(() => localStorage.removeItem('idcard_token'))
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);
  
  const login = async (email, password) => {
    const data = await api.auth.login(email, password);
    localStorage.setItem('idcard_token', data.access_token);
    setUser(data.user);
    return data;
  };
  
  const register = async (userData) => {
    const data = await api.auth.register(userData);
    localStorage.setItem('idcard_token', data.access_token);
    setUser(data.user);
    return data;
  };
  
  const logout = () => {
    localStorage.removeItem('idcard_token');
    setUser(null);
  };
  
  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

const useAuth = () => useContext(AuthContext);

// ═══════════════════════════════════════════════════════════════
// COMPONENTS
// ═══════════════════════════════════════════════════════════════

function Layout({ children }) {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  
  const navigation = [
    { name: 'Dashboard', href: '/', icon: Home },
    { name: 'Skrzynka', href: '/inbox', icon: Mail },
    { name: 'Usługi', href: '/services', icon: Link2 },
    { name: 'Ustawienia', href: '/settings', icon: Settings },
  ];
  
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Mobile sidebar */}
      <div className={`fixed inset-0 z-50 lg:hidden ${sidebarOpen ? '' : 'hidden'}`}>
        <div className="fixed inset-0 bg-gray-900/50" onClick={() => setSidebarOpen(false)} />
        <div className="fixed inset-y-0 left-0 w-64 bg-white shadow-xl">
          <div className="p-4 border-b flex justify-between items-center">
            <span className="text-xl font-bold text-idcard-600">IDCard.pl</span>
            <button onClick={() => setSidebarOpen(false)}>
              <X size={24} />
            </button>
          </div>
          <nav className="p-4 space-y-1">
            {navigation.map(item => (
              <Link
                key={item.href}
                to={item.href}
                onClick={() => setSidebarOpen(false)}
                className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                  location.pathname === item.href
                    ? 'bg-idcard-50 text-idcard-700'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                <item.icon size={20} />
                {item.name}
              </Link>
            ))}
          </nav>
        </div>
      </div>
      
      {/* Desktop sidebar */}
      <div className="hidden lg:fixed lg:inset-y-0 lg:flex lg:w-64 lg:flex-col">
        <div className="flex flex-col flex-grow bg-white border-r">
          <div className="p-6 border-b">
            <h1 className="text-2xl font-bold text-idcard-600">IDCard.pl</h1>
            <p className="text-sm text-gray-500 mt-1">Platforma Integracji</p>
          </div>
          
          <nav className="flex-1 p-4 space-y-1">
            {navigation.map(item => (
              <Link
                key={item.href}
                to={item.href}
                className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                  location.pathname === item.href
                    ? 'bg-idcard-50 text-idcard-700 font-medium'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                <item.icon size={20} />
                {item.name}
              </Link>
            ))}
          </nav>
          
          <div className="p-4 border-t">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-idcard-100 rounded-full flex items-center justify-center">
                <User size={20} className="text-idcard-600" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{user?.name}</p>
                <p className="text-xs text-gray-500 truncate">{user?.email}</p>
              </div>
            </div>
            <button
              onClick={logout}
              className="flex items-center gap-2 text-gray-600 hover:text-red-600 text-sm"
            >
              <LogOut size={16} />
              Wyloguj
            </button>
          </div>
        </div>
      </div>
      
      {/* Main content */}
      <div className="lg:pl-64">
        {/* Top bar */}
        <header className="sticky top-0 z-40 bg-white border-b">
          <div className="flex items-center justify-between px-4 py-3">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-2 rounded-lg hover:bg-gray-100"
            >
              <Menu size={24} />
            </button>
            
            <div className="flex items-center gap-4">
              <button className="relative p-2 rounded-lg hover:bg-gray-100">
                <Bell size={20} />
                <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
              </button>
            </div>
          </div>
        </header>
        
        <main className="p-6">
          {children}
        </main>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// PAGES
// ═══════════════════════════════════════════════════════════════

function LoginPage() {
  const { login, register } = useAuth();
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    
    try {
      if (isRegister) {
        await register({ email, password, name });
      } else {
        await login(email, password);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-idcard-500 to-idcard-700 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">IDCard.pl</h1>
          <p className="text-idcard-100">Platforma Integracji Usług Cyfrowych</p>
        </div>
        
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">
            {isRegister ? 'Rejestracja' : 'Logowanie'}
          </h2>
          
          {error && (
            <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">
              {error}
            </div>
          )}
          
          <form onSubmit={handleSubmit} className="space-y-4">
            {isRegister && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Imię i nazwisko
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-idcard-500 focus:border-transparent"
                  required
                />
              </div>
            )}
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-idcard-500 focus:border-transparent"
                required
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Hasło
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-idcard-500 focus:border-transparent"
                required
              />
            </div>
            
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-idcard-600 text-white rounded-lg font-medium hover:bg-idcard-700 disabled:opacity-50"
            >
              {loading ? 'Proszę czekać...' : (isRegister ? 'Zarejestruj się' : 'Zaloguj się')}
            </button>
          </form>
          
          <div className="mt-6 text-center">
            <button
              onClick={() => setIsRegister(!isRegister)}
              className="text-idcard-600 hover:underline text-sm"
            >
              {isRegister ? 'Masz już konto? Zaloguj się' : 'Nie masz konta? Zarejestruj się'}
            </button>
          </div>
        </div>
        
        <div className="mt-8 text-center text-idcard-100 text-sm">
          <p>Integracja z: e-Doręczenia • ePUAP • KSeF • mObywatel</p>
        </div>
      </div>
    </div>
  );
}

function DashboardPage() {
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    api.dashboard.get()
      .then(setDashboard)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);
  
  if (loading) {
    return <div className="flex justify-center py-12"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-idcard-600" /></div>;
  }
  
  const services = [
    { id: 'edoreczenia', name: 'e-Doręczenia', icon: Mail, color: 'bg-red-500', domain: 'szyfromat.pl' },
    { id: 'detax', name: 'Detax AI', icon: FileText, color: 'bg-emerald-500', domain: 'detax.pl' },
    { id: 'epuap', name: 'ePUAP', icon: Building, color: 'bg-blue-500', domain: 'gov.pl' },
    { id: 'ksef', name: 'KSeF', icon: CreditCard, color: 'bg-green-500', domain: 'mf.gov.pl' },
  ];
  
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500">Witaj w IDCard.pl - wszystkie usługi w jednym miejscu</p>
      </div>
      
      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl p-6 shadow-sm border">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-idcard-100 rounded-lg flex items-center justify-center">
              <Link2 className="text-idcard-600" size={24} />
            </div>
            <div>
              <p className="text-2xl font-bold">{dashboard?.stats?.active_connections || 0}</p>
              <p className="text-sm text-gray-500">Aktywne połączenia</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-xl p-6 shadow-sm border">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
              <Mail className="text-green-600" size={24} />
            </div>
            <div>
              <p className="text-2xl font-bold">3</p>
              <p className="text-sm text-gray-500">Nieprzeczytane</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-xl p-6 shadow-sm border">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-yellow-100 rounded-lg flex items-center justify-center">
              <Bell className="text-yellow-600" size={24} />
            </div>
            <div>
              <p className="text-2xl font-bold">2</p>
              <p className="text-sm text-gray-500">Powiadomienia</p>
            </div>
          </div>
        </div>
      </div>
      
      {/* Services */}
      <div>
        <h2 className="text-lg font-semibold mb-4">Usługi</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {services.map(service => {
            const serviceStatus = dashboard?.stats?.services?.[service.id];
            const isConnected = serviceStatus?.status === 'active';
            const isPending = serviceStatus?.status === 'pending';
            return (
              <Link
                key={service.id}
                to={`/services/${service.id}`}
                className="bg-white rounded-xl p-6 shadow-sm border hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className={`w-12 h-12 ${service.color} rounded-lg flex items-center justify-center`}>
                    <service.icon className="text-white" size={24} />
                  </div>
                  {isConnected ? (
                    <span className="flex items-center gap-1 text-xs text-green-600 bg-green-50 px-2 py-1 rounded-full">
                      <CheckCircle size={12} />
                      Połączono
                    </span>
                  ) : isPending ? (
                    <span className="flex items-center gap-1 text-xs text-yellow-600 bg-yellow-50 px-2 py-1 rounded-full">
                      <Clock size={12} />
                      Oczekuje
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded-full">
                      <Clock size={12} />
                      Niepołączono
                    </span>
                  )}
                </div>
                <h3 className="font-semibold text-gray-900">{service.name}</h3>
                <p className="text-sm text-gray-500">{service.domain}</p>
              </Link>
            );
          })}
        </div>
      </div>
      
      {/* Recent activity */}
      <div>
        <h2 className="text-lg font-semibold mb-4">Ostatnia aktywność</h2>
        <div className="bg-white rounded-xl shadow-sm border divide-y">
          {dashboard?.recent_activity?.length > 0 ? (
            dashboard.recent_activity.map((activity, i) => (
              <div key={i} className="p-4 flex items-center gap-4">
                <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center">
                  <Mail size={20} className="text-gray-600" />
                </div>
                <div className="flex-1">
                  <p className="font-medium">{activity.title}</p>
                  <p className="text-sm text-gray-500">{activity.service}</p>
                </div>
                <ChevronRight size={20} className="text-gray-400" />
              </div>
            ))
          ) : (
            <div className="p-8 text-center text-gray-500">
              Brak ostatniej aktywności
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ServicesPage() {
  const [services, setServices] = useState([]);
  const [connections, setConnections] = useState([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    Promise.all([
      api.services.list(),
      api.services.connections()
    ])
      .then(([servicesData, connectionsData]) => {
        setServices(servicesData.services || []);
        setConnections(connectionsData.connections || []);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);
  
  const handleConnect = async (serviceType) => {
    const adeAddress = prompt('Podaj adres e-Doręczeń (AE:PL-...)');
    if (!adeAddress) return;
    
    try {
      const result = await api.services.connect({
        service_type: serviceType,
        credentials: { ade_address: adeAddress },
        config: { auth_method: 'oauth2' }
      });
      alert(`Połączenie utworzone! ID: ${result.connection_id}`);
      // Refresh
      const connectionsData = await api.services.connections();
      setConnections(connectionsData.connections || []);
    } catch (err) {
      alert(`Błąd: ${err.message}`);
    }
  };
  
  if (loading) {
    return <div className="flex justify-center py-12"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-idcard-600" /></div>;
  }
  
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Usługi</h1>
        <p className="text-gray-500">Zarządzaj integracjami z usługami cyfrowymi</p>
      </div>
      
      {/* Connected services */}
      {connections.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-4">Połączone usługi</h2>
          <div className="space-y-3">
            {connections.map(conn => (
              <div key={conn.id} className="bg-white rounded-xl p-4 shadow-sm border flex items-center gap-4">
                <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                  <CheckCircle className="text-green-600" size={24} />
                </div>
                <div className="flex-1">
                  <p className="font-medium">{conn.service_type}</p>
                  <p className="text-sm text-gray-500">{conn.external_address}</p>
                </div>
                <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                  conn.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                }`}>
                  {conn.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Available services */}
      <div>
        <h2 className="text-lg font-semibold mb-4">Dostępne usługi</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {services.map(service => {
            const isConnected = connections.some(c => c.service_type === service.type);
            const isAvailable = service.status === 'available';
            
            return (
              <div key={service.type} className="bg-white rounded-xl p-6 shadow-sm border">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h3 className="font-semibold text-lg">{service.name}</h3>
                    <p className="text-sm text-gray-500">{service.provider}</p>
                  </div>
                  {isConnected ? (
                    <span className="bg-green-100 text-green-700 px-3 py-1 rounded-full text-xs font-medium">
                      Połączono
                    </span>
                  ) : isAvailable ? (
                    <span className="bg-blue-100 text-blue-700 px-3 py-1 rounded-full text-xs font-medium">
                      Dostępna
                    </span>
                  ) : (
                    <span className="bg-gray-100 text-gray-600 px-3 py-1 rounded-full text-xs font-medium">
                      Wkrótce
                    </span>
                  )}
                </div>
                
                <p className="text-gray-600 text-sm mb-4">{service.description}</p>
                
                <div className="mb-4">
                  <p className="text-xs font-medium text-gray-500 mb-2">Funkcje:</p>
                  <ul className="text-sm text-gray-600 space-y-1">
                    {service.features?.slice(0, 3).map((f, i) => (
                      <li key={i} className="flex items-center gap-2">
                        <CheckCircle size={14} className="text-green-500" />
                        {f}
                      </li>
                    ))}
                  </ul>
                </div>
                
                {!isConnected && isAvailable && (
                  <button
                    onClick={() => handleConnect(service.type)}
                    className="w-full py-2 bg-idcard-600 text-white rounded-lg font-medium hover:bg-idcard-700"
                  >
                    Połącz
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function InboxPage() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    api.dashboard.unifiedInbox()
      .then(data => setMessages(data.messages || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);
  
  if (loading) {
    return <div className="flex justify-center py-12"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-idcard-600" /></div>;
  }
  
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Skrzynka odbiorcza</h1>
        <p className="text-gray-500">Wiadomości ze wszystkich połączonych usług</p>
      </div>
      
      <div className="bg-white rounded-xl shadow-sm border divide-y">
        {messages.length > 0 ? (
          messages.map(msg => (
            <div key={msg.id} className="p-4 hover:bg-gray-50 cursor-pointer">
              <div className="flex items-start gap-4">
                <div className="text-2xl">{msg.source_icon || '📧'}</div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs bg-gray-100 px-2 py-0.5 rounded">{msg.source}</span>
                    <span className={`w-2 h-2 rounded-full ${msg.status === 'unread' ? 'bg-blue-500' : 'bg-gray-300'}`} />
                  </div>
                  <p className="font-medium text-gray-900 truncate">{msg.subject}</p>
                  <p className="text-sm text-gray-500 truncate">{msg.sender}</p>
                  {msg.preview && (
                    <p className="text-sm text-gray-400 truncate mt-1">{msg.preview}</p>
                  )}
                </div>
                <div className="text-xs text-gray-400">
                  {new Date(msg.received_at).toLocaleDateString('pl-PL')}
                </div>
              </div>
            </div>
          ))
        ) : (
          <div className="p-12 text-center text-gray-500">
            <Mail size={48} className="mx-auto mb-4 text-gray-300" />
            <p>Brak wiadomości</p>
            <p className="text-sm mt-2">Połącz usługi aby zobaczyć wiadomości</p>
          </div>
        )}
      </div>
    </div>
  );
}

function SettingsPage() {
  const { user } = useAuth();
  
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Ustawienia</h1>
        <p className="text-gray-500">Zarządzaj swoim kontem</p>
      </div>
      
      <div className="bg-white rounded-xl shadow-sm border p-6">
        <h2 className="font-semibold mb-4">Dane konta</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-gray-500 mb-1">Email</label>
            <p className="font-medium">{user?.email}</p>
          </div>
          <div>
            <label className="block text-sm text-gray-500 mb-1">Imię i nazwisko</label>
            <p className="font-medium">{user?.name}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function ServiceDetailPage() {
  const { serviceId } = useParams();
  const [connection, setConnection] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  
  const serviceInfo = {
    edoreczenia: { 
      name: 'e-Doręczenia', 
      icon: Mail, 
      color: 'bg-red-500',
      description: 'Oficjalna korespondencja elektroniczna z urzędami',
      externalUrl: 'http://localhost:3500',
      apiUrl: 'http://localhost:8500'
    },
    detax: { 
      name: 'Detax AI', 
      icon: FileText, 
      color: 'bg-emerald-500',
      description: 'Asystent AI do spraw podatkowych',
      externalUrl: 'http://localhost:3005',
      apiUrl: 'http://localhost:8005'
    },
    epuap: { 
      name: 'ePUAP', 
      icon: Building, 
      color: 'bg-blue-500',
      description: 'Elektroniczna Platforma Usług Administracji Publicznej',
      externalUrl: 'https://epuap.gov.pl'
    },
    ksef: { 
      name: 'KSeF', 
      icon: CreditCard, 
      color: 'bg-green-500',
      description: 'Krajowy System e-Faktur',
      externalUrl: 'https://ksef.mf.gov.pl'
    }
  };
  
  const service = serviceInfo[serviceId] || { name: serviceId, icon: Link2, color: 'bg-gray-500' };
  const ServiceIcon = service.icon;
  
  useEffect(() => {
    Promise.all([
      api.services.connections(),
      api.dashboard.unifiedInbox()
    ])
      .then(([connectionsData, inboxData]) => {
        const conn = (connectionsData.connections || []).find(c => 
          c.service_type.toLowerCase() === serviceId.toLowerCase()
        );
        setConnection(conn);
        setMessages((inboxData.messages || []).filter(m => 
          m.source.toLowerCase() === serviceId.toLowerCase()
        ));
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [serviceId]);
  
  const handleConnect = async () => {
    // Dla Detax - bezpośrednie przekierowanie SSO (nie wymaga połączenia)
    if (serviceId === 'detax') {
      const token = localStorage.getItem('idcard_token');
      if (token && service.apiUrl) {
        window.open(`${service.apiUrl}/sso?token=${token}&redirect=/`, '_blank');
      } else {
        window.open(service.externalUrl, '_blank');
      }
      return;
    }
    
    // Dla e-Doręczeń - wymaga adresu ADE
    const adeAddress = prompt('Podaj adres e-Doręczeń (AE:PL-...)');
    if (!adeAddress) return;
    
    try {
      await api.services.connect({
        service_type: serviceId,
        credentials: { ade_address: adeAddress },
        config: { auth_method: 'oauth2' }
      });
      alert('Połączono!');
      window.location.reload();
    } catch (err) {
      alert(`Błąd: ${err.message}`);
    }
  };
  
  const handleDisconnect = async () => {
    if (!connection || !confirm('Czy na pewno chcesz rozłączyć?')) return;
    
    try {
      await api.services.disconnect(connection.id);
      alert('Rozłączono');
      window.location.reload();
    } catch (err) {
      alert(`Błąd: ${err.message}`);
    }
  };
  
  if (loading) {
    return <div className="flex justify-center py-12"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-idcard-600" /></div>;
  }
  
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link to="/services" className="p-2 hover:bg-gray-100 rounded-lg">
          <ChevronRight className="rotate-180" size={20} />
        </Link>
        <div className={`w-12 h-12 ${service.color} rounded-lg flex items-center justify-center`}>
          <ServiceIcon className="text-white" size={24} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{service.name}</h1>
          <p className="text-gray-500">{service.description}</p>
        </div>
      </div>
      
      {/* Status */}
      <div className="bg-white rounded-xl shadow-sm border p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-semibold mb-2">Status połączenia</h2>
            {connection ? (
              <div className="flex items-center gap-2">
                <CheckCircle className="text-green-500" size={20} />
                <span className="text-green-700 font-medium">Połączono</span>
                <span className="text-gray-500">({connection.external_address})</span>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <AlertCircle className="text-yellow-500" size={20} />
                <span className="text-yellow-700">Niepołączono</span>
              </div>
            )}
          </div>
          
          <div className="flex gap-2">
            {connection ? (
              <>
                <a
                  href={service.apiUrl 
                    ? `${service.apiUrl}/sso?token=${localStorage.getItem('idcard_token')}&redirect=/`
                    : service.externalUrl
                  }
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2 bg-idcard-600 text-white rounded-lg hover:bg-idcard-700"
                >
                  Otwórz {service.name}
                </a>
                <button
                  onClick={handleDisconnect}
                  className="px-4 py-2 border border-red-300 text-red-600 rounded-lg hover:bg-red-50"
                >
                  Rozłącz
                </button>
              </>
            ) : (
              <button
                onClick={handleConnect}
                className="px-4 py-2 bg-idcard-600 text-white rounded-lg hover:bg-idcard-700"
              >
                Połącz
              </button>
            )}
          </div>
        </div>
      </div>
      
      {/* Messages */}
      {connection && (
        <div>
          <h2 className="text-lg font-semibold mb-4">Wiadomości z {service.name}</h2>
          <div className="bg-white rounded-xl shadow-sm border divide-y">
            {messages.length > 0 ? (
              messages.map(msg => (
                <div key={msg.id} className="p-4 hover:bg-gray-50">
                  <div className="flex items-start gap-4">
                    <div className="text-2xl">{msg.source_icon || '📧'}</div>
                    <div className="flex-1">
                      <p className="font-medium">{msg.subject}</p>
                      <p className="text-sm text-gray-500">{msg.sender}</p>
                    </div>
                    <span className="text-xs text-gray-400">
                      {new Date(msg.received_at).toLocaleDateString('pl-PL')}
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <div className="p-8 text-center text-gray-500">
                <Mail size={32} className="mx-auto mb-2 text-gray-300" />
                <p>Brak wiadomości</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// APP
// ═══════════════════════════════════════════════════════════════

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-idcard-600" />
      </div>
    );
  }
  
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  
  return <Layout>{children}</Layout>;
}

function AppRoutes() {
  const { user, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-idcard-600" />
      </div>
    );
  }
  
  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <LoginPage />} />
      <Route path="/" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
      <Route path="/inbox" element={<ProtectedRoute><InboxPage /></ProtectedRoute>} />
      <Route path="/services" element={<ProtectedRoute><ServicesPage /></ProtectedRoute>} />
      <Route path="/services/:serviceId" element={<ProtectedRoute><ServiceDetailPage /></ProtectedRoute>} />
      <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
