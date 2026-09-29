import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCcw } from 'lucide-react';

interface Props {
  children?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class GlobalErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="w-screen h-screen flex flex-col items-center justify-center bg-radar-950 text-radar-200 font-mono select-none">
          <div className="flex flex-col items-center bg-radar-900 border border-suspect-crimson/80 p-8 rounded-sm max-w-lg text-center shadow-2xl">
            <AlertTriangle className="w-12 h-12 text-suspect-crimson mb-4" />
            <h1 className="text-xl font-bold text-radar-100 mb-2">SYSTEM FAILURE DETECTED</h1>
            <p className="text-sm text-radar-400 mb-6">
              A critical exception occurred in the UI render thread. 
            </p>
            <div className="w-full bg-radar-950 p-3 rounded-xs border border-radar-800 text-left overflow-hidden text-xs text-radar-500 mb-6">
              {this.state.error?.message || 'Unknown Error'}
            </div>
            <button
              onClick={() => window.location.reload()}
              className="flex items-center gap-2 px-4 py-2 bg-suspect-crimson/20 hover:bg-suspect-crimson/30 border border-suspect-crimson text-suspect-crimson font-bold rounded-xs transition-colors"
            >
              <RefreshCcw className="w-4 h-4" />
              <span>REBOOT SUBSYSTEM</span>
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
