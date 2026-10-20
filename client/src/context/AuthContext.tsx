import React, { createContext, useContext, useState, useEffect } from 'react';
import api, { getApiBaseUrl } from '../services/api';
import type { User } from '../types';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  simulationMode: boolean;
  deviceStatus: 'online' | 'offline';
  setSimulationMode: (val: boolean) => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string, role?: string) => Promise<void>;
  logout: () => void;
  authenticateWithToken: (token: string, userData: any) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [simulationMode, setSimulationModeState] = useState<boolean>(true);
  const [deviceStatus, setDeviceStatus] = useState<'online' | 'offline'>('offline');

  // Load user session and check status on mount
  useEffect(() => {
    const fetchSession = async () => {
      const storedToken = localStorage.getItem('forensic_token');
      const storedUser = localStorage.getItem('forensic_user');
      
      if (storedToken && storedUser) {
        try {
          // Validate token with backend
          api.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`;
          const res = await api.get('/auth/me');
          setUser(res.data);
          setToken(storedToken);
        } catch (err) {
          console.error("Session verification failed, logging out", err);
          logout();
        }
      }
      
      // Load settings (simulation mode)
      try {
        const settingsRes = await api.get('/settings');
        setSimulationModeState(settingsRes.data.simulation_mode);
      } catch (err) {
        console.error("Failed to load settings from server", err);
      }

      setIsLoading(false);
    };

    fetchSession();
  }, []);

  // WebSocket for hardware auth and real-time alerts
  useEffect(() => {
    let ws: WebSocket | null = null;
    const apiBase = getApiBaseUrl().replace(/\/api\/?$/, '');
    const isHttps = apiBase.startsWith('https://') || (typeof window !== 'undefined' && window.location.protocol === 'https:');
    const wsUrl = apiBase.replace(/^https?:\/\//, isHttps ? 'wss://' : 'ws://') + '/api/ws/hardware';
    
    const connectWS = () => {
      ws = new WebSocket(wsUrl);
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'hardware_auth_success') {
            authenticateWithToken(data.token, data.user);
          } else if (data.type === 'device_status') {
            setDeviceStatus(data.status);
          }
        } catch (err) {
          console.error("Error parsing WS message", err);
        }
      };

      ws.onopen = () => {
        console.log("WebSocket connected for hardware authentication");
      };

      ws.onclose = () => {
        console.log("WebSocket disconnected, retrying in 5s...");
        setTimeout(connectWS, 5000);
      };

      ws.onerror = (err) => {
        console.error("WebSocket error", err);
        ws?.close();
      };
    };

    connectWS();

    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, []);

  const authenticateWithToken = (jwtToken: string, userData: any) => {
    localStorage.setItem('forensic_token', jwtToken);
    localStorage.setItem('forensic_user', JSON.stringify(userData));
    api.defaults.headers.common['Authorization'] = `Bearer ${jwtToken}`;
    setUser(userData);
    setToken(jwtToken);
  };

  const login = async (email: string, password: string) => {
    const cleanEmail = email.trim().toLowerCase();
    const response = await api.post('/auth/login', { email: cleanEmail, password });
    const { access_token, user: userData } = response.data;
    authenticateWithToken(access_token, userData);
    return userData;
  };

  const register = async (name: string, email: string, password: string, role?: string) => {
    const cleanEmail = email.trim().toLowerCase();
    await api.post('/auth/register', {
      name: name.trim(),
      email: cleanEmail,
      password,
      role: role || 'investigator'
    });
    // Automatically log in newly registered investigator
    const response = await api.post('/auth/login', { email: cleanEmail, password });
    const { access_token, user: userData } = response.data;
    authenticateWithToken(access_token, userData);
    return userData;
  };

  const logout = () => {
    localStorage.removeItem('forensic_token');
    localStorage.removeItem('forensic_user');
    delete api.defaults.headers.common['Authorization'];
    setUser(null);
    setToken(null);
  };

  const setSimulationMode = async (val: boolean) => {
    try {
      await api.post('/settings', { simulation_mode: val });
      setSimulationModeState(val);
    } catch (err) {
      console.error("Failed to update simulation mode on server", err);
      // Fallback
      setSimulationModeState(val);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!token,
        isLoading,
        simulationMode,
        deviceStatus,
        setSimulationMode,
        login,
        register,
        logout,
        authenticateWithToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
