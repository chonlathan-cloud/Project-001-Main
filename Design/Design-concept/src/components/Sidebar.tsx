import { LayoutDashboard, Briefcase, ClipboardCheck, TrendingUp, Settings, HelpCircle, Building2, User } from 'lucide-react';
import { ScreenType } from '../types';

interface SidebarProps {
  currentScreen: ScreenType;
  setScreen: (screen: ScreenType) => void;
  pendingApprovalsCount: number;
}

export default function Sidebar({ currentScreen, setScreen, pendingApprovalsCount }: SidebarProps) {
  const mainNavItems = [
    { id: 'dashboard' as ScreenType, label: 'Dashboard', icon: LayoutDashboard },
    { id: 'projects' as ScreenType, label: 'Projects', icon: Briefcase },
    { id: 'approvals' as ScreenType, label: 'Approvals', icon: ClipboardCheck, badge: pendingApprovalsCount },
    { id: 'insights' as ScreenType, label: 'Insights', icon: TrendingUp },
  ];

  return (
    <aside id="app-sidebar" className="w-64 border-r border-zinc-200 bg-zinc-50 flex flex-col h-screen fixed top-0 left-0 z-20">
      {/* Brand Header */}
      <div className="p-6 border-b border-zinc-200 flex items-center gap-3">
        <div className="h-9 w-9 bg-zinc-900 rounded-lg flex items-center justify-center text-white font-mono font-bold tracking-tight shadow-xs">
          01
        </div>
        <div>
          <h1 className="font-sans font-semibold tracking-tight text-zinc-900 text-sm">Projects-001</h1>
          <p className="font-mono text-[10px] tracking-wide text-zinc-500 uppercase">Program Director</p>
        </div>
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 p-4 space-y-1.5 overflow-y-auto">
        <p className="font-mono text-[10px] uppercase tracking-wider text-zinc-400 font-semibold px-3 mb-2">Main Menu</p>
        {mainNavItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentScreen === item.id;
          return (
            <button
              id={`nav-link-${item.id}`}
              key={item.id}
              onClick={() => setScreen(item.id)}
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                isActive
                  ? 'bg-zinc-900 text-white shadow-xs'
                  : 'text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900'
              }`}
            >
              <div className="flex items-center gap-3">
                <Icon className={`h-4 w-4 ${isActive ? 'text-white' : 'text-zinc-500 hover:text-zinc-900'}`} />
                <span>{item.label}</span>
              </div>
              {item.badge !== undefined && item.badge > 0 && (
                <span
                  id={`nav-badge-${item.id}`}
                  className={`inline-flex items-center justify-center font-semibold rounded-full font-mono text-[10px] h-5 min-w-5 px-1 ${
                    isActive ? 'bg-zinc-800 text-zinc-200' : 'bg-zinc-200 text-zinc-800'
                  }`}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Bottom Subsystems / Info & Profile */}
      <div className="p-4 border-t border-zinc-200 space-y-4">
        {/* Subsystem Shortcuts */}
        <div className="space-y-1">
          <div className="flex items-center gap-3 px-3 py-2 text-xs text-zinc-400 font-semibold uppercase tracking-wider font-mono">
            Integrations & Support
          </div>
          <button
            id="nav-support"
            onClick={() => alert(`Connect on-demand. Systems online & synchronized with ERP master.`)}
            className="w-full flex items-center gap-3 px-3 py-2 text-xs text-zinc-600 font-medium rounded-lg hover:bg-zinc-100 transition-colors"
          >
            <Building2 className="h-3.5 w-3.5 text-zinc-400" />
            <span>ERP Connection Status</span>
            <span className="ml-auto w-2 h-2 rounded-full bg-emerald-500"></span>
          </button>
        </div>

        {/* User Card */}
        <div id="user-profile-preview" className="p-3 bg-white border border-zinc-200 rounded-xl flex items-center gap-3 shadow-2xs">
          <div className="h-9 w-9 rounded-full bg-zinc-200 text-zinc-700 flex items-center justify-center font-medium text-xs border border-zinc-300">
            JH
          </div>
          <div className="flex-1 min-w-0">
            <h4 className="font-sans font-medium text-xs text-zinc-900 truncate">James Harrison</h4>
            <p className="font-mono text-[10px] text-zinc-500 truncate">j.harrison@construction.com</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
