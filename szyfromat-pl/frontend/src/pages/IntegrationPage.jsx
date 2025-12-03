import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api.jsx';
import { 
  Plus, CheckCircle, Clock, AlertCircle, Trash2, 
  Shield, Key, RefreshCw, ChevronRight, Building2,
  User, Briefcase, ExternalLink
} from 'lucide-react';

const entityTypes = [
  { id: 'person', name: 'Osoba fizyczna', icon: User },
  { id: 'company', name: 'Firma', icon: Briefcase },
  { id: 'public_entity', name: 'Podmiot publiczny', icon: Building2 },
];

const authMethods = [
  { id: 'oauth2', name: 'OAuth2', description: 'Oficjalne API e-Doręczeń (zalecane)' },
  { id: 'mobywatel', name: 'mObywatel', description: 'Aplikacja mObywatel' },
  { id: 'certificate', name: 'Certyfikat kwalifikowany', description: 'Certyfikat kwalifikowany (Certum, KIR)' },
];

// URL-e dla wersji dev (localhost) i produkcyjnej
const isDev = window.location.hostname === 'localhost';

const providers = [
  { id: 'idcard', name: 'IDCard.pl', url: isDev ? 'http://localhost:4100' : 'https://idcard.pl/' },
  { id: 'poczta_polska', name: 'Poczta Polska', url: 'https://edoreczenia.poczta-polska.pl/' },
];

export default function IntegrationPage() {
  const navigate = useNavigate();
  const [integrations, setIntegrations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [selectedIntegration, setSelectedIntegration] = useState(null);
  const [steps, setSteps] = useState([]);
  
  // Form state
  const [formData, setFormData] = useState({
    ade_address: '',
    provider: 'idcard',
    auth_method: 'oauth2',
    entity_type: 'person',
    pesel: '',
    nip: '',
    krs: '',
    regon: '',
  });
  const [formError, setFormError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    loadIntegrations();
  }, []);

  const loadIntegrations = async () => {
    setLoading(true);
    try {
      const response = await api.get('/api/address-integrations');
      setIntegrations(response.data);
    } catch (error) {
      console.error('Error loading integrations:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadSteps = async (integrationId) => {
    try {
      const response = await api.get(`/api/address-integrations/${integrationId}/steps`);
      setSteps(response.data);
    } catch (error) {
      console.error('Error loading steps:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError('');
    setSubmitting(true);

    try {
      const response = await api.post('/api/address-integrations', formData);
      setIntegrations([...integrations, response.data]);
      setShowForm(false);
      setSelectedIntegration(response.data);
      loadSteps(response.data.id);
    } catch (error) {
      setFormError(error.response?.data?.detail || 'Błąd podczas tworzenia integracji');
    } finally {
      setSubmitting(false);
    }
  };

  const handleVerify = async (integrationId) => {
    try {
      await api.post(`/api/address-integrations/${integrationId}/verify`);
      loadIntegrations();
      loadSteps(integrationId);
    } catch (error) {
      console.error('Error verifying:', error);
    }
  };

  const handleComplete = async (integrationId) => {
    try {
      await api.post(`/api/address-integrations/${integrationId}/complete`);
      loadIntegrations();
      loadSteps(integrationId);
    } catch (error) {
      console.error('Error completing:', error);
    }
  };

  const handleDelete = async (integrationId) => {
    if (!confirm('Czy na pewno chcesz usunąć tę integrację?')) return;
    
    try {
      await api.delete(`/api/address-integrations/${integrationId}`);
      setIntegrations(integrations.filter(i => i.id !== integrationId));
      if (selectedIntegration?.id === integrationId) {
        setSelectedIntegration(null);
      }
    } catch (error) {
      console.error('Error deleting:', error);
    }
  };

  const getStatusBadge = (status) => {
    const badges = {
      pending: { color: 'bg-yellow-100 text-yellow-700', icon: Clock, text: 'Oczekuje' },
      verifying: { color: 'bg-blue-100 text-blue-700', icon: RefreshCw, text: 'Weryfikacja' },
      active: { color: 'bg-green-100 text-green-700', icon: CheckCircle, text: 'Aktywna' },
      failed: { color: 'bg-red-100 text-red-700', icon: AlertCircle, text: 'Błąd' },
    };
    const badge = badges[status] || badges.pending;
    const Icon = badge.icon;
    
    return (
      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${badge.color}`}>
        <Icon size={12} />
        {badge.text}
      </span>
    );
  };

  return (
    <div className="h-full overflow-auto bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-pp-dark">Integracja adresów e-Doręczeń</h1>
            <p className="text-gray-500 mt-1">Dodaj i zarządzaj adresami e-Doręczeń</p>
          </div>
          <button
            onClick={() => setShowForm(true)}
            className="btn-primary flex items-center gap-2"
          >
            <Plus size={20} />
            Dodaj adres
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Lista integracji */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-xl shadow-sm border border-gray-200">
              <div className="p-4 border-b border-gray-200">
                <h2 className="font-semibold text-gray-900">Twoje adresy</h2>
              </div>
              
              {loading ? (
                <div className="p-8 text-center">
                  <RefreshCw className="animate-spin mx-auto text-gray-400" size={24} />
                </div>
              ) : integrations.length === 0 ? (
                <div className="p-8 text-center text-gray-500">
                  <Shield size={48} className="mx-auto mb-4 text-gray-300" />
                  <p>Brak zintegrowanych adresów</p>
                  <button
                    onClick={() => setShowForm(true)}
                    className="mt-4 text-pp-red hover:underline"
                  >
                    Dodaj pierwszy adres
                  </button>
                </div>
              ) : (
                <div className="divide-y divide-gray-100">
                  {integrations.map((integration) => (
                    <div
                      key={integration.id}
                      onClick={() => {
                        setSelectedIntegration(integration);
                        loadSteps(integration.id);
                      }}
                      className={`p-4 cursor-pointer hover:bg-gray-50 transition-colors ${
                        selectedIntegration?.id === integration.id ? 'bg-pp-red/5 border-l-4 border-pp-red' : ''
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="font-mono text-sm text-gray-900">
                          {integration.ade_address}
                        </div>
                        <ChevronRight size={16} className="text-gray-400" />
                      </div>
                      <div className="flex items-center gap-2 mt-2">
                        {getStatusBadge(integration.status)}
                        <span className="text-xs text-gray-500">{integration.provider}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Szczegóły / Formularz */}
          <div className="lg:col-span-2">
            {showForm ? (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-6">Dodaj adres e-Doręczeń</h2>
                
                <form onSubmit={handleSubmit} className="space-y-6">
                  {formError && (
                    <div className="p-4 bg-red-50 text-red-700 rounded-lg flex items-center gap-2">
                      <AlertCircle size={20} />
                      {formError}
                    </div>
                  )}

                  {/* Adres ADE */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Adres ADE *
                    </label>
                    <input
                      type="text"
                      value={formData.ade_address}
                      onChange={(e) => setFormData({ ...formData, ade_address: e.target.value })}
                      placeholder="AE:PL-12345-67890-ABCDE-12"
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-pp-red focus:border-transparent"
                      required
                    />
                    <p className="mt-1 text-xs text-gray-500">
                      Adres znajdziesz w panelu dostawcy e-Doręczeń
                    </p>
                  </div>

                  {/* Dostawca */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Dostawca
                    </label>
                    <div className="grid grid-cols-2 gap-3">
                      {providers.map((provider) => (
                        <button
                          key={provider.id}
                          type="button"
                          onClick={() => setFormData({ ...formData, provider: provider.id })}
                          className={`p-4 border rounded-lg text-left transition-colors ${
                            formData.provider === provider.id
                              ? 'border-pp-red bg-pp-red/5'
                              : 'border-gray-200 hover:border-gray-300'
                          }`}
                        >
                          <div className="font-medium">{provider.name}</div>
                          <a
                            href={provider.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-pp-red hover:underline flex items-center gap-1 mt-1"
                            onClick={(e) => e.stopPropagation()}
                          >
                            Panel <ExternalLink size={10} />
                          </a>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Typ podmiotu */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Typ podmiotu
                    </label>
                    <div className="grid grid-cols-3 gap-3">
                      {entityTypes.map((type) => {
                        const Icon = type.icon;
                        return (
                          <button
                            key={type.id}
                            type="button"
                            onClick={() => setFormData({ ...formData, entity_type: type.id })}
                            className={`p-4 border rounded-lg text-center transition-colors ${
                              formData.entity_type === type.id
                                ? 'border-pp-red bg-pp-red/5'
                                : 'border-gray-200 hover:border-gray-300'
                            }`}
                          >
                            <Icon size={24} className="mx-auto mb-2" />
                            <div className="text-sm font-medium">{type.name}</div>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Dane identyfikacyjne */}
                  <div className="grid grid-cols-2 gap-4">
                    {formData.entity_type === 'person' && (
                      <div className="col-span-2">
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          PESEL *
                        </label>
                        <input
                          type="text"
                          value={formData.pesel}
                          onChange={(e) => setFormData({ ...formData, pesel: e.target.value })}
                          placeholder="00000000000"
                          maxLength={11}
                          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-pp-red focus:border-transparent"
                        />
                      </div>
                    )}
                    {formData.entity_type !== 'person' && (
                      <>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">
                            NIP *
                          </label>
                          <input
                            type="text"
                            value={formData.nip}
                            onChange={(e) => setFormData({ ...formData, nip: e.target.value })}
                            placeholder="0000000000"
                            maxLength={10}
                            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-pp-red focus:border-transparent"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">
                            KRS (opcjonalnie)
                          </label>
                          <input
                            type="text"
                            value={formData.krs}
                            onChange={(e) => setFormData({ ...formData, krs: e.target.value })}
                            placeholder="0000000000"
                            maxLength={10}
                            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-pp-red focus:border-transparent"
                          />
                        </div>
                      </>
                    )}
                  </div>

                  {/* Metoda uwierzytelnienia */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Metoda uwierzytelnienia
                    </label>
                    <div className="space-y-2">
                      {authMethods.map((method) => (
                        <label
                          key={method.id}
                          className={`flex items-center p-4 border rounded-lg cursor-pointer transition-colors ${
                            formData.auth_method === method.id
                              ? 'border-pp-red bg-pp-red/5'
                              : 'border-gray-200 hover:border-gray-300'
                          }`}
                        >
                          <input
                            type="radio"
                            name="auth_method"
                            value={method.id}
                            checked={formData.auth_method === method.id}
                            onChange={(e) => setFormData({ ...formData, auth_method: e.target.value })}
                            className="sr-only"
                          />
                          <div className="flex-1">
                            <div className="font-medium">{method.name}</div>
                            <div className="text-sm text-gray-500">{method.description}</div>
                          </div>
                          {formData.auth_method === method.id && (
                            <CheckCircle size={20} className="text-pp-red" />
                          )}
                        </label>
                      ))}
                    </div>
                  </div>

                  {/* Przyciski */}
                  <div className="flex gap-3 pt-4">
                    <button
                      type="button"
                      onClick={() => setShowForm(false)}
                      className="flex-1 px-4 py-3 border border-gray-300 rounded-lg hover:bg-gray-50"
                    >
                      Anuluj
                    </button>
                    <button
                      type="submit"
                      disabled={submitting}
                      className="flex-1 btn-primary py-3"
                    >
                      {submitting ? 'Dodawanie...' : 'Dodaj adres'}
                    </button>
                  </div>
                </form>
              </div>
            ) : selectedIntegration ? (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200">
                <div className="p-6 border-b border-gray-200">
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className="text-xl font-semibold text-gray-900">
                        {selectedIntegration.ade_address}
                      </h2>
                      <div className="flex items-center gap-3 mt-2">
                        {getStatusBadge(selectedIntegration.status)}
                        <span className="text-sm text-gray-500">
                          {selectedIntegration.provider} • {selectedIntegration.entity_type}
                        </span>
                      </div>
                    </div>
                    <button
                      onClick={() => handleDelete(selectedIntegration.id)}
                      className="p-2 text-red-500 hover:bg-red-50 rounded-lg"
                    >
                      <Trash2 size={20} />
                    </button>
                  </div>
                </div>

                {/* Kroki weryfikacji */}
                <div className="p-6">
                  <h3 className="font-semibold text-gray-900 mb-4">Kroki weryfikacji</h3>
                  <div className="space-y-4">
                    {steps.map((step) => (
                      <div key={step.step} className="flex items-start gap-4">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                          step.status === 'completed' ? 'bg-green-100 text-green-600' :
                          step.status === 'in_progress' ? 'bg-blue-100 text-blue-600' :
                          'bg-gray-100 text-gray-400'
                        }`}>
                          {step.status === 'completed' ? (
                            <CheckCircle size={16} />
                          ) : step.status === 'in_progress' ? (
                            <RefreshCw size={16} className="animate-spin" />
                          ) : (
                            <span className="text-sm font-medium">{step.step}</span>
                          )}
                        </div>
                        <div className="flex-1">
                          <div className="font-medium text-gray-900">{step.name}</div>
                          <div className="text-sm text-gray-500">{step.description}</div>
                          {step.required_action && (
                            <div className="mt-2 text-sm text-pp-red">{step.required_action}</div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Akcje */}
                  <div className="mt-8 flex gap-3">
                    {selectedIntegration.status === 'pending' && (
                      <button
                        onClick={() => handleVerify(selectedIntegration.id)}
                        className="btn-primary flex items-center gap-2"
                      >
                        <Key size={20} />
                        Rozpocznij weryfikację
                      </button>
                    )}
                    {selectedIntegration.status === 'verifying' && (
                      <button
                        onClick={() => handleComplete(selectedIntegration.id)}
                        className="btn-primary flex items-center gap-2"
                      >
                        <CheckCircle size={20} />
                        Zakończ weryfikację (demo)
                      </button>
                    )}
                    {selectedIntegration.status === 'active' && (
                      <div className="flex items-center gap-2 text-green-600">
                        <CheckCircle size={20} />
                        <span>Integracja aktywna</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
                <Shield size={64} className="mx-auto mb-4 text-gray-300" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  Wybierz adres lub dodaj nowy
                </h3>
                <p className="text-gray-500 mb-6">
                  Zintegruj swój adres e-Doręczeń aby wysyłać i odbierać korespondencję
                </p>
                <button
                  onClick={() => setShowForm(true)}
                  className="btn-primary inline-flex items-center gap-2"
                >
                  <Plus size={20} />
                  Dodaj adres e-Doręczeń
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
