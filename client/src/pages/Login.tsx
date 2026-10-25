import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { 
  AlertTriangle, 
  Eye, 
  EyeOff, 
  Loader2, 
  ShieldCheck,
  ArrowLeft,
  UserCheck,
  CheckCircle2,
  Clock,
  LogIn
} from 'lucide-react';
import { getApiBaseUrl } from '../services/api';

export const Login: React.FC = () => {
  const navigate = useNavigate();
  const { 
    user,
    login, 
    register,
    isAuthenticated,
    stage1Ticket,
    clearStage1Ticket
  } = useAuth();

  // If already authenticated, redirect to portal-manager for admin or dashboard for caseworkers
  useEffect(() => {
    if (isAuthenticated || (typeof window !== 'undefined' && localStorage.getItem('forensic_token'))) {
      const isAdmin = user?.role === 'admin';
      window.location.href = isAdmin ? '/portal-manager' : '/dashboard';
    }
  }, [isAuthenticated, user?.role]);

  const [authMode, setAuthMode] = useState<'login' | 'signup'>('login');

  // Countdown timer if hardware token is present
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
      }
    };

    updateTimer();
    const interval = setInterval(updateTimer, 1000);
    return () => clearInterval(interval);
  }, [stage1Ticket, clearStage1Ticket]);

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

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Handle Software Login Credentials Submission
  const handleCredentialsSubmit = async (e?: React.FormEvent, overrideEmail?: string, overridePassword?: string) => {
    if (e) e.preventDefault();
    const cleanId = (overrideEmail !== undefined ? overrideEmail : email).trim();
    const cleanPass = overridePassword !== undefined ? overridePassword : password;
    if (!cleanId || !cleanPass) return;
    
    setIsSubmitting(true);
    setError(null);
    try {
      const loggedUser = await login(cleanId, cleanPass, stage1Ticket?.ticket_id);
      if (loggedUser?.role === 'admin') {
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
        setError('Incorrect password or invalid credentials. Please verify your credentials.');
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
        <span className="text-[10px] sm:text-[11px] text-slate-400 font-mono">ISO/IEC 27037 Standard</span>
      </div>

      {/* Main Container */}
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

        {/* Global Error Banner */}
        {error && (
          <div className="p-3.5 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs flex items-start gap-2.5 shadow-xs">
            <AlertTriangle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
            <span className="leading-relaxed font-sans">{error}</span>
          </div>
        )}

        {/* Optional Active Hardware Token Banner (if scanned) */}
        {stage1Ticket && (
          <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs flex items-center justify-between shadow-xs">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              <div>
                <span className="font-bold">Hardware Authentication Verified</span>
                <div className="text-[10px] text-emerald-700 font-mono">
                  {stage1Ticket.user_email || stage1Ticket.user_name}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1 px-2 py-0.5 rounded bg-emerald-100/80 border border-emerald-300 font-mono text-[11px] font-bold text-emerald-800">
                <Clock className="w-3 h-3 text-emerald-700" />
                <span>{formatCountdown(ticketSecondsLeft)}</span>
              </div>
              <button
                type="button"
                onClick={() => clearStage1Ticket()}
                className="text-red-600 hover:text-red-800 text-[10px] font-medium hover:underline cursor-pointer"
              >
                Clear
              </button>
            </div>
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

        {/* TAB 1: LOGIN FORM */}
        {authMode === 'login' && (
          <div className="space-y-4">
            {/* Quick Role Preset Selectors */}
            <div className="space-y-1.5">
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                Select Account Role:
              </span>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setEmail("admin@forensics.gov")}
                  className={`p-2.5 rounded-xl border text-left transition-all cursor-pointer ${
                    email.toLowerCase() === "admin@forensics.gov"
                      ? "bg-blue-50 border-blue-400 text-blue-900 ring-2 ring-blue-500/20 shadow-xs"
                      : "bg-white border-slate-200 text-slate-700 hover:bg-slate-50"
                  }`}
                >
                  <div className="flex items-center justify-between mb-0.5">
                    <span className="text-xs font-bold">Admin Portal</span>
                    <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-blue-100 text-blue-800 font-semibold">
                      Management
                    </span>
                  </div>
                  <div className="text-[10px] font-mono text-slate-500 truncate">admin@forensics.gov</div>
                </button>

                <button
                  type="button"
                  onClick={() => setEmail("chief@forensics.gov")}
                  className={`p-2.5 rounded-xl border text-left transition-all cursor-pointer ${
                    email.toLowerCase() === "chief@forensics.gov"
                      ? "bg-purple-50 border-purple-400 text-purple-900 ring-2 ring-purple-500/20 shadow-xs"
                      : "bg-white border-slate-200 text-slate-700 hover:bg-slate-50"
                  }`}
                >
                  <div className="flex items-center justify-between mb-0.5">
                    <span className="text-xs font-bold">Chief Investigator</span>
                    <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-purple-100 text-purple-800 font-semibold">
                      Forensic Cases
                    </span>
                  </div>
                  <div className="text-[10px] font-mono text-slate-500 truncate">chief@forensics.gov</div>
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
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="admin@forensics.gov or chief@forensics.gov"
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
                    placeholder="Enter access passphrase"
                    className="ws-input w-full pr-10 text-xs font-mono"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full ws-btn ws-btn-primary py-2.5 text-xs flex items-center justify-center gap-2 mt-2 disabled:opacity-50 cursor-pointer shadow-xs"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Authenticating Credentials...</span>
                  </>
                ) : (
                  <>
                    <LogIn className="w-4 h-4 text-emerald-400" />
                    <span>Sign In to Forensic Workstation</span>
                  </>
                )}
              </button>
            </form>
          </div>
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

        {/* Footer info */}
        <div className="pt-3 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500">
          <span className="text-[11px]">System v2.4 (Court-Admissible)</span>
          <span className="text-[11px] text-slate-400 font-mono">Forensic Chain of Custody</span>
        </div>
      </div>
    </div>
  );
};

export default Login;
