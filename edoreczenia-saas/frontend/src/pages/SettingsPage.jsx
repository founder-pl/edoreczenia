import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth.jsx';
import { integrationsApi } from '../services/api.jsx';
import { 
  User, Mail, Shield, Bell, Link2, Server,
  CheckCircle, XCircle, AlertCircle, RefreshCw
} from 'lucide-react';

export default function SettingsPage() {
  const { user } = useAuth();
  const [integrations, setIntegrations] = useState([]);
  const [loadingIntegrations, setLoadingIntegrations] = useState(true);

  useEffect(() => {
    loadIntegrations();
  }, []);

  const loadIntegrations = async () => {
    setLoadingIntegrations(true);
    try {
      const response = await integrationsApi.getStatus();
      setIntegrations(response.data);
    } catch (error) {
      console.error('Error loading integrations:', error);
    } finally {
      setLoadingIntegrations(false);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'online':
        return <CheckCircle size={20} className="text-green-500" />;
      case 'offline':
        return <XCircle size={20} className="text-red-500" />;
      default:
        return <AlertCircle size={20} className="text-yellow-500" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'online':
        return 'bg-green-100 text-green-700';
      case 'offline':
        return 'bg-red-100 text-red-700';
      default:
        return 'bg-yellow-100 text-yellow-700';
    }
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-pp-dark mb-8">Ustawienia</h1>

      {/* Profile section */}
      <section className="card p-6 mb-6">
        <h2 className="flex items-center gap-2 text-lg font-semibold text-pp-dark mb-6">
          <User size={20} />
          Profil użytkownika
        </h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-500 mb-1">
              Nazwa użytkownika
            </label>
            <div className="px-4 py-3 bg-gray-50 rounded-lg font-medium">
              {user?.username}
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-500 mb-1">
              Imię i nazwisko
            </label>
            <div className="px-4 py-3 bg-gray-50 rounded-lg font-medium">
              {user?.name}
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-500 mb-1">
              Email
            </label>
            <div className="px-4 py-3 bg-gray-50 rounded-lg">
              {user?.email}
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-500 mb-1">
              Adres ADE
            </label>
            <div className="px-4 py-3 bg-gray-50 rounded-lg font-mono text-sm">
              {user?.address}
            </div>
          </div>
        </div>
      </section>

      {/* Integrations section */}
      <section className="card p-6 mb-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-pp-dark">
            <Link2 size={20} />
            Status integracji
          </h2>
          <button 
            onClick={loadIntegrations}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            disabled={loadingIntegrations}
          >
            <RefreshCw size={20} className={loadingIntegrations ? 'animate-spin' : ''} />
          </button>
        </div>

        <div className="space-y-4">
          {loadingIntegrations ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-pp-red"></div>
            </div>
          ) : integrations.length > 0 ? (
            integrations.map((integration, index) => (
              <div 
                key={index}
                className="flex items-center justify-between p-4 bg-gray-50 rounded-xl"
              >
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 bg-pp-dark rounded-lg flex items-center justify-center text-white">
                    <Server size={20} />
                  </div>
                  <div>
                    <div className="font-medium">{integration.name}</div>
                    <div className="text-sm text-gray-500">{integration.url}</div>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  {integration.latency_ms && (
                    <span className="text-sm text-gray-500">
                      {integration.latency_ms}ms
                    </span>
                  )}
                  <span className={`flex items-center gap-2 px-3 py-1 rounded-full text-sm ${getStatusColor(integration.status)}`}>
                    {getStatusIcon(integration.status)}
                    {integration.status === 'online' ? 'Online' : integration.status === 'offline' ? 'Offline' : 'Błąd'}
                  </span>
                </div>
              </div>
            ))
          ) : (
            <div className="text-center py-8 text-gray-500">
              Brak danych o integracjach
            </div>
          )}
        </div>

        {/* Integration URLs info */}
        <div className="mt-6 p-4 bg-blue-50 rounded-xl">
          <h4 className="font-medium text-blue-900 mb-2">Adresy usług</h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-blue-700">Proxy IMAP/SMTP:</span>
              <div className="font-mono text-blue-900">localhost:8180</div>
            </div>
            <div>
              <span className="text-blue-700">Middleware Sync:</span>
              <div className="font-mono text-blue-900">localhost:8280</div>
            </div>
            <div>
              <span className="text-blue-700">DSL:</span>
              <div className="font-mono text-blue-900">localhost:8380</div>
            </div>
          </div>
        </div>
      </section>

      {/* Notifications section */}
      <section className="card p-6 mb-6">
        <h2 className="flex items-center gap-2 text-lg font-semibold text-pp-dark mb-6">
          <Bell size={20} />
          Powiadomienia
        </h2>
        
        <div className="space-y-4">
          <label className="flex items-center justify-between p-4 bg-gray-50 rounded-xl cursor-pointer">
            <div>
              <div className="font-medium">Powiadomienia email</div>
              <div className="text-sm text-gray-500">Otrzymuj powiadomienia o nowych wiadomościach</div>
            </div>
            <input type="checkbox" defaultChecked className="w-5 h-5 text-pp-red rounded" />
          </label>
          
          <label className="flex items-center justify-between p-4 bg-gray-50 rounded-xl cursor-pointer">
            <div>
              <div className="font-medium">Powiadomienia push</div>
              <div className="text-sm text-gray-500">Powiadomienia w przeglądarce</div>
            </div>
            <input type="checkbox" className="w-5 h-5 text-pp-red rounded" />
          </label>
          
          <label className="flex items-center justify-between p-4 bg-gray-50 rounded-xl cursor-pointer">
            <div>
              <div className="font-medium">Podsumowanie dzienne</div>
              <div className="text-sm text-gray-500">Codzienny raport aktywności</div>
            </div>
            <input type="checkbox" className="w-5 h-5 text-pp-red rounded" />
          </label>
        </div>
      </section>

      {/* Security section */}
      <section className="card p-6">
        <h2 className="flex items-center gap-2 text-lg font-semibold text-pp-dark mb-6">
          <Shield size={20} />
          Bezpieczeństwo
        </h2>
        
        <div className="space-y-4">
          <div className="p-4 bg-gray-50 rounded-xl">
            <div className="flex items-center justify-between mb-2">
              <div className="font-medium">Uwierzytelnianie dwuskładnikowe</div>
              <span className="px-2 py-1 bg-yellow-100 text-yellow-700 text-xs rounded-full">
                Nieaktywne
              </span>
            </div>
            <p className="text-sm text-gray-500 mb-3">
              Dodatkowa warstwa zabezpieczeń dla Twojego konta
            </p>
            <button className="btn-secondary text-sm">
              Włącz 2FA
            </button>
          </div>
          
          <div className="p-4 bg-gray-50 rounded-xl">
            <div className="font-medium mb-2">Zmiana hasła</div>
            <p className="text-sm text-gray-500 mb-3">
              Ostatnia zmiana: nigdy
            </p>
            <button className="btn-secondary text-sm">
              Zmień hasło
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
