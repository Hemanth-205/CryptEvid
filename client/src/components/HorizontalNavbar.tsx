import React, { useState, useEffect, useMemo } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  LogOut,
  Menu,
  X
} from 'lucide-react';
import { caseApi } from '../services/api';
import type { Case } from '../types';

export const HorizontalNavbar: React.FC = () => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [activeCase, setActiveCase] = useState<Case | null>(null);

  const handleLogout = (e?: React.MouseEvent) => {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    logout();
  };

  // Fetch active case context
  useEffect(() => {
    const fetchActiveCase = async () => {
      try {
        const res = await caseApi.getCases({ limit: 1 });
        if (res.cases && res.cases.length > 0) {
          setActiveCase(res.cases[0]);
        } else {
          setActiveCase(null);
        }
      } catch (err) {
        setActiveCase(null);
      }
    };
    fetchActiveCase();
  }, [location.pathname]);

  // Close mobile drawer on route change
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname]);

  const isPortalManager = user?.role === 'portal_manager';
  const isAdmin = user?.role === 'admin';
  const isManagerOrAdmin = isAdmin || isPortalManager;

  const navItems = useMemo(() => {
    // In Admin login, ONLY Portal Users and Settings page must be visible
    if (isManagerOrAdmin) {
      return [
        { name: 'Portal Users', path: '/portal-manager' },
        { name: 'Settings', path: '/settings' },
      ];
    }
    // For other users (investigator, lead investigator, etc.), Portal Users is NOT displayed
    return [
      { name: 'Dashboard', path: '/dashboard' },
      { name: 'Cases', path: '/cases' },
      { name: 'Graph', path: '/graph' },
      { name: 'Threat Intel', path: '/ai-analysis' },
      { name: 'Alerts', path: '/security-alerts' },
      { name: 'Reports', path: '/reports' },
      { name: 'Settings', path: '/settings' }
    ];
  }, [isManagerOrAdmin]);

  return (
    <header className="sticky top-0 z-50 select-none border-b transition-colors duration-200 bg-white border-slate-200 text-slate-900 shadow-xs">
      {/* Primary Navigation Row - Full Width & Professional */}
      <div className="w-full px-5 sm:px-8 lg:px-12">
        <div className="flex items-center justify-between h-16 gap-6">
          
          {/* Left: Brand Identity */}
          <div className="flex items-center gap-4 shrink-0">
            <Link to={isManagerOrAdmin ? "/portal-manager" : "/dashboard"} className="flex items-center gap-3 group">
              <img
                src="/cryptevid_logo.png"
                alt="CRYPTEVID"
                className="h-11 sm:h-12 w-auto object-contain rounded-lg shadow-xs transition-transform group-hover:scale-105"
              />
              <div className="flex flex-col">
                <span className="text-base font-extrabold tracking-wider uppercase font-sans text-slate-900 group-hover:text-amber-600 transition-colors">
                  CRYPTEVID
                </span>
                <span className="text-[11px] text-slate-500 font-sans tracking-tight">
                  Forensic Intelligence Platform
                </span>
              </div>
            </Link>
          </div>

          {/* Center: Desktop Navigation - Clean Text Only (No Icons) */}
          <nav className="hidden lg:flex items-center gap-1.5 py-1">
            {navItems.map((item) => {
              const isActive =
                location.pathname === item.path ||
                (item.path !== '/dashboard' && location.pathname.startsWith(item.path));
              return (
                <Link
                  key={item.path}
                  to={item.path}
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
                  {item.name}
                </Link>
              );
            })}
          </nav>

          {/* Right: Operational Status, User Profile & Actions */}
          <div className="flex items-center gap-3 sm:gap-4 shrink-0">
            {/* Live Platform Security Status Badge */}
            <div className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-[10px] font-mono font-bold text-emerald-700">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span>FORENSIC ENGINE ONLINE</span>
            </div>

            {/* User Profile & Logout */}
            <div className="flex items-center gap-2.5 pl-3 border-l border-slate-200">
              <div className="hidden md:flex flex-col text-right">
                <span className="text-xs font-bold leading-tight text-slate-900">
                  {user?.name || 'Lead Investigator'}
                </span>
                <span className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded border mt-0.5 font-semibold ${
                  user?.role === 'portal_manager'
                    ? 'text-blue-700 bg-blue-50 border-blue-200'
                    : user?.role === 'admin'
                    ? 'text-red-700 bg-red-50 border-red-200'
                    : 'text-amber-700 bg-amber-50 border-amber-200'
                }`}>
                  {user?.role === 'portal_manager' ? 'PORTAL MANAGER' : (user?.role || 'Examiner')}
                </span>
              </div>
              <button
                onClick={handleLogout}
                title="End Session & Logout"
                className="w-8 h-8 rounded-lg border flex items-center justify-center transition-all cursor-pointer bg-white hover:bg-red-50 text-slate-600 hover:text-red-600 border-slate-200 hover:border-red-200 shadow-xs active:scale-95"
              >
                <LogOut className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Mobile Menu Button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="lg:hidden w-8 h-8 rounded-md border flex items-center justify-center transition-colors bg-slate-100 text-slate-700 border-slate-200"
              aria-label="Toggle navigation menu"
            >
              {mobileMenuOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </div>

      {/* Sub-header Context Bar: Active Case Dossier Breadcrumb (Visible only to casework investigators) */}
      {!isManagerOrAdmin && (
        <div className="w-full px-5 sm:px-8 lg:px-12 py-1.5 text-xs font-mono border-t bg-slate-50 border-slate-200 text-slate-600">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-2.5 truncate">
              <span className="text-[11px] uppercase tracking-wider font-semibold text-slate-600">
                ACTIVE CASE:
              </span>
              {activeCase ? (
                <div className="flex items-center gap-2 truncate">
                  <Link
                    to={`/cases/${activeCase._id}`}
                    className="font-bold hover:underline truncate text-blue-600 hover:text-blue-700"
                  >
                    {activeCase.case_number}
                  </Link>
                  <span className="text-slate-300">|</span>
                  <span className="truncate font-sans text-xs text-slate-800 font-medium">
                    {activeCase.title}
                  </span>
                  <span
                    className={`ws-badge ${
                      activeCase.status === 'IN_PROGRESS'
                        ? 'ws-badge-amber'
                        : activeCase.status === 'CLOSED'
                        ? 'ws-badge-green'
                        : 'ws-badge-gray'
                    }`}
                  >
                    {activeCase.status}
                  </span>
                </div>
              ) : (
                <span className="text-xs text-slate-600">
                  No active case selected • Open case file to bind context
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Mobile Drawer Menu - Text Only with Full Profile & Controls */}
      {mobileMenuOpen && (
        <div className="lg:hidden border-b px-4 py-3 space-y-3 bg-white border-slate-200 text-slate-900 shadow-lg animate-fade-in-up">
          {/* User Info Bar on Mobile */}
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <div className="flex flex-col">
              <span className="text-xs font-bold leading-tight text-slate-900">
                {user?.name || 'Lead Investigator'}
              </span>
              <span className="text-[10px] font-mono uppercase text-amber-700 bg-amber-50 px-1.5 py-0.2 rounded border border-amber-200 mt-0.5 font-semibold w-fit">
                {user?.role || 'Examiner'}
              </span>
            </div>
            
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-[10px] font-mono font-bold text-emerald-700">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span>ENGINE ONLINE</span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-1.5">
            {navItems.map((item) => {
              const isActive =
                location.pathname === item.path ||
                (item.path !== '/dashboard' && location.pathname.startsWith(item.path));
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`ws-nav-link justify-center py-2.5 ${isActive ? 'ws-nav-link-active' : ''}`}
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
                  {item.name}
                </Link>
              );
            })}
          </div>

          {/* Mobile Logout Button */}
          <button
            onClick={handleLogout}
            className="w-full py-2.5 rounded-lg border border-red-200 bg-red-50/50 hover:bg-red-50 text-red-700 text-xs font-bold flex items-center justify-center gap-2 transition"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>End Workstation Session</span>
          </button>
        </div>
      )}
    </header>
  );
};

export default HorizontalNavbar;
