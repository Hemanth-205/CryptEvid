import React, { useState, useRef } from 'react';
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
  UserCheck,
  Usb,
  CheckCircle2,
  Terminal
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
      window.location.href = '/dashboard';
    }
  }, [isAuthenticated]);

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
    const cleanUrl = customApiUrl.trim().replace(/\/$/, '');
    if (cleanUrl) {
      const formatted = cleanUrl.endsWith('/api') ? cleanUrl : `${cleanUrl}/api`;
      localStorage.setItem('forensic_api_url', formatted);
      setCustomApiUrl(formatted);
    } else {
      localStorage.removeItem('forensic_api_url');
      setCustomApiUrl('');
    }
    setApiSaved(true);
    setTimeout(() => {
      setApiSaved(false);
      window.location.reload();
    }, 500);
  };

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [simulatingAuth, setSimulatingAuth] = useState<'rfid' | 'fingerprint' | null>(null);

  // Physical Hardware Detection States
  const [detectedRfid, setDetectedRfid] = useState<string | null>(null);
  const [detectedFid, setDetectedFid] = useState<number | null>(null);
  const [serialLogs, setSerialLogs] = useState<string[]>([]);
  const detectedRfidRef = useRef<string | null>(null);
  const detectedFidRef = useRef<number | null>(null);

  // Web Serial for physically wired ESP32 over USB
  const [usbConnected, setUsbConnected] = useState(false);
  const [usbPort, setUsbPort] = useState<any>(null);

  const handleConnectUsb = async () => {
    if (usbConnected && usbPort) {
      try {
        await usbPort.close();
      } catch (e) {
        console.error(e);
      }
      setUsbPort(null);
      setUsbConnected(false);
      return;
    }

    if (!('serial' in navigator)) {
      alert("Web Serial is supported in Google Chrome, Microsoft Edge, Opera, and Brave on PC/Mac. Please open the platform in Chrome or Edge to connect your USB hardware.");
      return;
    }

    try {
      const port = await (navigator as any).serial.requestPort();
      await port.open({ baudRate: 115200 });
      setUsbPort(port);
      setUsbConnected(true);

      // Send initial heartbeat to mark node online
      await api.post('/hardware/heartbeat', {
        device: "ESP32_WIFI",
        macAddress: "DA:51:53:00:95:7C",
        firmwareVersion: "v1.0.4-forensic-usb"
      });

      // Keep sending periodic heartbeat while USB is connected
      const hbInterval = setInterval(() => {
        api.post('/hardware/heartbeat', {
          device: "ESP32_WIFI",
          macAddress: "DA:51:53:00:95:7C",
          firmwareVersion: "v1.0.4-forensic-usb"
        }).catch(console.error);
      }, 15000);

      // Read serial stream in background
      const textDecoder = new TextDecoderStream();
      port.readable.pipeTo(textDecoder.writable).catch(() => {});
      const reader = textDecoder.readable.getReader();

      let streamBuffer = "";
      (async () => {
        try {
          while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            if (value) {
              streamBuffer += value;
              const lines = streamBuffer.split(/[\r\n]+/);
              // Retain last unfinished segment in streamBuffer
              streamBuffer = lines.pop() || "";

              for (const line of lines) {
                const trimmed = line.trim();
                if (!trimmed) continue;

                // Push to live serial terminal view (limit to last 20 lines)
                setSerialLogs(prev => [...prev.slice(-19), trimmed]);

                const cleanUpper = trimmed.replace(/[\s:-]/g, '').toUpperCase();
                let foundRfid: string | null = null;
                let foundFid: number | null = null;

                // 1. Identify RFID Card
                if (cleanUpper.includes('105B965C') || cleanUpper.includes('ADMIN')) {
                  foundRfid = '105B965C';
                } else if (cleanUpper.includes('C0A3CF54') || cleanUpper.includes('INVESTIGATOR')) {
                  foundRfid = 'C0A3CF54';
                } else {
                  const hexMatch = trimmed.match(/([0-9a-fA-F]{2}[\s:-]?[0-9a-fA-F]{2}[\s:-]?[0-9a-fA-F]{2}[\s:-]?[0-9a-fA-F]{2})/i);
                  if (hexMatch) {
                    const candidate = hexMatch[1].replace(/[\s:-]/g, '').toUpperCase();
                    if (candidate === '105B965C' || candidate === 'C0A3CF54') {
                      foundRfid = candidate;
                    }
                  }
                }

                if (foundRfid) {
                  detectedRfidRef.current = foundRfid;
                  setDetectedRfid(foundRfid);
                }

                // 2. Identify Fingerprint Sensor match
                if (trimmed === '1' || trimmed === '2') {
                  foundFid = parseInt(trimmed, 10);
                } else {
                  const fpMatch = trimmed.match(/(?:fingerprint|finger|id|fid|found|matched|match|slot)\s*[:#]?\s*([12])\b/i);
                  if (fpMatch) {
                    foundFid = parseInt(fpMatch[1], 10);
                  }
                }

                if (foundFid !== null) {
                  detectedFidRef.current = foundFid;
                  setDetectedFid(foundFid);
                }

                // 3. Fallback: verification keywords
                if (cleanUpper.includes('VERIFIED') || cleanUpper.includes('GRANTED') || cleanUpper.includes('SUCCESS') || cleanUpper.includes('AUTHORIZED')) {
                  if (!foundRfid && !detectedRfidRef.current && foundFid === null && detectedFidRef.current === null) {
                    if (cleanUpper.includes('2') || cleanUpper.includes('INVESTIGATOR')) {
                      foundFid = 2;
                      foundRfid = 'C0A3CF54';
                    } else {
                      foundFid = 1;
                      foundRfid = '105B965C';
                    }
                    detectedRfidRef.current = foundRfid;
                    detectedFidRef.current = foundFid;
                    setDetectedRfid(foundRfid);
                    setDetectedFid(foundFid);
                  }
                }

                // 4. Authenticate if any factor is detected
                const activeRfid = foundRfid || detectedRfidRef.current;
                const activeFid = foundFid !== null ? foundFid : detectedFidRef.current;

                if (activeRfid || activeFid !== null) {
                  setError(null);
                  try {
                    const payload: any = {
                      deviceId: "ESP32_WIFI",
                      timestamp: new Date().toISOString()
                    };
                    if (activeRfid) payload.rfid = activeRfid;
                    if (activeFid !== null) payload.fingerprintId = activeFid;

                    console.log("[ESP32 USB]: Authenticating with payload:", payload);
                    const res = await api.post('/hardware/authenticate', payload);
                    if (res.data?.jwt) {
                      setIsSubmitting(true);
                      authenticateWithToken(res.data.jwt, res.data.user);
                      // Force immediate hard navigation to dashboard
                      window.location.href = '/dashboard';
                      return;
                    }
                  } catch (authErr: any) {
                    console.error("Hardware auth error:", authErr);
                    setError(authErr.response?.data?.detail || "Hardware credential authentication failed.");
                  }
                }
              }
            }
          }
        } catch (readErr) {
          console.warn("Serial reader closed:", readErr);
        } finally {
          clearInterval(hbInterval);
          try { reader.releaseLock(); } catch (_) {}
          setUsbConnected(false);
          setUsbPort(null);
        }
      })();
    } catch (err: any) {
      if (err.name !== 'NotFoundError') {
        console.error("Failed to connect USB serial port", err);
        setError(`Failed to open USB serial port: ${err.message}`);
      }
    }
  };

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
        rfid: type === 'rfid' ? "105B965C" : undefined,
        fingerprintId: type === 'fingerprint' ? 1 : undefined,
        timestamp: new Date().toISOString()
      };

      const res = await api.post('/hardware/authenticate', payload);
      
      if (res.data.success && res.data.jwt) {
        authenticateWithToken(res.data.jwt, res.data.user);
        window.location.href = '/dashboard';
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
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${deviceStatus === 'online' || usbConnected ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`}></span>
            <span className={`text-[11px] font-mono font-bold ${deviceStatus === 'online' || usbConnected ? 'text-emerald-700' : 'text-red-600'}`}>
              {deviceStatus === 'online' || usbConnected ? 'NODE ONLINE' : 'NODE OFFLINE'}
            </span>
            <button
              type="button"
              onClick={handleConnectUsb}
              className={`text-[10px] px-2 py-0.5 rounded font-mono font-semibold transition-all flex items-center gap-1 cursor-pointer ${
                usbConnected
                  ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                  : 'bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200'
              }`}
              title={usbConnected ? "Click to disconnect USB" : "Connect wired ESP32 directly via USB COM port"}
            >
              <Usb className="w-3 h-3" />
              <span>{usbConnected ? 'USB Active' : 'Connect USB Wire'}</span>
            </button>
          </div>
        </div>

        {/* TAB 1: LOGIN FORM */}
        {authMode === 'login' && (
          <>
            {!simulationMode ? (
              /* Pure Physical Hardware Authentication */
              <div className="py-4 space-y-4">
                {/* Main Physical Security Header */}
                <div className="text-center space-y-1.5">
                  <div className="w-16 h-16 rounded-2xl bg-amber-50 border border-amber-200 flex items-center justify-center mx-auto text-amber-600 shadow-sm relative">
                    <Fingerprint className={`w-8 h-8 ${isSubmitting ? 'text-emerald-600 animate-spin' : 'animate-pulse'}`} />
                    {isSubmitting && (
                      <span className="absolute -top-1 -right-1 flex h-4 w-4">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-4 w-4 bg-emerald-500"></span>
                      </span>
                    )}
                  </div>
                  <div className="text-xs font-bold text-slate-800 uppercase tracking-wider font-mono">
                    {isSubmitting ? 'Hardware Verified! Opening Station...' : 'Physical Hardware Verification'}
                  </div>
                  <p className="text-[11px] text-slate-500 max-w-xs mx-auto leading-relaxed">
                    {isSubmitting
                      ? 'Cryptographic credentials verified. Initializing secure forensic session...'
                      : 'Physical token scan mandatory. Scan your RFID card or biometric finger on the ESP32 node.'}
                  </p>
                </div>

                {/* Factor 1: RFID Badge Card */}
                <div className={`p-3 rounded-xl border transition-all ${
                  detectedRfid 
                    ? 'bg-emerald-50/80 border-emerald-300 text-emerald-900' 
                    : 'bg-slate-50 border-slate-200 text-slate-700'
                }`}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                        detectedRfid ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-200 text-slate-500'
                      }`}>
                        <Scan className="w-4 h-4" />
                      </div>
                      <div>
                        <div className="text-xs font-bold font-mono">1. RFID Smart Card (RC522)</div>
                        <div className="text-[10px] text-slate-500">
                          {detectedRfid 
                            ? `Scanned: ${detectedRfid === '105B965C' ? '10 5B 96 5C (Admin)' : detectedRfid === 'C0A3CF54' ? 'C0 A3 CF 54 (Investigator)' : detectedRfid}`
                            : 'Waiting for card tap (10 5B 96 5C / C0 A3 CF 54)...'}
                        </div>
                      </div>
                    </div>
                    {detectedRfid ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                    ) : (
                      <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono bg-amber-100 text-amber-800 animate-pulse">
                        Scanning...
                      </span>
                    )}
                  </div>
                </div>

                {/* Factor 2: Optical Biometric Sensor */}
                <div className={`p-3 rounded-xl border transition-all ${
                  detectedFid !== null 
                    ? 'bg-emerald-50/80 border-emerald-300 text-emerald-900' 
                    : 'bg-slate-50 border-slate-200 text-slate-700'
                }`}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                        detectedFid !== null ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-200 text-slate-500'
                      }`}>
                        <Fingerprint className="w-4 h-4" />
                      </div>
                      <div>
                        <div className="text-xs font-bold font-mono">2. Biometric Fingerprint (R307)</div>
                        <div className="text-[10px] text-slate-500">
                          {detectedFid !== null 
                            ? `Matched Finger ID: #${detectedFid} (${detectedFid === 1 ? 'Admin' : 'Investigator'})`
                            : 'Waiting for enrolled finger touch (ID #1 / #2)...'}
                        </div>
                      </div>
                    </div>
                    {detectedFid !== null ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                    ) : (
                      <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono bg-amber-100 text-amber-800 animate-pulse">
                        Standby...
                      </span>
                    )}
                  </div>
                </div>

                {/* Real-time USB Serial Console (Active when USB is connected) */}
                {usbConnected && (
                  <div className="p-2.5 bg-slate-950 text-slate-100 rounded-xl font-mono text-[10px] space-y-1 border border-slate-800">
                    <div className="flex items-center justify-between text-slate-400 border-b border-slate-800 pb-1">
                      <span className="flex items-center gap-1">
                        <Terminal className="w-3 h-3 text-emerald-400" />
                        ESP32 Live Serial Console (115200 Baud)
                      </span>
                      <span className="text-emerald-400 flex items-center gap-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                        Listening
                      </span>
                    </div>
                    <div className="max-h-24 overflow-y-auto space-y-0.5 font-mono text-[10px] text-slate-300">
                      {serialLogs.length === 0 ? (
                        <div className="text-slate-500 italic">Connected to COM port. Waiting for ESP32 bytes...</div>
                      ) : (
                        serialLogs.slice(-6).map((log, i) => (
                          <div key={i} className="truncate text-slate-300">
                            <span className="text-emerald-500 mr-1">&gt;</span>
                            {log}
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                )}

                {/* Helpful Instruction Footer */}
                <div className="text-[11px] text-slate-500 text-center space-y-1 pt-1 border-t border-slate-100">
                  <p>
                    {usbConnected 
                      ? 'Wired USB Active: Scan your RFID or place your finger on the sensor.'
                      : 'Connecting via USB? Click "Connect USB Wire" above. If using WiFi, ensure the ESP32 is powered on.'}
                  </p>
                  <p className="text-[10px] text-slate-400">
                    Important: Close Arduino IDE Serial Monitor so the browser has exclusive access to the USB port.
                  </p>
                </div>
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
                Backend API URL (Render / Railway / Custom)
              </label>
              <input
                type="text"
                value={customApiUrl}
                onChange={(e) => setCustomApiUrl(e.target.value)}
                placeholder="https://cryptevid-final.onrender.com"
                className="ws-input w-full text-xs font-mono"
              />
              <p className="text-[10px] text-slate-500">
                Default: <span className="font-mono text-slate-700 font-semibold">https://cryptevid-final.onrender.com</span>
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
