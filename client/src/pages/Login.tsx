import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { 
  Fingerprint, 
  Cpu, 
  AlertTriangle, 
  Eye, 
  EyeOff, 
  Loader2, 
  Scan, 
  RefreshCw, 
  Lock, 
  ShieldCheck,
  ArrowLeft,
  UserCheck
} from 'lucide-react';

import api, { getApiBaseUrl } from '../services/api';

export const Login: React.FC = () => {
  const navigate = useNavigate();
  const { 
    login, 
    register,
    simulationMode, 
    deviceStatus, 
    setSimulationMode,
    authenticateWithToken,
    isAuthenticated
  } = useAuth();

  // If already authenticated, redirect to dashboard
  React.useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const [authMode, setAuthMode] = useState<'login' | 'signup'>('login');

  // Login state
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  // Signup state
  const [regName, setRegName] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regConfirmPassword, setRegConfirmPassword] = useState('');
  const [regRole, setRegRole] = useState<'investigator' | 'admin' | 'readonly'>('investigator');
  const [showRegPassword, setShowRegPassword] = useState(false);

  // Backend API URL Customization (for cloud/Railway deployments)
  const [showApiConfig, setShowApiConfig] = useState(false);
  const [customApiUrl, setCustomApiUrl] = useState(
    typeof window !== 'undefined' ? localStorage.getItem('forensic_api_url') || '' : ''
  );
  const [apiSaved, setApiSaved] = useState(false);

  const handleSaveApiUrl = (e: React.FormEvent) => {
    e.preventDefault();
    if (customApiUrl.trim()) {
      localStorage.setItem('forensic_api_url', customApiUrl.trim());
    } else {
      localStorage.removeItem('forensic_api_url');
    }
    setApiSaved(true);
    setTimeout(() => {
      setApiSaved(false);
      window.location.reload();
    }, 800);
  };

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [simulatingAuth, setSimulatingAuth] = useState<'rfid' | 'fingerprint' | null>(null);

  const handleCredentialsSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanId = email.trim();
    if (!cleanId || !password) return;
    
    setIsSubmitting(true);
    setError(null);
    try {
      await login(cleanId, password);
      navigate('/dashboard', { replace: true });
    } catch (err: any) {
      console.error('Login error:', err);
      if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else if (err.response?.status === 503) {
        setError(err.response?.data?.detail || 'Database service temporarily unavailable.');
      } else if (err.response?.status === 500) {
        setError('Server encountered an internal error. Please check server logs.');
      } else if (!err.response) {
        setError(`Unable to connect to forensic backend (${getApiBaseUrl()}). Please ensure the service is running.`);
      } else {
        setError('Authentication failed. Invalid credentials.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSignupSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!regName.trim() || !regEmail.trim() || !regPassword) {
      setError('Please fill in all mandatory investigator credentials.');
      return;
    }
    if (regPassword !== regConfirmPassword) {
      setError('Master passphrase and confirmation do not match.');
      return;
    }
    if (regPassword.length < 6) {
      setError('Passphrase must be at least 6 characters in length.');
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      await register(regName.trim(), regEmail.trim(), regPassword, regRole);
      navigate('/dashboard', { replace: true });
    } catch (err: any) {
      console.error(err);
      if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else if (!err.response) {
        setError('Unable to reach backend service. Please ensure the server is online.');
      } else {
        setError('Registration failed. Email may already be registered.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  // Simulate hardware input by posting to the hardware endpoint
  const handleSimulateHardware = async (type: 'rfid' | 'fingerprint') => {
    setSimulatingAuth(type);
    setError(null);
    try {
      const payload = {
        deviceId: "ESP32_01",
        rfid: type === 'rfid' ? "04A1B2C3" : undefined,
        fingerprintId: type === 'fingerprint' ? 12 : undefined,
        timestamp: new Date().toISOString()
      };

      const res = await api.post('/hardware/authenticate', payload);
      
      if (res.data.success && res.data.jwt) {
        authenticateWithToken(res.data.jwt, res.data.user);
        navigate('/dashboard', { replace: true });
      } else {
        setError("Hardware verification failed: Identifier not bound to active forensic investigator profile.");
      }
    } catch (err: any) {
      console.error(err);
      if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else if (!err.response) {
        setError("Unable to connect to backend service. Please verify server status.");
      } else {
        setError("Hardware simulation authentication failed.");
      }
    } finally {
      setIsSubmitting(false);
      setSimulatingAuth(null);
    }
  };

  // Quick Demo Credentials helper
  const handleFillDemo = (demoEmail: string, demoPass: string) => {
    setAuthMode('login');
    setEmail(demoEmail);
    setPassword(demoPass);
    setError(null);
  };

  return (
    <div className="min-h-screen w-full flex flex-col items-center justify-center p-4 relative overflow-hidden font-sans select-none bg-slate-100">
      {/* Soft Ambient Accents */}
      <div className="absolute -top-32 -left-32 w-96 h-96 rounded-full bg-blue-100/60 blur-[100px] pointer-events-none" />
      <div className="absolute top-1/2 -right-32 w-96 h-96 rounded-full bg-amber-100/60 blur-[120px] pointer-events-none" />

      {/* Back to Platform Overview Link */}
      <div className="w-full max-w-md mb-3 flex flex-wrap items-center justify-between gap-2 z-10 px-1">
        <Link
          to="/"
          className="text-xs text-slate-500 hover:text-slate-900 flex items-center gap-1.5 transition-colors font-medium"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Platform Overview</span>
        </Link>
        <span className="text-[10px] sm:text-[11px] text-slate-400 font-mono">ISO/IEC 27037 Standard</span>
      </div>

      {/* Light Professional Login Container */}
      <div className="w-full max-w-md bg-white border border-slate-200/90 rounded-2xl p-4.5 sm:p-7 space-y-4 sm:space-y-5 relative z-10 shadow-2xl shadow-slate-900/5 animate-fade-in-up">
        {/* Terminal Header */}
        <div className="flex items-center justify-between border-b border-slate-200 pb-4">
          <div className="flex items-center gap-3">
            <img
              src="/cryptevid_logo.png"
              alt="CRYPTEVID"
              className="h-14 sm:h-16 w-auto object-contain rounded-xl shadow-xs bg-white p-0.5 border border-slate-100"
            />
            <div>
              <h1 className="text-base font-extrabold text-slate-900 tracking-tight font-sans flex items-center gap-1.5">
                CRYPTEVID <ShieldCheck className="w-4 h-4 text-emerald-500" />
              </h1>
              <p className="text-[11px] text-slate-500">
                Secure Digital Evidence & Forensic Intelligence Platform
              </p>
            </div>
          </div>
        </div>

        {/* Tab Switcher: Sign In / Register Account */}
        <div className="flex rounded-xl bg-slate-100 p-1 border border-slate-200 text-xs font-semibold">
          <button
            type="button"
            onClick={() => { setAuthMode('login'); setError(null); }}
            className={`flex-1 py-1.5 rounded-lg transition-all ${
              authMode === 'login'
                ? 'bg-white text-slate-900 shadow-xs border border-slate-200 font-bold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Investigator Sign In
          </button>
          <button
            type="button"
            onClick={() => { setAuthMode('signup'); setError(null); }}
            className={`flex-1 py-1.5 rounded-lg transition-all ${
              authMode === 'signup'
                ? 'bg-white text-slate-900 shadow-xs border border-slate-200 font-bold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Register Account
          </button>
        </div>

        {/* Global Error Banner */}
        {error && (
          <div className="p-3.5 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs flex items-start gap-2.5 shadow-xs">
            <AlertTriangle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
            <span className="leading-relaxed font-sans">{error}</span>
          </div>
        )}

        {/* ESP32 Hardware Status Badge */}
        <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2 text-slate-600">
            <Cpu className="w-3.5 h-3.5 text-amber-600" />
            <span className="text-[11px] font-mono font-semibold">HARDWARE NODE (ESP32):</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-full ${deviceStatus === 'online' ? 'bg-emerald-500' : 'bg-red-500'}`}></span>
            <span className={`text-[11px] font-mono font-bold ${deviceStatus === 'online' ? 'text-emerald-700' : 'text-red-600'}`}>
              {deviceStatus === 'online' ? 'NODE ONLINE' : 'NODE OFFLINE'}
            </span>
          </div>
        </div>

        {/* TAB 1: LOGIN FORM */}
        {authMode === 'login' && (
          <>
            {!simulationMode ? (
              /* Pure Physical Hardware Auth */
              <div className="py-6 text-center space-y-4">
                <div className="w-20 h-20 rounded-2xl bg-amber-50 border border-amber-200 flex items-center justify-center mx-auto text-amber-600 shadow-sm">
                  <Fingerprint className="w-10 h-10 animate-pulse" />
                </div>
                <div className="text-xs font-bold text-slate-800 uppercase tracking-wider font-mono">
                  Physical Hardware Token Required
                </div>
                <p className="text-xs text-slate-500 max-w-xs mx-auto leading-relaxed">
                  Standard credential login is locked in hardware-enforced mode. Scan authorized RFID badge or verify biometric index on physical terminal reader.
                </p>
              </div>
            ) : (
              /* Standard Credential Login */
              <form onSubmit={handleCredentialsSubmit} className="space-y-4">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1.5 font-sans">
                    Investigator Identity (Email or Username)
                  </label>
                  <input
                    type="text"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="admin@forensics.gov or admin"
                    className="ws-input w-full"
                    autoCapitalize="none"
                    autoCorrect="off"
                    autoComplete="username"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1.5 font-sans">
                    Access Passphrase / Key
                  </label>
                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••••••"
                      className="ws-input w-full pr-10"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {/* Quick Demo Credentials */}
                <div className="flex items-center justify-between text-[11px] text-slate-500 pt-0.5">
                  <span>Demo profiles:</span>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => handleFillDemo('admin@forensics.gov', 'password123')}
                      className="text-amber-700 font-semibold hover:underline"
                    >
                      Admin
                    </button>
                    <span>•</span>
                    <button
                      type="button"
                      onClick={() => handleFillDemo('investigator@forensics.gov', 'password123')}
                      className="text-blue-700 font-semibold hover:underline"
                    >
                      Investigator
                    </button>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full ws-btn ws-btn-amber py-2.5 text-xs flex items-center justify-center gap-2 mt-2 disabled:opacity-50"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Validating Cryptographic Credentials...</span>
                    </>
                  ) : (
                    <>
                      <Lock className="w-4 h-4" />
                      <span>Authenticate Workstation</span>
                    </>
                  )}
                </button>
              </form>
            )}

            {/* Hardware Simulator Drawer */}
            {simulationMode && (
              <div className="pt-3 border-t border-slate-200 space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold text-slate-600 uppercase font-mono tracking-wider">
                    Hardware Node Simulation
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => handleSimulateHardware('rfid')}
                    disabled={simulatingAuth !== null}
                    className="ws-btn ws-btn-secondary p-2 text-xs flex items-center justify-center gap-2 disabled:opacity-50"
                  >
                    {simulatingAuth === 'rfid' ? (
                      <RefreshCw className="w-3.5 h-3.5 animate-spin text-amber-600" />
                    ) : (
                      <Scan className="w-3.5 h-3.5 text-amber-600" />
                    )}
                    <span>Simulate RFID</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleSimulateHardware('fingerprint')}
                    disabled={simulatingAuth !== null}
                    className="ws-btn ws-btn-secondary p-2 text-xs flex items-center justify-center gap-2 disabled:opacity-50"
                  >
                    {simulatingAuth === 'fingerprint' ? (
                      <RefreshCw className="w-3.5 h-3.5 animate-spin text-amber-600" />
                    ) : (
                      <Fingerprint className="w-3.5 h-3.5 text-amber-600" />
                    )}
                    <span>Simulate Bio</span>
                  </button>
                </div>
              </div>
            )}
          </>
        )}

        {/* TAB 2: SIGN UP FORM */}
        {authMode === 'signup' && (
          <form onSubmit={handleSignupSubmit} className="space-y-3.5">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Full Legal Name / Examiner Badge
              </label>
              <input
                type="text"
                value={regName}
                onChange={e => setRegName(e.target.value)}
                placeholder="Agent Sarah Connor"
                className="ws-input w-full text-xs"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Official Agency Email
              </label>
              <input
                type="email"
                value={regEmail}
                onChange={e => setRegEmail(e.target.value)}
                placeholder="sarah.c@forensics.gov"
                className="ws-input w-full text-xs font-mono"
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-2.5">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Passphrase
                </label>
                <div className="relative">
                  <input
                    type={showRegPassword ? 'text' : 'password'}
                    value={regPassword}
                    onChange={e => setRegPassword(e.target.value)}
                    placeholder="••••••••"
                    className="ws-input w-full pr-7 text-xs font-mono"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowRegPassword(!showRegPassword)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  >
                    {showRegPassword ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Confirm
                </label>
                <input
                  type="password"
                  value={regConfirmPassword}
                  onChange={e => setRegConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                  className="ws-input w-full text-xs font-mono"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Assigned Station Role
              </label>
              <select
                value={regRole}
                onChange={e => setRegRole(e.target.value as any)}
                className="ws-input w-full text-xs"
              >
                <option value="investigator">Digital Forensic Investigator (Standard)</option>
                <option value="admin">Chief Laboratory Administrator</option>
                <option value="readonly">Read-Only Legal / Judicial Auditor</option>
              </select>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full ws-btn ws-btn-amber py-2.5 text-xs flex items-center justify-center gap-2 mt-2"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Registering Investigator...</span>
                </>
              ) : (
                <>
                  <UserCheck className="w-4 h-4" />
                  <span>Create Account & Enter Station</span>
                </>
              )}
            </button>
          </form>
        )}

        {/* Cloud / Railway Backend Connection Settings */}
        <div className="pt-2 border-t border-slate-100">
          <div className="flex items-center justify-between">
            <button
              type="button"
              onClick={() => setShowApiConfig(!showApiConfig)}
              className="text-[11px] text-slate-400 hover:text-slate-600 font-mono flex items-center gap-1 cursor-pointer"
            >
              <span>API Endpoint:</span>
              <span className="font-semibold text-slate-600 underline truncate max-w-[200px]">
                {getApiBaseUrl()}
              </span>
            </button>
            <button
              type="button"
              onClick={() => setShowApiConfig(!showApiConfig)}
              className="text-[10px] text-blue-600 hover:underline font-mono"
            >
              {showApiConfig ? 'Hide' : 'Configure'}
            </button>
          </div>

          {showApiConfig && (
            <form onSubmit={handleSaveApiUrl} className="mt-2.5 p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-2">
              <label className="block text-[11px] font-bold text-slate-700">
                Backend API URL (for Railway / Cloud Deployments)
              </label>
              <input
                type="text"
                value={customApiUrl}
                onChange={(e) => setCustomApiUrl(e.target.value)}
                placeholder="https://your-backend.up.railway.app"
                className="ws-input w-full text-xs font-mono"
              />
              <p className="text-[10px] text-slate-500">
                Leave blank to reset to default ({import.meta.env.VITE_API_URL || 'http://localhost:8000'}).
              </p>
              <div className="flex justify-end gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => {
                    localStorage.removeItem('forensic_api_url');
                    setCustomApiUrl('');
                    window.location.reload();
                  }}
                  className="ws-btn ws-btn-secondary py-1 px-2 text-[11px]"
                >
                  Reset Default
                </button>
                <button
                  type="submit"
                  className="ws-btn ws-btn-primary py-1 px-3 text-[11px]"
                >
                  {apiSaved ? 'Saved & Reloading...' : 'Save & Connect'}
                </button>
              </div>
            </form>
          )}
        </div>

        {/* Footer info & Mode toggle */}
        <div className="pt-3 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500">
          <span className="text-[11px]">System v2.4 (Court-Admissible)</span>
          <button
            type="button"
            onClick={() => setSimulationMode(!simulationMode)}
            className="text-blue-600 hover:text-blue-800 hover:underline font-semibold text-xs"
          >
            Switch to {simulationMode ? "Hardware-Only" : "Simulation"} Mode
          </button>
        </div>
      </div>
    </div>
  );
};

export default Login;
