import React from 'react';
import { AlertTriangle, RefreshCw, Home, ChevronDown, ChevronUp } from 'lucide-react';

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallbackTitle?: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
  showDetails: boolean;
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      showDetails: false
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("Forensic Workstation Error Boundary caught an error:", error, errorInfo);
    this.setState({ errorInfo });
  }

  handleReload = () => {
    window.location.reload();
  };

  handleGoDashboard = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    window.location.href = '/dashboard';
  };

  handleGoCases = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    window.location.href = '/cases';
  };

  render() {
    if (this.state.hasError) {
      const errorMessage = this.state.error?.message || 'An unexpected client-side exception occurred.';

      return (
        <div className="min-h-[500px] flex items-center justify-center p-6 bg-slate-50 text-slate-900 font-sans">
          <div className="max-w-2xl w-full bg-white rounded-xl shadow-xl border border-red-200 overflow-hidden animate-fade-in-up">
            {/* Header */}
            <div className="bg-gradient-to-r from-red-600 to-rose-700 px-6 py-4 text-white flex items-center gap-3">
              <div className="p-2 bg-white/20 rounded-lg shrink-0">
                <AlertTriangle className="w-6 h-6 text-white" />
              </div>
              <div>
                <h2 className="text-base font-bold font-mono tracking-tight">
                  {this.props.fallbackTitle || 'Forensic Workstation Component Fault'}
                </h2>
                <p className="text-xs text-red-100 font-sans">
                  The interface prevented a blank screen crash and isolated this subsystem error.
                </p>
              </div>
            </div>

            {/* Content Body */}
            <div className="p-6 space-y-4">
              <div className="p-3.5 bg-red-50 rounded-lg border border-red-200">
                <div className="text-xs font-mono font-bold text-red-800 break-all">
                  {errorMessage}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-wrap items-center gap-3 pt-2">
                <button
                  type="button"
                  onClick={this.handleReload}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-xs font-semibold flex items-center gap-2 cursor-pointer shadow-xs transition-colors"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Reload View</span>
                </button>

                <button
                  type="button"
                  onClick={this.handleGoCases}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white rounded-md text-xs font-semibold flex items-center gap-2 cursor-pointer transition-colors"
                >
                  <Home className="w-3.5 h-3.5" />
                  <span>Return to Cases</span>
                </button>
              </div>

              {/* Collapsible Technical Details */}
              <div className="pt-2 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => this.setState(prev => ({ showDetails: !prev.showDetails }))}
                  className="text-xs font-mono text-slate-500 hover:text-slate-800 flex items-center gap-1 cursor-pointer select-none"
                >
                  <span>{this.state.showDetails ? 'Hide' : 'Show'} Diagnostic Stack Trace</span>
                  {this.state.showDetails ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                </button>

                {this.state.showDetails && (
                  <pre className="mt-2 p-3 bg-slate-900 text-slate-200 text-[10px] font-mono rounded-lg overflow-x-auto max-h-48 whitespace-pre-wrap leading-relaxed">
                    {this.state.error?.stack || 'No component stack available.'}
                    {this.state.errorInfo?.componentStack}
                  </pre>
                )}
              </div>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
