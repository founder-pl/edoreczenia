import { useState, useEffect, createContext, useContext } from 'react';
import { authApi } from '../services/api.jsx';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Sprawdź SSO token z URL
    const urlParams = new URLSearchParams(window.location.search);
    const ssoToken = urlParams.get('sso_token');
    
    if (ssoToken) {
      // SSO login - zapisz token i pobierz dane użytkownika
      localStorage.setItem('token', ssoToken);
      
      // Dekoduj token aby uzyskać dane użytkownika
      try {
        const payload = JSON.parse(atob(ssoToken.split('.')[1]));
        const ssoUser = {
          id: payload.sub,
          email: payload.email,
          name: payload.email?.split('@')[0] || 'User',
          sso: true
        };
        localStorage.setItem('user', JSON.stringify(ssoUser));
        setUser(ssoUser);
        
        // Usuń token z URL
        window.history.replaceState({}, document.title, window.location.pathname);
      } catch (e) {
        console.error('SSO token decode error:', e);
      }
      setLoading(false);
      return;
    }
    
    // Normalne sprawdzenie tokena
    const token = localStorage.getItem('token');
    const savedUser = localStorage.getItem('user');
    
    if (token && savedUser) {
      setUser(JSON.parse(savedUser));
    }
    setLoading(false);
  }, []);

  const login = async (username, password) => {
    const response = await authApi.login(username, password);
    const { access_token, user } = response.data;
    
    localStorage.setItem('token', access_token);
    localStorage.setItem('user', JSON.stringify(user));
    setUser(user);
    
    return user;
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
