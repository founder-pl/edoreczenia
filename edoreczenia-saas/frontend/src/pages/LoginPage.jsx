import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth.jsx';
import { Mail, Lock, AlertCircle, ArrowRight, BookOpen } from 'lucide-react';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(username, password);
      navigate('/inbox');
    } catch (err) {
      setError(err.response?.data?.detail || 'Błąd logowania');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Left panel - branding */}
      <div className="hidden lg:flex lg:w-1/2 gradient-dark text-white p-12 flex-col justify-between">
        <div>
          <div className="flex items-center gap-3 mb-12">
            <div className="w-12 h-12 bg-pp-red rounded-xl flex items-center justify-center">
              <Mail size={28} />
            </div>
            <div>
              <span className="text-pp-red font-bold text-2xl">e-</span>
              <span className="font-bold text-2xl">Doręczenia</span>
            </div>
          </div>
          
          <h1 className="text-4xl font-bold mb-6">
            Bezpiecznie, szybko,<br />elektronicznie
          </h1>
          <p className="text-xl text-gray-300 mb-8">
            Panel SaaS do zarządzania korespondencją elektroniczną<br />
            w ramach systemu e-Doręczeń
          </p>

          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-pp-red/20 rounded-lg flex items-center justify-center">
                <span className="text-pp-red font-bold">✓</span>
              </div>
              <span>Integracja z Proxy IMAP/SMTP</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-pp-red/20 rounded-lg flex items-center justify-center">
                <span className="text-pp-red font-bold">✓</span>
              </div>
              <span>Synchronizacja z Middleware Sync</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-pp-red/20 rounded-lg flex items-center justify-center">
                <span className="text-pp-red font-bold">✓</span>
              </div>
              <span>DSL do automatyzacji przepływów</span>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <Link 
            to="/guide"
            className="flex items-center gap-2 text-white/80 hover:text-white transition-colors"
          >
            <BookOpen size={18} />
            <span>Jak założyć skrzynkę e-Doręczeń?</span>
          </Link>
          <div className="text-sm text-gray-400">
            © 2024 e-Doręczenia SaaS. Wszystkie prawa zastrzeżone.
          </div>
        </div>
      </div>

      {/* Right panel - login form */}
      <div className="flex-1 flex items-center justify-center p-8 bg-gray-50">
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center justify-center gap-3 mb-8">
            <div className="w-12 h-12 bg-pp-red rounded-xl flex items-center justify-center text-white">
              <Mail size={28} />
            </div>
            <div>
              <span className="text-pp-red font-bold text-2xl">e-</span>
              <span className="font-bold text-2xl text-pp-dark">Doręczenia</span>
            </div>
          </div>

          <div className="card p-8">
            <h2 className="text-2xl font-bold text-pp-dark mb-2">Zaloguj się</h2>
            <p className="text-gray-500 mb-8">
              Wprowadź dane logowania do panelu e-Doręczeń
            </p>

            {error && (
              <div className="flex items-center gap-2 p-4 bg-red-50 text-red-700 rounded-xl mb-6 animate-fadeIn">
                <AlertCircle size={20} />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Nazwa użytkownika
                </label>
                <div className="relative">
                  <Mail className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="input pl-12"
                    placeholder="np. testuser"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Hasło
                </label>
                <div className="relative">
                  <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="input pl-12"
                    placeholder="••••••••"
                    required
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full btn-primary py-3 flex items-center justify-center gap-2"
              >
                {loading ? (
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <>
                    <span>Zaloguj się</span>
                    <ArrowRight size={20} />
                  </>
                )}
              </button>
            </form>

            <div className="mt-8 pt-6 border-t border-gray-200">
              <p className="text-sm text-gray-500 text-center mb-4">
                Dane testowe do logowania:
              </p>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div className="p-3 bg-gray-50 rounded-lg">
                  <div className="font-medium text-gray-700">Proxy User</div>
                  <div className="text-gray-500">testuser / testpass123</div>
                </div>
                <div className="p-3 bg-gray-50 rounded-lg">
                  <div className="font-medium text-gray-700">Sync User</div>
                  <div className="text-gray-500">mailuser / mailpass123</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
