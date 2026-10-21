import React, { createContext, useContext, useState, useEffect } from 'react';
import api, { getApiBaseUrl } from '../services/api';
import type { User } from '../types';

export interface Stage1Ticket {
  ticket_id: string;
  user_email: string;
  user_name: string;
  expires_in_seconds: number;
  timestamp?: number;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  simulationMode: boolean;
  deviceStatus: 'online' | 'offline';
  stage1Ticket: Stage1Ticket | null;
  setStage1Ticket: (ticket: Stage1Ticket | null) => void;
  clearStage1Ticket: () => void;
  setSimulationMode: (val: boolean) => Promise<void>;
  login: (email: string, password: string, hardwareTicketId?: string) => Promise<any>;
  register: (name: string, email: string, password: string, role?: string) => Promise<any>;
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
  const [stage1Ticket, setStage1TicketState] = useState<Stage1Ticket | null>(() => {
    try {
      const saved = sessionStorage.getItem('forensic_stage1_ticket');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed && parsed.ticket_id) {
          const age = Date.now() - (parsed.timestamp || 0);
          if (age < (parsed.expires_in_seconds || 300) * 1000) {
            return parsed;
          }
        }
      }
    } catch (_) {}
    return null;
  });

  const setStage1Ticket = (t: Stage1Ticket | null) => {
    setStage1TicketState(t);
    if (t) {
      try {
        sessionStorage.setItem('forensic_stage1_ticket', JSON.stringify({ ...t, timestamp: Date.now() }));
      } catch (_) {}
    } else {
      try {
        sessionStorage.removeItem('forensic_stage1_ticket');
      } catch (_) {}
    }
  };

  const clearStage1Ticket = () => {
    setStage1Ticket(null);
  };

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
          if (data.type === 'hardware_stage1_success') {
            console.log("[WS Stage 1 Success]:", data);
            setStage1Ticket({
              ticket_id: data.ticket_id,
              user_email: data.user_email,
              user_name: data.user_name,
              expires_in_seconds: data.expires_in_seconds || 300,
              timestamp: Date.now()
            });
          } else if (data.type === 'hardware_stage1_denied') {
            console.warn("[WS Stage 1 Denied]:", data);
          } else if (data.type === 'device_status') {
            setDeviceStatus(data.status);
          } else if (data.type === 'hardware_bridge_status') {
            setDeviceStatus(data.bridge?.status === 'Connected' ? 'online' : 'offline');
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

  // Proactive check of hardware bridge and device status
  useEffect(() => {
    const checkBridgeStatus = async () => {
      try {
        const bRes = await api.get('/hardware/bridge-status');
        if (bRes.data?.status === 'Connected') {
          setDeviceStatus('online');
          return;
        }
        const devRes = await api.get('/hardware/devices');
        const list = Array.isArray(devRes.data) ? devRes.data : (devRes.data?.devices || []);
        const hasOnline = list.some((d: any) => d.status === 'online');
        setDeviceStatus(hasOnline ? 'online' : 'offline');
      } catch (_) {}
    };

    checkBridgeStatus();
    const interval = setInterval(checkBridgeStatus, 3000);
    return () => clearInterval(interval);
  }, []);

  // Polling backup for Stage 1 hardware authentication challenge ticket
  useEffect(() => {
    const pollInterval = setInterval(async () => {
      if (typeof window === 'undefined') return;
      if (window.location.pathname !== '/login' && window.location.pathname !== '/' && window.location.pathname !== '/hardware-auth') return;
      if (localStorage.getItem('forensic_token')) return;

      // Prevent immediate re-authentication loop if user explicitly logged out in the last 10s
      try {
        const justLoggedOut = sessionStorage.getItem('forensic_just_logged_out');
        if (justLoggedOut && (Date.now() - parseInt(justLoggedOut, 10)) < 10000) {
          return;
        }
      } catch (_) {}

      try {
        const res = await api.get('/hardware/latest-auth');
        if (res.data?.stage1_verified && res.data?.ticket_id) {
          setStage1Ticket({
            ticket_id: res.data.ticket_id,
            user_email: res.data.user_email,
            user_name: res.data.user_name,
            expires_in_seconds: res.data.expires_in_seconds || 300,
            timestamp: Date.now()
          });
        }
      } catch (e) {
        // Silent catch during background poll
      }
    }, 1500);

    return () => clearInterval(pollInterval);
  }, []);

  const authenticateWithToken = (jwtToken: string, userData: any) => {
    try {
      sessionStorage.removeItem('forensic_just_logged_out');
    } catch (_) {}
    localStorage.setItem('forensic_token', jwtToken);
    localStorage.setItem('forensic_user', JSON.stringify(userData));
    api.defaults.headers.common['Authorization'] = `Bearer ${jwtToken}`;
    setUser(userData);
    setToken(jwtToken);
  };

  const login = async (email: string, password: string, hardwareTicketId?: string) => {
    const cleanEmail = email.trim().toLowerCase();
    const payload: any = { email: cleanEmail, password };
    if (hardwareTicketId) {
      payload.hardware_ticket_id = hardwareTicketId;
    }
    const response = await api.post('/auth/login', payload);
    const { access_token, user: userData } = response.data;
    clearStage1Ticket();
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
    clearStage1Ticket();
    authenticateWithToken(access_token, userData);
    return userData;
  };

  const logout = () => {
    clearStage1Ticket();
    try {
      sessionStorage.setItem('forensic_just_logged_out', Date.now().toString());
    } catch (_) {}
    localStorage.removeItem('forensic_token');
    localStorage.removeItem('forensic_user');
    delete api.defaults.headers.common['Authorization'];
    setUser(null);
    setToken(null);
    // Explicitly consume/invalidate hardware session on server
    api.post('/hardware/consume-auth').catch(() => {});
    if (typeof window !== 'undefined') {
      window.location.href = '/login';
    }
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
        stage1Ticket,
        setStage1Ticket,
        clearStage1Ticket,
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
