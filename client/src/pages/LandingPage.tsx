import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  User,
  Lock,
  ArrowRight,
  ShieldCheck,
  Link2,
  Users,
  BarChart3,
  Folder,
  Calendar,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  Clock,
  Share2,
  Database,
  FileText,
  Shield,
  Activity,
  Cpu,
  ChevronRight,
  ExternalLink,
  Menu,
  X
} from 'lucide-react';

export const LandingPage: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const [activeTab, setActiveTab] = useState<string>('');
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  return (
    <div className="min-h-screen bg-[#faf8f5] text-slate-900 font-sans selection:bg-amber-100 selection:text-amber-900 relative pt-16 sm:pt-18">
      
      {/* =========================================================================
          PERFECTLY FIXED STICKY TOP NAVIGATION (Matching Application HorizontalNavbar)
          ========================================================================= */}
      <header className="fixed top-0 left-0 right-0 z-50 select-none border-b transition-colors duration-200 bg-white/95 backdrop-blur-md border-slate-200 text-slate-900 shadow-xs">
        <div className="w-full max-w-[1720px] mx-auto px-4 sm:px-8 lg:px-12">
          <div className="flex items-center justify-between h-16 sm:h-18 gap-4 sm:gap-6">
            
            {/* Left: Brand Identity matching application HorizontalNavbar */}
            <div className="flex items-center gap-3.5 shrink-0">
              <Link to="/" className="flex items-center gap-3 group">
                <img
                  src="/cryptevid_logo.png"
                  alt="CRYPTEVID"
                  className="h-10 sm:h-12 w-auto object-contain rounded-lg shadow-xs transition-transform group-hover:scale-105"
                />
                <div className="flex flex-col">
                  <span className="text-sm sm:text-base font-extrabold tracking-wider uppercase font-sans text-slate-900 group-hover:text-amber-600 transition-colors">
                    CRYPTEVID
                  </span>
                  <span className="text-[10px] sm:text-[11px] text-slate-500 font-sans tracking-tight leading-none">
                    Forensic Intelligence Platform
                  </span>
                </div>
              </Link>
            </div>

            {/* Center: Desktop Navigation - Styled identical to application navbar */}
            <nav className="hidden md:flex items-center gap-1.5 py-1">
              {[
                { id: 'capabilities', label: 'Capabilities', href: '#capabilities' },
                { id: 'security', label: 'Security', href: '#security' },
                { id: 'about', label: 'About', href: '#about' }
              ].map((item) => {
                const isActive = activeTab === item.id;
                return (
                  <a
                    key={item.id}
                    href={item.href}
                    onClick={() => setActiveTab(item.id as any)}
                    className={`ws-nav-link ${isActive ? 'ws-nav-link-active' : ''}`}
                    style={
                      isActive
                        ? {
                            backgroundColor: '#1E3A8A',
                            color: '#FFFFFF',
                            fontWeight: 800
                          }
                        : undefined
                    }
                  >
                    {item.label}
                  </a>
                );
              })}
            </nav>

            {/* Right: Forensic Engine Status & Single Access Portal Button (No Man Icon) */}
            <div className="flex items-center gap-2.5 sm:gap-4 shrink-0">
              {/* Live Platform Security Status Badge (matching application navbar) */}
              <div className="hidden lg:flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-[10px] font-mono font-bold text-emerald-700">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                <span>FORENSIC ENGINE ONLINE</span>
              </div>

              {/* Main Access Portal Action */}
              <Link
                to={isAuthenticated ? "/dashboard" : "/login"}
                className="px-3.5 sm:px-4 py-2 rounded-lg bg-[#0f2744] hover:bg-[#0b1d33] text-white text-xs font-bold flex items-center gap-2 shadow-xs transition active:scale-98"
              >
                <Lock className="w-3.5 h-3.5 text-amber-300" />
                <span>{isAuthenticated ? "Enter Workstation" : "Access Portal"}</span>
                <ArrowRight className="w-3.5 h-3.5 text-white/90" />
              </Link>

              {/* Mobile Hamburger Button */}
              <button
                onClick={() => setMobileNavOpen(!mobileNavOpen)}
                className="md:hidden w-8 h-8 rounded-lg border border-slate-200 flex items-center justify-center text-slate-700 bg-slate-50 hover:bg-slate-100 transition"
                aria-label="Toggle navigation menu"
              >
                {mobileNavOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
              </button>
            </div>
          </div>
        </div>

        {/* Mobile Navigation Drawer */}
        {mobileNavOpen && (
          <div className="md:hidden border-t border-slate-200 bg-white px-4 py-3 space-y-2 shadow-lg animate-fade-in-up">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <span className="text-xs font-bold text-slate-700 font-mono">FORENSIC NAVIGATION</span>
              <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 font-mono text-[9px] font-bold">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                <span>ONLINE</span>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-1.5 text-xs font-bold text-slate-800">
              {[
                { id: 'capabilities', label: 'Capabilities', href: '#capabilities' },
                { id: 'security', label: 'Security', href: '#security' },
                { id: 'about', label: 'About', href: '#about' }
              ].map((item) => (
                <a
                  key={item.id}
                  href={item.href}
                  onClick={() => { setActiveTab(item.id as any); setMobileNavOpen(false); }}
                  className={`p-2.5 rounded-lg text-center transition ${
                    activeTab === item.id
                      ? 'bg-[#1E3A8A] text-white font-extrabold'
                      : 'bg-slate-50 hover:bg-amber-50 text-slate-800'
                  }`}
                >
                  {item.label}
                </a>
              ))}
            </div>
          </div>
        )}
      </header>


      {/* =========================================================================
          HERO SECTION (Warm sand background with watermark & workstation preview)
          ========================================================================= */}
      <section className="relative pt-8 sm:pt-12 pb-16 lg:pb-20 overflow-hidden bg-gradient-to-br from-[#faf8f5] via-[#f7f4ed] to-[#eee8da]">
        
        {/* Subtle Ashoka Emblem / Sacred Seal Watermark in top-right background */}
        <div className="absolute right-6 top-8 w-[580px] h-[580px] pointer-events-none opacity-[0.065] select-none">
          <svg viewBox="0 0 200 200" className="w-full h-full text-amber-900 fill-current">
            <circle cx="100" cy="100" r="95" stroke="currentColor" strokeWidth="2" fill="none" />
            <circle cx="100" cy="100" r="85" stroke="currentColor" strokeWidth="1.5" strokeDasharray="4 4" fill="none" />
            <circle cx="100" cy="100" r="25" stroke="currentColor" strokeWidth="3" fill="none" />
            {Array.from({ length: 24 }).map((_, i) => (
              <line
                key={i}
                x1="100"
                y1="100"
                x2={100 + 75 * Math.cos((i * 15 * Math.PI) / 180)}
                y2={100 + 75 * Math.sin((i * 15 * Math.PI) / 180)}
                stroke="currentColor"
                strokeWidth="1.5"
              />
            ))}
          </svg>
        </div>

        {/* Ambient Soft Gold Radial Glow */}
        <div className="absolute top-1/4 left-1/3 w-[600px] h-[600px] bg-amber-200/25 blur-[140px] rounded-full pointer-events-none" />

        <div className="max-w-[1720px] mx-auto px-4 sm:px-6 lg:px-10 relative z-10">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 xl:gap-12 items-center">

            {/* -------------------------------------------------------------------
                LEFT COLUMN: Hero Headlines & Core Trust Badges
                ------------------------------------------------------------------- */}
            <div className="lg:col-span-5 xl:col-span-5 space-y-6">
              
              {/* Eyebrow Label */}
              <div className="flex items-center gap-2.5">
                <span className="w-6 h-0.5 bg-[#b45309] inline-block rounded-full"></span>
                <span className="text-[11px] sm:text-xs font-bold tracking-[0.2em] uppercase text-[#b45309] font-mono">
                  SECURE DIGITAL FORENSICS
                </span>
              </div>

              {/* Main Headline */}
              <h1 className="text-3xl sm:text-5xl xl:text-6xl font-black tracking-tight leading-[1.1] font-sans">
                <span className="block text-slate-950">Preserve Evidence.</span>
                <span className="block text-[#b45309] mt-0.5">Reveal the Truth.</span>
              </h1>

              {/* Description Paragraph */}
              <p className="text-sm sm:text-base text-slate-600 leading-relaxed font-sans max-w-lg">
                A unified platform for secure evidence collection, integrity verification, chain of custody and AI-assisted forensic intelligence, enabling trusted investigator workflows.
              </p>

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 pt-2">
                <Link
                  to={isAuthenticated ? "/dashboard" : "/login"}
                  className="px-6 py-3.5 rounded-lg bg-[#0f2744] hover:bg-[#0b1d33] text-white font-bold text-xs sm:text-sm flex items-center justify-center gap-2.5 shadow-md hover:shadow-lg transition active:scale-98"
                >
                  <Lock className="w-4 h-4 text-amber-300 shrink-0" />
                  <span>Enter Forensic Platform</span>
                  <ArrowRight className="w-4 h-4 text-white shrink-0" />
                </Link>

                <a
                  href="#capabilities"
                  className="px-5 py-3.5 rounded-lg bg-white border border-amber-300 text-[#92400e] font-bold text-xs sm:text-sm flex items-center justify-center gap-2 shadow-2xs hover:bg-amber-50/60 transition active:scale-98"
                >
                  <BarChart3 className="w-4 h-4 text-[#b45309] shrink-0" />
                  <span>Explore Capabilities</span>
                </a>
              </div>

              {/* Three Trust Pillars (Responsive Grid on Mobile) */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 sm:gap-3 pt-4 border-t border-slate-300/60 max-w-lg">
                
                {/* Pillar 1 */}
                <div className="flex items-center sm:flex-col sm:items-start gap-3 sm:gap-1 p-2 sm:p-0 rounded-lg bg-white/40 sm:bg-transparent border sm:border-0 border-slate-200/50">
                  <div className="w-7 h-7 rounded-md flex items-center justify-center text-[#b45309] shrink-0">
                    <ShieldCheck className="w-5 sm:w-6 h-5 sm:h-6 stroke-[1.8]" />
                  </div>
                  <div>
                    <div className="text-xs font-bold text-slate-900 leading-tight">
                      SHA-256 Integrity
                    </div>
                    <div className="text-[10px] text-slate-500 leading-tight mt-0.5">
                      Cryptographic verification
                    </div>
                  </div>
                </div>

                {/* Pillar 2 */}
                <div className="flex items-center sm:flex-col sm:items-start gap-3 sm:gap-1 p-2 sm:p-0 rounded-lg bg-white/40 sm:bg-transparent border sm:border-0 border-slate-200/50">
                  <div className="w-7 h-7 rounded-md flex items-center justify-center text-[#b45309] shrink-0">
                    <Link2 className="w-5 sm:w-6 h-5 sm:h-6 stroke-[1.8]" />
                  </div>
                  <div>
                    <div className="text-xs font-bold text-slate-900 leading-tight">
                      Verified Chain of Custody
                    </div>
                    <div className="text-[10px] text-slate-500 leading-tight mt-0.5">
                      Tamper-proof audit trail
                    </div>
                  </div>
                </div>

                {/* Pillar 3 */}
                <div className="flex items-center sm:flex-col sm:items-start gap-3 sm:gap-1 p-2 sm:p-0 rounded-lg bg-white/40 sm:bg-transparent border sm:border-0 border-slate-200/50">
                  <div className="w-7 h-7 rounded-md flex items-center justify-center text-[#b45309] shrink-0">
                    <Users className="w-5 sm:w-6 h-5 sm:h-6 stroke-[1.8]" />
                  </div>
                  <div>
                    <div className="text-xs font-bold text-slate-900 leading-tight">
                      Role-Based Access
                    </div>
                    <div className="text-[10px] text-slate-500 leading-tight mt-0.5">
                      Secure investigator workflows
                    </div>
                  </div>
                </div>

              </div>

            </div>


            {/* -------------------------------------------------------------------
                RIGHT COLUMN: Interactive Workstation Preview (Pixel-perfect replica)
                ------------------------------------------------------------------- */}
            <div className="lg:col-span-7 xl:col-span-7">
              <div className="relative bg-white rounded-2xl shadow-2xl border border-slate-200/90 p-3.5 sm:p-5 text-slate-900 space-y-3 select-none transition-all duration-300 hover:shadow-3xl">
                
                {/* Mockup Top Header */}
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-2.5">
                  <div className="flex items-center gap-2">
                    <img
                      src="/cryptevid_logo.png"
                      alt="Logo"
                      className="h-6 w-auto object-contain rounded"
                    />
                  </div>

                  <div className="hidden sm:flex items-center gap-1 text-[10px] font-bold">
                    <span className="px-2 py-0.5 text-slate-600 hover:text-slate-900 cursor-pointer">DASHBOARD</span>
                    <span className="px-2 py-0.5 text-slate-600 hover:text-slate-900 cursor-pointer">CASES</span>
                    <span className="px-2.5 py-0.5 bg-[#1e3a8a] text-white rounded font-bold cursor-pointer">THREAT INTEL</span>
                    <span className="px-2 py-0.5 text-slate-600 hover:text-slate-900 cursor-pointer">ALERTS</span>
                    <span className="px-2 py-0.5 text-slate-600 hover:text-slate-900 cursor-pointer">SETTINGS</span>
                  </div>

                  <div className="flex items-center gap-2 flex-wrap">
                    <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 font-mono text-[9px] font-bold">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                      <span>FORENSIC ENGINE ONLINE</span>
                    </div>

                    <div className="flex items-center gap-1.5 bg-amber-50/80 border border-amber-200 px-2 py-0.5 rounded text-[10px]">
                      <span className="font-bold text-slate-800">Chief Investigator</span>
                      <span className="text-[8px] bg-amber-200 text-amber-900 font-bold px-1 rounded">ADMIN</span>
                      <ExternalLink className="w-2.5 h-2.5 text-slate-400" />
                    </div>
                  </div>
                </div>

                {/* Active Case Context Bar */}
                <div className="text-[10px] font-mono text-slate-600 bg-slate-50 border border-slate-200 px-3 py-1.5 rounded flex flex-col sm:flex-row sm:items-center justify-between gap-1 sm:gap-2">
                  <div className="truncate">
                    <span className="font-bold text-slate-700">ACTIVE CASE : </span>
                    <span className="text-blue-600 font-bold hover:underline cursor-pointer">DF-2026-000018</span>
                    <span className="text-slate-400"> | </span>
                    <span className="truncate">Operation Citadel - Verification Run</span>
                  </div>
                  <span className="text-[9px] font-bold text-emerald-700 bg-emerald-100/80 px-1.5 py-0.2 rounded border border-emerald-200 self-start sm:self-auto">
                    OPEN
                  </span>
                </div>

                {/* Case Overview Box - Fully Responsive on Mobile */}
                <div className="p-3 sm:p-3.5 rounded-xl border border-slate-200 bg-white shadow-2xs space-y-3">
                  <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3.5">
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <Folder className="w-3.5 h-3.5 text-amber-600" />
                        <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider font-mono">CASE OVERVIEW</span>
                      </div>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-sm font-bold text-slate-900 font-mono">DF-2026-000007</span>
                        <span className="text-[9px] bg-red-100 text-red-700 font-bold px-1.5 py-0.2 rounded border border-red-200 font-mono">
                          CRITICAL
                        </span>
                      </div>
                      <div className="text-xs font-semibold text-slate-800">Operation Citadel - Verification Run</div>
                      <div className="text-[10px] text-slate-500">Cryptographic posture & threat vectors analysis</div>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-[10px] text-slate-600 pt-2 lg:pt-0 border-t lg:border-t-0 border-slate-100">
                      <div>
                        <div className="text-[9px] text-slate-400 uppercase font-mono font-bold">CASE STATUS</div>
                        <div className="flex items-center gap-1 font-bold text-slate-800">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                          <span>OPEN</span>
                        </div>
                        <div className="text-[9px] text-slate-400">Active Investigation</div>
                      </div>

                      <div>
                        <div className="text-[9px] text-slate-400 uppercase font-mono font-bold">CREATED ON</div>
                        <div className="flex items-center gap-1 font-semibold text-slate-800 font-mono">
                          <Calendar className="w-3 h-3 text-slate-400" />
                          <span>07 Oct 2026</span>
                        </div>
                        <div className="text-[9px] text-slate-400 font-mono">18:10:51</div>
                      </div>

                      <div className="col-span-2 sm:col-span-1">
                        <div className="text-[9px] text-slate-400 uppercase font-mono font-bold">INVESTIGATOR</div>
                        <div className="flex items-center gap-1 font-semibold text-slate-800">
                          <User className="w-3 h-3 text-slate-400" />
                          <span>Chief Investigator</span>
                        </div>
                        <div className="text-[9px] text-amber-700 font-bold font-mono">ADMIN</div>
                      </div>
                    </div>

                    <Link
                      to="/login"
                      className="w-full lg:w-auto justify-center px-3.5 py-2 bg-[#c2410c] hover:bg-[#9a3412] text-white text-[11px] font-bold rounded-lg shadow-xs flex items-center gap-1.5 shrink-0 transition active:scale-98"
                    >
                      <span>View Case Details</span>
                      <ArrowRight className="w-3 h-3" />
                    </Link>
                  </div>
                </div>

                {/* Middle Row (Risk Posture, Evidence Integrity, Timeline) */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
                  
                  {/* Card 1: Case Risk Posture with Gauge */}
                  <div className="p-3 rounded-xl border border-slate-200 bg-white shadow-2xs space-y-1.5">
                    <div className="flex items-center gap-1.5 text-[10px] font-bold text-slate-700 uppercase font-mono">
                      <Shield className="w-3 h-3 text-amber-600" />
                      <span>CASE RISK POSTURE</span>
                    </div>

                    <div className="flex items-center justify-between pt-1">
                      {/* Doughnut Gauge Ring */}
                      <div className="relative w-16 h-16 shrink-0 flex items-center justify-center">
                        <svg className="w-full h-full -rotate-90" viewBox="0 0 36 36">
                          <path
                            className="text-slate-100"
                            strokeWidth="3.8"
                            stroke="currentColor"
                            fill="none"
                            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                          />
                          <path
                            className="text-emerald-500"
                            strokeDasharray="24, 100"
                            strokeWidth="3.8"
                            strokeLinecap="round"
                            stroke="currentColor"
                            fill="none"
                            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                          />
                        </svg>
                        <div className="absolute text-center">
                          <span className="text-base font-black text-slate-900 block leading-none font-mono">24</span>
                          <span className="text-[8px] text-slate-400 block font-mono">/ 100</span>
                        </div>
                      </div>

                      {/* Legend List */}
                      <div className="text-[10px] font-mono space-y-0.5">
                        <div className="flex items-center gap-1.5">
                          <span className="w-1.5 h-1.5 rounded-full bg-red-500" />
                          <span className="text-slate-600">Critical</span>
                          <span className="font-bold text-slate-900 ml-auto">0</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                          <span className="text-slate-600">High</span>
                          <span className="font-bold text-slate-900 ml-auto">1</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                          <span className="text-slate-600">Medium</span>
                          <span className="font-bold text-slate-900 ml-auto">2</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                          <span className="text-slate-600">Low</span>
                          <span className="font-bold text-slate-900 ml-auto">3</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Card 2: Evidence Integrity */}
                  <div className="p-3 rounded-xl border border-slate-200 bg-white shadow-2xs space-y-2 flex flex-col justify-between">
                    <div className="flex items-center gap-1.5 text-[10px] font-bold text-slate-700 uppercase font-mono">
                      <FileText className="w-3 h-3 text-amber-600" />
                      <span>EVIDENCE INTEGRITY</span>
                    </div>

                    <div className="p-2.5 rounded-lg bg-emerald-50 border border-emerald-200 text-center space-y-0.5">
                      <div className="inline-flex items-center gap-1 text-emerald-800 font-bold text-xs">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                        <span>VERIFIED</span>
                      </div>
                      <div className="text-[10px] font-semibold text-slate-800">All evidence hashes match</div>
                      <div className="text-[9px] text-slate-500 font-mono">SHA-256 integrity confirmed</div>
                    </div>
                  </div>

                  {/* Card 3: Recent Timeline Events */}
                  <div className="p-3 rounded-xl border border-slate-200 bg-white shadow-2xs space-y-1.5">
                    <div className="flex items-center justify-between text-[10px] font-bold font-mono">
                      <div className="flex items-center gap-1.5 text-slate-700 uppercase">
                        <Clock className="w-3 h-3 text-amber-600" />
                        <span>RECENT TIMELINE EVENTS</span>
                      </div>
                      <span className="text-blue-600 text-[9px] hover:underline cursor-pointer">View All →</span>
                    </div>

                    <div className="space-y-1 text-[9px] font-mono text-slate-600">
                      <div className="flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-blue-500 shrink-0" />
                        <span className="text-slate-400">18:10:51</span>
                        <span className="truncate">Evidence verification completed</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-amber-500 shrink-0" />
                        <span className="text-slate-400">18:07:22</span>
                        <span className="truncate">Hash mismatch detected (Working copy)</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-blue-500 shrink-0" />
                        <span className="text-slate-400">18:05:14</span>
                        <span className="truncate">Evidence item added to vault</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-blue-500 shrink-0" />
                        <span className="text-slate-400">18:02:33</span>
                        <span className="truncate">Chain of custody updated</span>
                      </div>
                    </div>
                  </div>

                </div>

                {/* Bottom Row (Threat Intel Graph + Key Findings) */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                  
                  {/* Card 4: Threat Intelligence Graph */}
                  <div className="p-3 rounded-xl border border-slate-200 bg-white shadow-2xs space-y-1.5">
                    <div className="flex items-center justify-between text-[10px] font-bold font-mono">
                      <div className="flex items-center gap-1.5 text-slate-700 uppercase">
                        <Share2 className="w-3 h-3 text-amber-600" />
                        <span>THREAT INTELLIGENCE GRAPH</span>
                      </div>
                      <span className="text-blue-600 text-[9px] hover:underline cursor-pointer">View Full Graph →</span>
                    </div>

                    {/* Miniature Topological Relational Graph Visual */}
                    <div className="relative h-28 w-full bg-slate-50/70 rounded-lg border border-slate-200/60 overflow-hidden flex items-center justify-center">
                      <svg className="w-full h-full" viewBox="0 0 300 110">
                        {/* Connecting dotted lines */}
                        <line x1="150" y1="55" x2="60" y2="25" stroke="#cbd5e1" strokeWidth="1" strokeDasharray="3 3" />
                        <line x1="150" y1="55" x2="240" y2="25" stroke="#cbd5e1" strokeWidth="1" strokeDasharray="3 3" />
                        <line x1="150" y1="55" x2="40" y2="85" stroke="#cbd5e1" strokeWidth="1" strokeDasharray="3 3" />
                        <line x1="150" y1="55" x2="260" y2="85" stroke="#cbd5e1" strokeWidth="1" strokeDasharray="3 3" />
                        <line x1="150" y1="55" x2="90" y2="95" stroke="#cbd5e1" strokeWidth="1" strokeDasharray="3 3" />
                        <line x1="150" y1="55" x2="210" y2="95" stroke="#cbd5e1" strokeWidth="1" strokeDasharray="3 3" />

                        {/* Central Hub Node */}
                        <circle cx="150" cy="55" r="14" fill="#fee2e2" stroke="#ef4444" strokeWidth="2" />
                        <circle cx="150" cy="55" r="6" fill="#dc2626" />
                        <text x="150" y="78" textAnchor="middle" fontSize="7" fontWeight="bold" fill="#dc2626" fontFamily="monospace">
                          DF-2026-000007
                        </text>

                        {/* Satellite Nodes */}
                        {/* Node 1: Malware Artifact */}
                        <circle cx="60" cy="25" r="5" fill="#f87171" />
                        <text x="60" y="38" textAnchor="middle" fontSize="6" fill="#64748b" fontFamily="sans-serif">Malware Artifact</text>

                        {/* Node 2: Suspicious Domain */}
                        <circle cx="240" cy="25" r="5" fill="#fb923c" />
                        <text x="240" y="38" textAnchor="middle" fontSize="6" fill="#64748b" fontFamily="sans-serif">Suspicious Domain</text>

                        {/* Node 3: User Activity */}
                        <circle cx="40" cy="85" r="4.5" fill="#60a5fa" />
                        <text x="40" y="98" textAnchor="middle" fontSize="6" fill="#64748b" fontFamily="sans-serif">User Activity</text>

                        {/* Node 4: External IP */}
                        <circle cx="260" cy="85" r="4.5" fill="#38bdf8" />
                        <text x="260" y="98" textAnchor="middle" fontSize="6" fill="#64748b" fontFamily="sans-serif">External IP</text>

                        {/* Node 5: File Hash */}
                        <circle cx="90" cy="95" r="4" fill="#34d399" />
                        <text x="90" y="106" textAnchor="middle" fontSize="5.5" fill="#64748b" fontFamily="sans-serif">File Hash</text>

                        {/* Node 6: Registry Key */}
                        <circle cx="210" cy="95" r="4" fill="#fbbf24" />
                        <text x="210" y="106" textAnchor="middle" fontSize="5.5" fill="#64748b" fontFamily="sans-serif">Registry Key</text>
                      </svg>
                    </div>
                  </div>

                  {/* Card 5: Key Findings */}
                  <div className="p-3 rounded-xl border border-slate-200 bg-white shadow-2xs space-y-1.5 flex flex-col justify-between">
                    <div className="flex items-center gap-1.5 text-[10px] font-bold text-slate-700 uppercase font-mono">
                      <FileText className="w-3 h-3 text-amber-600" />
                      <span>KEY FINDINGS</span>
                    </div>

                    <div className="space-y-1.5 text-[9px]">
                      {/* Finding 1 */}
                      <div className="p-1.5 rounded-lg bg-red-50/70 border border-red-200 flex items-start gap-2">
                        <AlertTriangle className="w-3 h-3 text-red-600 shrink-0 mt-0.5" />
                        <div>
                          <div className="font-bold text-red-950 flex items-center justify-between">
                            <span>Tampered Evidence Exhibits</span>
                            <span className="text-[8px] bg-red-200 text-red-800 px-1 rounded">1 exhibits</span>
                          </div>
                          <div className="text-red-700/90 text-[8px] font-mono">+35 risk points per hash mismatch</div>
                        </div>
                      </div>

                      {/* Finding 2 */}
                      <div className="p-1.5 rounded-lg bg-amber-50/70 border border-amber-200 flex items-start gap-2">
                        <AlertTriangle className="w-3 h-3 text-amber-600 shrink-0 mt-0.5" />
                        <div>
                          <div className="font-bold text-amber-950 flex items-center justify-between">
                            <span>Critical Severity Events</span>
                            <span className="text-[8px] bg-amber-200 text-amber-800 px-1 rounded">1 events</span>
                          </div>
                          <div className="text-amber-800/90 text-[8px] font-mono">+15 risk points per unauthorized access</div>
                        </div>
                      </div>

                      {/* Finding 3 */}
                      <div className="p-1.5 rounded-lg bg-blue-50/70 border border-blue-200 flex items-start gap-2">
                        <AlertCircle className="w-3 h-3 text-blue-600 shrink-0 mt-0.5" />
                        <div>
                          <div className="font-bold text-blue-950 flex items-center justify-between">
                            <span>Chain of Custody Breaks</span>
                            <span className="text-[8px] bg-blue-200 text-blue-800 px-1 rounded">1 anomalies</span>
                          </div>
                          <div className="text-blue-800/90 text-[8px] font-mono">Ledger continuity verification required</div>
                        </div>
                      </div>
                    </div>
                  </div>

                </div>

              </div>
            </div>

          </div>
        </div>

        {/* =======================================================================
            BOTTOM HORIZONTAL FEATURE STRIP (Exact matching reference image)
            ======================================================================= */}
        <div className="max-w-[1720px] mx-auto px-4 sm:px-6 lg:px-10 mt-10 relative z-20">
          <div className="bg-white rounded-2xl border border-slate-200/90 shadow-xl p-5 sm:p-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 items-center">
            
            {/* Feature Item 1: Evidence Integrity */}
            <div className="flex items-center gap-3.5">
              <div className="w-11 h-11 rounded-xl bg-amber-50 border border-amber-200/80 flex items-center justify-center text-[#b45309] shrink-0 shadow-2xs">
                <FileText className="w-6 h-6 stroke-[1.8]" />
              </div>
              <div>
                <div className="text-sm font-extrabold text-slate-900 leading-tight">
                  Evidence Integrity
                </div>
                <div className="text-xs text-slate-500 leading-tight mt-0.5">
                  Cryptographic verification & tamper detection
                </div>
              </div>
            </div>

            {/* Feature Item 2: Forensic Timeline */}
            <div className="flex items-center gap-3.5 sm:border-l sm:border-slate-200 sm:pl-6">
              <div className="w-11 h-11 rounded-xl bg-amber-50 border border-amber-200/80 flex items-center justify-center text-[#b45309] shrink-0 shadow-2xs">
                <Clock className="w-6 h-6 stroke-[1.8]" />
              </div>
              <div>
                <div className="text-sm font-extrabold text-slate-900 leading-tight">
                  Forensic Timeline
                </div>
                <div className="text-xs text-slate-500 leading-tight mt-0.5">
                  Automated reconstruction & event correlation
                </div>
              </div>
            </div>

            {/* Feature Item 3: Threat Intelligence */}
            <div className="flex items-center gap-3.5 lg:border-l lg:border-slate-200 lg:pl-6">
              <div className="w-11 h-11 rounded-xl bg-amber-50 border border-amber-200/80 flex items-center justify-center text-[#b45309] shrink-0 shadow-2xs">
                <Share2 className="w-6 h-6 stroke-[1.8]" />
              </div>
              <div>
                <div className="text-sm font-extrabold text-slate-900 leading-tight">
                  Threat Intelligence
                </div>
                <div className="text-xs text-slate-500 leading-tight mt-0.5">
                  AI-assisted analysis & risk assessment
                </div>
              </div>
            </div>

            {/* Feature Item 4: Secure Evidence Vault */}
            <div className="flex items-center gap-3.5 sm:border-l sm:border-slate-200 sm:pl-6">
              <div className="w-11 h-11 rounded-xl bg-amber-50 border border-amber-200/80 flex items-center justify-center text-[#b45309] shrink-0 shadow-2xs">
                <Database className="w-6 h-6 stroke-[1.8]" />
              </div>
              <div>
                <div className="text-sm font-extrabold text-slate-900 leading-tight">
                  Secure Evidence Vault
                </div>
                <div className="text-xs text-slate-500 leading-tight mt-0.5">
                  Encrypted storage & controlled access
                </div>
              </div>
            </div>

          </div>
        </div>

      </section>


      {/* =========================================================================
          SECTION 2: INSTITUTIONAL CAPABILITIES & ARCHITECTURE (#capabilities)
          ========================================================================= */}
      <section id="capabilities" className="py-20 bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          
          <div className="text-center max-w-3xl mx-auto mb-16 space-y-3">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-50 border border-amber-200 text-amber-900 text-xs font-semibold">
              <Cpu className="w-3.5 h-3.5 text-amber-700" />
              <span>Court-Admissible Evidence Architecture</span>
            </div>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
              Enterprise Forensic Capabilities
            </h2>
            <p className="text-sm text-slate-600 leading-relaxed">
              Designed from first principles to meet the evidentiary standards of legal discovery, ISO/IEC 27037:2012 protocols, and multi-agency cross-jurisdictional collaboration.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            
            {/* Capability 1 */}
            <div className="p-6 rounded-2xl bg-slate-50/70 border border-slate-200/80 hover:border-amber-300 hover:shadow-lg transition-all duration-300 space-y-3">
              <div className="w-10 h-10 rounded-xl bg-amber-100/70 border border-amber-200 flex items-center justify-center text-amber-700">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold text-slate-900">Cryptographic Bit-Stream Sealing</h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                Automated SHA-256 and MD5 hashing upon ingest. Preserved original forensic backups are physically isolated from working copies to guarantee non-repudiation.
              </p>
            </div>

            {/* Capability 2 */}
            <div className="p-6 rounded-2xl bg-slate-50/70 border border-slate-200/80 hover:border-blue-300 hover:shadow-lg transition-all duration-300 space-y-3">
              <div className="w-10 h-10 rounded-xl bg-blue-100/70 border border-blue-200 flex items-center justify-center text-blue-700">
                <Link2 className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold text-slate-900">Immutable Chain of Custody</h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                Hash-chained custodial handoffs recording examiner identity, source IP, timestamp, action type, and cryptographic digest verification at every transfer.
              </p>
            </div>

            {/* Capability 3 */}
            <div className="p-6 rounded-2xl bg-slate-50/70 border border-slate-200/80 hover:border-emerald-300 hover:shadow-lg transition-all duration-300 space-y-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-100/70 border border-emerald-200 flex items-center justify-center text-emerald-700">
                <Share2 className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold text-slate-900">Relational Topological Graph</h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                Interactive entity correlation connecting suspects, hardware devices, network indicators, malware artifacts, and GPS coordinates into an intuitive graph.
              </p>
            </div>

            {/* Capability 4 */}
            <div className="p-6 rounded-2xl bg-slate-50/70 border border-slate-200/80 hover:border-amber-300 hover:shadow-lg transition-all duration-300 space-y-3">
              <div className="w-10 h-10 rounded-xl bg-amber-100/70 border border-amber-200 flex items-center justify-center text-amber-700">
                <Cpu className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold text-slate-900">Hardware Node Biometrics</h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                Hardware RFID smartcard and optical fingerprint biometric verification via ESP32 ingestion nodes for dual-factor physical custody enforcement.
              </p>
            </div>

            {/* Capability 5 */}
            <div className="p-6 rounded-2xl bg-slate-50/70 border border-slate-200/80 hover:border-purple-300 hover:shadow-lg transition-all duration-300 space-y-3">
              <div className="w-10 h-10 rounded-xl bg-purple-100/70 border border-purple-200 flex items-center justify-center text-purple-700">
                <Activity className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold text-slate-900">Deterministic Threat Scoring</h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                Automated 0-100 threat assessment engine that differentiates verified facts from analytical inferences without black-box hallucination risks.
              </p>
            </div>

            {/* Capability 6 */}
            <div className="p-6 rounded-2xl bg-slate-50/70 border border-slate-200/80 hover:border-red-300 hover:shadow-lg transition-all duration-300 space-y-3">
              <div className="w-10 h-10 rounded-xl bg-red-100/70 border border-red-200 flex items-center justify-center text-red-700">
                <FileText className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold text-slate-900">Official Judicial PDF Export</h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                One-click compilation of certified forensic dossiers sealed with digital timestamps, legal disclosures, and dynamic PDF regeneration for court proceedings.
              </p>
            </div>

          </div>

        </div>
      </section>


      {/* =========================================================================
          SECTION 3: SECURITY & COMPLIANCE (#security)
          ========================================================================= */}
      <section id="security" className="py-16 bg-slate-50 border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          
          <div className="p-8 rounded-2xl bg-white border border-slate-200/90 shadow-sm flex flex-col lg:flex-row items-center justify-between gap-8">
            <div className="space-y-3 max-w-2xl">
              <div className="flex items-center gap-2 text-xs font-bold font-mono text-[#b45309] uppercase">
                <Shield className="w-4 h-4 text-[#b45309]" />
                <span>Forensic Standards & Institutional Security</span>
              </div>
              <h3 className="text-2xl font-black text-slate-900 tracking-tight">
                Strict Adherence to ISO/IEC 27037 Standards
              </h3>
              <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
                Our cryptographic primitives, zero-trust RBAC segregation, and immutable audit logs strictly satisfy international specifications for digital evidence handling, seizure, acquisition, and preservation.
              </p>
              <div className="flex flex-wrap items-center gap-4 pt-2 text-xs font-mono text-slate-600">
                <span className="flex items-center gap-1.5"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> FIPS 180-4 SHA-256 Hashing</span>
                <span className="flex items-center gap-1.5"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> CJIS-Compliant Audit Ledger</span>
                <span className="flex items-center gap-1.5"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> Ephemeral Token Sandboxing</span>
              </div>
            </div>

            <div className="shrink-0">
              <Link
                to={isAuthenticated ? "/dashboard" : "/login"}
                className="px-6 py-3 rounded-xl bg-[#0f2744] hover:bg-[#0b1d33] text-white font-bold text-xs flex items-center gap-2 shadow-md transition"
              >
                <Lock className="w-3.5 h-3.5 text-amber-300" />
                <span>Verify Investigator Clearance</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>

        </div>
      </section>


      {/* =========================================================================
          SECTION 4: ABOUT & PLATFORM METRICS (#about)
          ========================================================================= */}
      <section id="about" className="py-20 bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center space-y-12">
          
          <div className="max-w-2xl mx-auto space-y-3">
            <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight">
              Engineered for Law Enforcement & Cyber Forensic Labs
            </h2>
            <p className="text-xs sm:text-sm text-slate-500 leading-relaxed">
              Trusted by forensic examiners, digital investigators, and judicial auditors to maintain evidentiary integrity across multi-tiered investigations.
            </p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 font-mono text-center">
            <div className="p-6 rounded-xl bg-slate-50 border border-slate-200">
              <div className="text-3xl font-black text-slate-900 font-mono">100%</div>
              <div className="text-xs text-slate-500 mt-1 uppercase font-semibold">Deterministic Hashing</div>
            </div>
            <div className="p-6 rounded-xl bg-slate-50 border border-slate-200">
              <div className="text-3xl font-black text-[#b45309] font-mono">256-BIT</div>
              <div className="text-xs text-slate-500 mt-1 uppercase font-semibold">Cryptographic Digest</div>
            </div>
            <div className="p-6 rounded-xl bg-slate-50 border border-slate-200">
              <div className="text-3xl font-black text-slate-900 font-mono">ISO 27037</div>
              <div className="text-xs text-slate-500 mt-1 uppercase font-semibold">Evidence Standard</div>
            </div>
            <div className="p-6 rounded-xl bg-slate-50 border border-slate-200">
              <div className="text-3xl font-black text-emerald-700 font-mono">ZERO</div>
              <div className="text-xs text-slate-500 mt-1 uppercase font-semibold">Black-Box Inferences</div>
            </div>
          </div>

        </div>
      </section>


      {/* =========================================================================
          FOOTER (Exact matching reference image, correct compact size)
          ========================================================================= */}
      <footer className="py-4 sm:py-5 bg-white text-xs text-slate-500 border-t border-slate-200 select-none">
        <div className="w-full max-w-[1720px] mx-auto px-4 sm:px-8 lg:px-12 flex flex-col lg:flex-row items-center justify-between gap-3 sm:gap-6">
          
          {/* Left: Brand & Legal Title */}
          <div className="flex items-center gap-3 shrink-0">
            <img
              src="/cryptevid_logo.png"
              alt="CRYPTEVID"
              className="h-8 sm:h-9 w-auto object-contain"
            />
            <div className="text-left">
              <div className="font-bold text-slate-900 font-sans text-xs">
                CRYPTEVID Forensic Intelligence Platform
              </div>
              <div className="text-[10px] text-slate-400">
                Court-Admissible Evidence Custody & Cryptographic Verification Framework
              </div>
            </div>
          </div>

          {/* Center: Clean Nav Links */}
          <div className="flex flex-wrap items-center justify-center gap-5 sm:gap-7 text-xs font-medium text-slate-600">
            <a href="#capabilities" className="hover:text-slate-900 transition-colors">Capabilities</a>
            <a href="#security" className="hover:text-slate-900 transition-colors">Security Framework</a>
            <a href="#about" className="hover:text-slate-900 transition-colors">Compliance</a>
            <Link to="/login" className="text-[#b45309] hover:underline font-bold transition-colors">Investigator Portal</Link>
          </div>

          {/* Right: Security Classification Warning */}
          <div className="text-[10.5px] sm:text-[11px] text-slate-400 font-mono text-center lg:text-right shrink-0">
            Restricted to authorized law enforcement and judicial personnel.
          </div>

        </div>
      </footer>

    </div>
  );
};

export default LandingPage;
