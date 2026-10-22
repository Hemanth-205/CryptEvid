import React, { useState, useEffect } from 'react';
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
  Lock, 
  Unlock, 
  ShieldCheck,
  ArrowLeft,
  UserCheck,
  Usb,
  CheckCircle2,
  Clock,
  Radio,
  ArrowRight
} from 'lucide-react';

import api, { getApiBaseUrl } from '../services/api';

export const Login: React.FC = () => {
  const navigate = useNavigate();
  const { 
    login, 
    register,
    simulationMode, 
    setSimulationMode,
    isAuthenticated,
    stage1Ticket,
    setStage1Ticket,
    clearStage1Ticket
  } = useAuth();

  // If already authenticated, redirect to dashboard
  useEffect(() => {
    if (isAuthenticated || (typeof window !== 'undefined' && localStorage.getItem('forensic_token'))) {
      window.location.href = '/dashboard';
    }
  }, [isAuthenticated]);

  const [authMode, setAuthMode] = useState<'login' | 'signup'>('login');

  // Stage 1 vs Stage 2 state
  // Stage 1: Hardware authentication (RFID + Fingerprint -> Ticket)
  // Stage 2: Software credentials login (User ID + Password + Ticket -> JWT)
  const isStage1Complete = !!stage1Ticket;

  // Countdown timer for 5-minute single-use ticket
  const [ticketSecondsLeft, setTicketSecondsLeft] = useState<number>(300);

  useEffect(() => {
    if (!stage1Ticket) {
      setTicketSecondsLeft(300);
      return;
    }

    const updateTimer = () => {
      const now = Date.now();
      const createdAt = stage1Ticket.timestamp || now;
      const elapsed = Math.floor((now - createdAt) / 1000);
      const remaining = Math.max(0, (stage1Ticket.expires_in_seconds || 300) - elapsed);
      setTicketSecondsLeft(remaining);

      if (remaining <= 0) {
        clearStage1Ticket();
        setError("Stage 1 Hardware Challenge Ticket expired (5-minute validity limit). Please re-authenticate on the ESP32 hardware.");
      }
    };

    updateTimer();
    const interval = setInterval(updateTimer, 1000);
    return () => clearInterval(interval);
  }, [stage1Ticket, clearStage1Ticket]);

  // Stage 1 Telemetry & Bridge Status polling
  const [stage1State, setStage1State] = useState<{
    state: string;
    bridge_status: string;
    port: string;
    baud_rate: number;
    latest_event?: any;
    detail?: string | null;
  }>({
    state: 'WAITING_CONNECTION',
    bridge_status: 'Disconnected',
    port: 'COM5',
    baud_rate: 115200,
    detail: null
  });

  const [isSimulatingStage1, setIsSimulatingStage1] = useState(false);

  // Poll Stage 1 hardware status from FastAPI
  useEffect(() => {
    let isMounted = true;
    const fetchStage1Status = async () => {
      try {
        const res = await api.get('/hardware/stage1-status');
        if (!isMounted) return;
        setStage1State(res.data);

        // If backend reports an active valid ticket and we don't have it in context, load it
        if (res.data.ticket && !stage1Ticket) {
          setStage1Ticket({
            ticket_id: res.data.ticket.ticket_id,
            user_email: res.data.ticket.user_email,
            user_name: res.data.ticket.user_name,
            allowed_emails: res.data.ticket.allowed_emails,
            expires_in_seconds: res.data.ticket.expires_in_seconds || 300,
            timestamp: Date.now()
          });
          if (res.data.ticket.user_email) {
            setEmail(res.data.ticket.user_email);
          }
          setError(null);
        }
      } catch (_) {}
    };

    fetchStage1Status();
    const interval = setInterval(fetchStage1Status, 1000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [stage1Ticket, setStage1Ticket]);

  // Login form state
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  // Automatically sync email when stage 1 ticket arrives
  useEffect(() => {
    if (stage1Ticket?.user_email && !email) {
      setEmail(stage1Ticket.user_email);
    }
  }, [stage1Ticket]);

  // Signup form state
  const [regName, setRegName] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regConfirmPassword, setRegConfirmPassword] = useState('');
  const [regRole, setRegRole] = useState<'investigator' | 'admin' | 'readonly'>('investigator');
  const [showRegPassword, setShowRegPassword] = useState(false);

  // Backend API URL Customization
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

  // Web Serial directly in browser (alternative to Python bridge)
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
      alert("Web Serial is supported in Chrome, Edge, and Brave. Please use a Chromium-based browser to connect directly over USB.");
      return;
    }

    try {
      const port = await (navigator as any).serial.requestPort();
      await port.open({ baudRate: 115200 });
      setUsbPort(port);
      setUsbConnected(true);
      setError(null);

      // Read serial stream in background
      const textDecoder = new TextDecoderStream();
      port.readable.pipeTo(textDecoder.writable).catch(() => {});
      const reader = textDecoder.readable.getReader();

      let lineBuffer = "";
      (async () => {
        try {
          while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            if (value) {
              lineBuffer += value;
              const lines = lineBuffer.split(/\r?\n/);
              lineBuffer = lines.pop() || "";
              for (const line of lines) {
                const trimmed = line.trim();
                if (!trimmed) continue;

                // Extract CRYPTEVID protocol line from serial stream
                const match = trimmed.match(/CRYPTEVID\|(\d+)\|(GRANTED|DENIED)\|UID=([^|\r\n]+)\|REASON=([^|\r\n]+)/);
                if (match) {
                  const status = match[2];
                  const uidPart = match[3].trim();
                  const reasonPart = match[4].trim();

                  try {
                    const evRes = await api.post("/hardware/events", {
                      status,
                      uid: uidPart,
                      reason: reasonPart,
                      raw_message: match[0]
                    }, {
                      headers: { "X-Bridge-Key": "cryptevid_usb_bridge_secret_dev" }
                    });

                    if (evRes.data?.ticket_id) {
                      setStage1Ticket({
                        ticket_id: evRes.data.ticket_id,
                        user_email: evRes.data.mapped_investigator?.email || "admin@forensics.gov",
                        user_name: evRes.data.mapped_investigator?.name || "Chief Investigator",
                        expires_in_seconds: evRes.data.expires_in_seconds || 300,
                        timestamp: Date.now()
                      });
                      setEmail(evRes.data.mapped_investigator?.email || "admin@forensics.gov");
                      setError(null);
                    }
                  } catch (e: any) {
                    console.error("Web serial event forward error:", e);
                    setError(e.response?.data?.detail || "Hardware event processing failed");
                  }
                } else if (trimmed.includes("RFID_SCANNED:")) {
                  setStage1State(prev => ({
                    ...prev,
                    state: 'RFID_ACCEPTED',
                    detail: 'RFID card detected. Place finger on biometric sensor.'
                  }));
                } else if (trimmed.includes("FINGER_DETECTED") || trimmed.includes("FINGER_SCAN_START")) {
                  setStage1State(prev => ({
                    ...prev,
                    state: 'WAITING_FINGERPRINT',
                    detail: 'Biometric finger detected. Verifying...'
                  }));
                }
              }
            }
          }
        } catch (readErr) {
          console.warn("Web serial reader closed:", readErr);
        } finally {
          try { reader.releaseLock(); } catch (_) {}
          setUsbConnected(false);
          setUsbPort(null);
        }
      })();
    } catch (err: any) {
      if (err.name === 'NotFoundError') {
        return; // User cancelled prompt
      }
      console.warn("Web Serial notice:", err);
      if (stage1State.bridge_status === 'Connected') {
        setError(null);
        alert("The ESP32 is already connected via hardware_serial_bridge.py! You do not need in-browser Web Serial.");
        return;
      }
      setError("Serial COM port could not be opened. Check if another program (like Arduino IDE or python bridge) is using it.");
    }
  };

  // Trigger simulated Stage 1 Hardware Authentication
  const handleSimulateStage1 = async (targetEmail: string = "admin@forensics.gov", fid: number = 6) => {
    setIsSimulatingStage1(true);
    setError(null);
    try {
      const res = await api.post('/hardware/stage1-simulate', {
        uid: "10 5B 96 5C",
        email: targetEmail,
        fingerprint_id: fid
      });

      if (res.data?.success && res.data?.ticket_id) {
        setError(null);
        setStage1Ticket({
          ticket_id: res.data.ticket_id,
          user_email: res.data.user_email,
          user_name: res.data.user_name || (targetEmail.includes("manager") ? "Portal Manager" : "Chief Investigator"),
          allowed_emails: ["admin@forensics.gov", "manager@forensics.gov"],
          expires_in_seconds: res.data.expires_in_seconds || 300,
          timestamp: Date.now()
        });
        setEmail(res.data.user_email);
      }
    } catch (err: any) {
      console.error("Stage 1 simulation failed:", err);
      setError(err.response?.data?.detail || "Stage 1 hardware simulation failed.");
    } finally {
      setIsSimulatingStage1(false);
    }
  };

  // Handle Stage 2 Software Login Credentials Submission
  const handleCredentialsSubmit = async (e?: React.FormEvent, overrideEmail?: string, overridePassword?: string) => {
    if (e) e.preventDefault();
    const cleanId = (overrideEmail !== undefined ? overrideEmail : email).trim();
    const cleanPass = overridePassword !== undefined ? overridePassword : password;
    if (!cleanId || !cleanPass) return;
    
    setIsSubmitting(true);
    setError(null);
    try {
      // Pass the single-use hardware ticket ID from Stage 1
      const loggedUser = await login(cleanId, cleanPass, stage1Ticket?.ticket_id);
      if (loggedUser?.role === 'portal_manager') {
        navigate('/portal-manager', { replace: true });
      } else {
        navigate('/dashboard', { replace: true });
      }
    } catch (err: any) {
      console.error('Login error:', err);
      if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else if (err.response?.status === 503) {
        setError(err.response?.data?.detail || 'Database service temporarily unavailable.');
      } else if (err.response?.status === 401) {
        setError('Incorrect password or invalid hardware ticket. Please verify your credentials.');
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

  const formatCountdown = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="min-h-screen w-full flex flex-col items-center justify-center p-4 relative overflow-hidden font-sans select-none bg-slate-100">
      {/* Soft Ambient Accents */}
      <div className="absolute -top-32 -left-32 w-96 h-96 rounded-full bg-blue-100/60 blur-[100px] pointer-events-none" />
      <div className="absolute top-1/2 -right-32 w-96 h-96 rounded-full bg-amber-100/60 blur-[120px] pointer-events-none" />

      {/* Back to Platform Overview Link */}
      <div className="w-full max-w-lg mb-3 flex flex-wrap items-center justify-between gap-2 z-10 px-1">
        <Link
          to="/"
          className="text-xs text-slate-500 hover:text-slate-900 flex items-center gap-1.5 transition-colors font-medium"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Platform Overview</span>
        </Link>
        <span className="text-[10px] sm:text-[11px] text-slate-400 font-mono">ISO/IEC 27037 Standard • Two-Stage Auth</span>
      </div>

      {/* Main Terminal Container */}
      <div className="w-full max-w-lg bg-white border border-slate-200/90 rounded-2xl p-5 sm:p-7 space-y-5 relative z-10 shadow-2xl shadow-slate-900/5 animate-fade-in-up">
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

        {/* Two-Stage Progress Indicator */}
        <div className="rounded-xl bg-slate-50 border border-slate-200 p-3">
          <div className="flex items-center justify-between text-xs font-semibold">
            {/* Stage 1 Step */}
            <div className={`flex items-center gap-2 ${isStage1Complete ? 'text-emerald-700' : 'text-blue-700 font-bold'}`}>
              <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-mono font-bold ${
                isStage1Complete ? 'bg-emerald-100 text-emerald-700 border border-emerald-300' : 'bg-blue-600 text-white'
              }`}>
                {isStage1Complete ? <CheckCircle2 className="w-4 h-4" /> : '1'}
              </div>
              <span className="text-xs">Stage 1: Hardware Auth</span>
            </div>

            <ArrowRight className="w-3.5 h-3.5 text-slate-400" />

            {/* Stage 2 Step */}
            <div className={`flex items-center gap-2 ${
              isStage1Complete ? 'text-blue-700 font-bold' : 'text-slate-400'
            }`}>
              <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-mono font-bold ${
                isStage1Complete ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-500'
              }`}>
                {isStage1Complete ? '2' : <Lock className="w-3 h-3" />}
              </div>
              <span className="text-xs">Stage 2: Software Login</span>
            </div>
          </div>
        </div>

        {/* Global Error Banner */}
        {error && (
          <div className="p-3.5 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs flex items-start gap-2.5 shadow-xs">
            <AlertTriangle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
            <span className="leading-relaxed font-sans">{error}</span>
          </div>
        )}

        {/* Hardware Status Strip */}
        <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2 text-slate-600">
            <Cpu className="w-3.5 h-3.5 text-amber-600" />
            <span className="text-[11px] font-mono font-semibold">ESP32 PORT ({stage1State.port}):</span>
          </div>
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${
              stage1State.bridge_status === 'Connected' || usbConnected ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'
            }`}></span>
            <span className={`text-[11px] font-mono font-bold ${
              stage1State.bridge_status === 'Connected' || usbConnected ? 'text-emerald-700' : 'text-slate-600'
            }`}>
              {stage1State.bridge_status === 'Connected' || usbConnected ? 'BRIDGE ONLINE' : 'LISTENING'}
            </span>
            <button
              type="button"
              onClick={handleConnectUsb}
              className={`text-[10px] px-2 py-0.5 rounded font-mono font-semibold transition-all flex items-center gap-1 cursor-pointer ${
                stage1State.bridge_status === 'Connected' || usbConnected
                  ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                  : 'bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200'
              }`}
            >
              <Usb className="w-3 h-3" />
              <span>{stage1State.bridge_status === 'Connected' || usbConnected ? 'USB Active' : 'Connect USB Wire'}</span>
            </button>
          </div>
        </div>

        {/* =========================================================================
            STAGE 1: HARDWARE AUTHENTICATION CARD
            Active when no challenge ticket exists
            ========================================================================= */}
        {!isStage1Complete && authMode === 'login' && (
          <div className="space-y-4">
            <div className="p-4 rounded-xl border border-blue-100 bg-blue-50/50 space-y-3">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center shrink-0">
                  <Fingerprint className="w-5 h-5 animate-pulse" />
                </div>
                <div>
                  <h3 className="text-xs font-bold text-slate-900 font-sans">
                    Stage 1 — ESP32 Physical Authentication
                  </h3>
                  <p className="text-[11px] text-slate-500">
                    Scan authorized RFID badge and verify fingerprint on the hardware terminal.
                  </p>
                </div>
              </div>

              {/* Hardware State Status Card */}
              <div className="p-3 rounded-lg bg-white border border-slate-200 space-y-2">
                <div className="flex items-center justify-between text-[11px]">
                  <span className="font-mono text-slate-500">HARDWARE TERMINAL STATE:</span>
                  <span className="font-mono font-bold text-blue-700 flex items-center gap-1">
                    <Radio className="w-3 h-3 text-blue-600 animate-ping" />
                    {stage1State.state}
                  </span>
                </div>
                <p className="text-xs text-slate-700 font-medium">
                  {stage1State.detail || "Connect ESP32 USB wire or launch hardware_serial_bridge.py."}
                </p>
              </div>

              {/* Authorized Shared Hardware Credentials Mapping */}
              <div className="p-2.5 rounded-lg bg-white border border-slate-200 space-y-2">
                <div className="flex items-center justify-between text-[11px] pb-1 border-b border-slate-100">
                  <span className="font-semibold text-slate-700 flex items-center gap-1.5">
                    <Scan className="w-3.5 h-3.5 text-amber-600" />
                    Shared Hardware RFID Card:
                  </span>
                  <span className="font-mono font-bold text-amber-800 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                    10 5B 96 5C
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-[10px]">
                  <div className="p-2 rounded bg-slate-50 border border-slate-200">
                    <span className="block font-bold text-slate-800">Chief Investigator</span>
                    <span className="text-slate-500 font-mono">admin@forensics.gov</span>
                    <span className="block text-emerald-600 font-medium mt-0.5">Biometric FID: 6</span>
                  </div>
                  <div className="p-2 rounded bg-slate-50 border border-slate-200">
                    <span className="block font-bold text-slate-800">Portal Manager</span>
                    <span className="text-slate-500 font-mono">manager@forensics.gov</span>
                    <span className="block text-emerald-600 font-medium mt-0.5">Biometric FID: 15</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Simulation / Testing Action */}
            <div className="grid grid-cols-2 gap-2 pt-1">
              <button
                type="button"
                onClick={() => handleSimulateStage1("admin@forensics.gov", 6)}
                disabled={isSimulatingStage1}
                className="ws-btn ws-btn-amber py-2 text-[11px] flex items-center justify-center gap-1.5 shadow-xs cursor-pointer"
              >
                {isSimulatingStage1 ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                )}
                <span>Simulate Admin (FID 6)</span>
              </button>

              <button
                type="button"
                onClick={() => handleSimulateStage1("manager@forensics.gov", 15)}
                disabled={isSimulatingStage1}
                className="ws-btn ws-btn-secondary py-2 text-[11px] flex items-center justify-center gap-1.5 shadow-xs cursor-pointer"
              >
                {isSimulatingStage1 ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <ShieldCheck className="w-3.5 h-3.5 text-blue-600" />
                )}
                <span>Simulate Manager (FID 15)</span>
              </button>
            </div>
          </div>
        )}

        {/* =========================================================================
            STAGE 2: SOFTWARE LOGIN CARD
            Active once Stage 1 issues a valid challenge ticket
            ========================================================= */}
        {isStage1Complete && authMode === 'login' && (
          <div className="space-y-4">
            {/* Stage 1 Verified Identity Banner */}
            <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 space-y-2 shadow-xs">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  <span className="text-xs font-bold font-sans">
                    Stage 1 Verified: RFID Card 10 5B 96 5C
                  </span>
                </div>
                <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-emerald-100/80 border border-emerald-300 font-mono text-[11px] font-bold text-emerald-800">
                  <Clock className="w-3.5 h-3.5 text-emerald-700" />
                  <span>{formatCountdown(ticketSecondsLeft)}</span>
                </div>
              </div>

              <div className="flex items-center justify-between text-[11px] text-emerald-700 font-mono pt-1 border-t border-emerald-200/60">
                <span className="truncate max-w-[220px]">Ticket: {stage1Ticket.ticket_id}</span>
                <button
                  type="button"
                  onClick={() => clearStage1Ticket()}
                  className="text-red-600 hover:text-red-800 hover:underline font-sans text-[11px] cursor-pointer"
                >
                  Rescan Hardware
                </button>
              </div>
            </div>

            {/* Quick Account Switcher for RFID 10 5B 96 5C */}
            <div className="space-y-1.5">
              <span className="text-[11px] font-bold text-slate-700 uppercase tracking-wider">
                Select Authorized Account for Card 10 5B 96 5C:
              </span>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setEmail("admin@forensics.gov");
                    setPassword("password123");
                  }}
                  className={`p-2.5 rounded-xl border text-left transition-all cursor-pointer ${
                    email.toLowerCase() === "admin@forensics.gov"
                      ? "bg-blue-50 border-blue-400 text-blue-900 ring-2 ring-blue-500/20 shadow-xs"
                      : "bg-white border-slate-200 text-slate-700 hover:bg-slate-50"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-bold">Admin</span>
                    <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-amber-100 text-amber-800">
                      Command Center
                    </span>
                  </div>
                  <div className="text-[10px] font-mono text-slate-500 truncate">admin@forensics.gov</div>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setEmail("manager@forensics.gov");
                    setPassword("password123");
                  }}
                  className={`p-2.5 rounded-xl border text-left transition-all cursor-pointer ${
                    email.toLowerCase() === "manager@forensics.gov"
                      ? "bg-purple-50 border-purple-400 text-purple-900 ring-2 ring-purple-500/20 shadow-xs"
                      : "bg-white border-slate-200 text-slate-700 hover:bg-slate-50"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-bold">Portal Manager</span>
                    <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-purple-100 text-purple-800">
                      User Dashboard
                    </span>
                  </div>
                  <div className="text-[10px] font-mono text-slate-500 truncate">manager@forensics.gov</div>
                </button>
              </div>
            </div>

            {/* Software Passphrase Form */}
            <form onSubmit={handleCredentialsSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1.5 font-sans">
                  Investigator User ID / Email
                </label>
                <input
                  type="text"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="admin@forensics.gov or manager@forensics.gov"
                  className="ws-input w-full font-mono text-xs"
                  autoCapitalize="none"
                  autoCorrect="off"
                  autoComplete="username"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1.5 font-sans">
                  Investigator Access Passphrase
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter password (e.g. password123)"
                    className="ws-input w-full pr-10 text-xs font-mono"
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

              {/* Quick Fill Credentials button */}
              <div className="flex items-center justify-between text-[11px] text-slate-500 pt-0.5">
                <span>Default Passphrase:</span>
                <button
                  type="button"
                  onClick={() => setPassword('password123')}
                  className="text-amber-700 font-semibold hover:underline"
                >
                  Use Default (password123)
                </button>
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full ws-btn ws-btn-primary py-2.5 text-xs flex items-center justify-center gap-2 mt-2 disabled:opacity-50 cursor-pointer shadow-xs"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Consuming Hardware Ticket & Authenticating...</span>
                  </>
                ) : (
                  <>
                    <Unlock className="w-4 h-4 text-emerald-400" />
                    <span>Complete Software Login & Enter Workstation</span>
                  </>
                )}
              </button>
            </form>
          </div>
        )}

        {/* Tab Switcher: Sign In / Register Account */}
        <div className="flex rounded-xl bg-slate-100 p-1 border border-slate-200 text-xs font-semibold">
          <button
            type="button"
            onClick={() => { setAuthMode('login'); setError(null); }}
            className={`flex-1 py-1.5 rounded-lg transition-all cursor-pointer ${
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
            className={`flex-1 py-1.5 rounded-lg transition-all cursor-pointer ${
              authMode === 'signup'
                ? 'bg-white text-slate-900 shadow-xs border border-slate-200 font-bold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Register Account
          </button>
        </div>

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
              className="w-full ws-btn ws-btn-amber py-2.5 text-xs flex items-center justify-center gap-2 mt-2 cursor-pointer"
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

        {/* Cloud Backend Connection Settings */}
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
              className="text-[10px] text-blue-600 hover:underline font-mono cursor-pointer"
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
            className="text-blue-600 hover:text-blue-800 hover:underline font-semibold text-xs cursor-pointer"
          >
            Switch to {simulationMode ? "Hardware-Only" : "Simulation"} Mode
          </button>
        </div>
      </div>
    </div>
  );
};

export default Login;
