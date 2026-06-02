import { 
  LayoutDashboard, 
  Briefcase, 
  ClipboardCheck, 
  TrendingUp, 
  Settings, 
  HelpCircle, 
  User, 
  Bot, 
  Plus, 
  Wrench 
} from 'lucide-react';
import { ScreenType } from '../types';

interface SidebarProps {
  currentScreen: ScreenType;
  setScreen: (screen: ScreenType) => void;
  pendingApprovalsCount: number;
  onNewProjectClick: () => void;
}

export default function Sidebar({ currentScreen, setScreen, pendingApprovalsCount, onNewProjectClick }: SidebarProps) {
  // Navigation item array matching reference design exactly
  const navItems = [
    { id: 'dashboard' as ScreenType, label: 'Dashboard', icon: LayoutDashboard },
    { id: 'projects' as ScreenType, label: 'Projects', icon: Briefcase },
    { id: 'approvals' as ScreenType, label: 'Approvals', icon: ClipboardCheck, badge: pendingApprovalsCount },
    { id: 'insights' as ScreenType, label: 'Insights', icon: TrendingUp },
    { id: 'chat_ai' as ScreenType, label: 'Chat AI', icon: Bot },
    { id: 'user_profile' as ScreenType, label: 'User Profile', icon: User },
  ];

  return (
    <aside 
      id="app-sidebar" 
      className="w-64 border-r border-zinc-200/80 bg-white flex flex-col h-screen fixed top-0 left-0 z-20 shadow-[1px_0_4px_rgba(0,0,0,0.02)]"
    >
      {/* Brand Header */}
      <div className="p-5 flex items-center gap-3">
        <div className="h-9 w-9 bg-[#3F5E53] rounded-lg flex items-center justify-center text-white shadow-xs">
          <Wrench className="h-4.5 w-4.5 stroke-[2.25px]" />
        </div>
        <div>
          <h1 className="font-sans font-bold tracking-tight text-[#1E2E28] text-[15px] leading-tight">Projects-001</h1>
          <p className="font-sans text-[11px] font-medium text-zinc-400">Admin Portal</p>
        </div>
      </div>

      {/* New Project CTA Button */}
      <div className="px-4 mb-4">
        <button
          id="sidebar-new-project-btn"
          onClick={() => {
            if (currentScreen !== 'projects') {
              setScreen('projects');
            }
            setTimeout(() => {
              onNewProjectClick();
            }, 100);
          }}
          className="w-full py-2.5 bg-[#3F5E53] hover:bg-[#344E44] active:scale-[0.99] text-white font-sans font-semibold text-xs rounded-lg transition-all flex items-center justify-center gap-1.5 shadow-md shadow-emerald-950/10 cursor-pointer"
        >
          <Plus className="h-4 w-4 stroke-[2.5px]" />
          <span>New Project</span>
        </button>
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 px-3 py-2 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          // Support highlight even for placeholders
          const isActive = currentScreen === item.id;
          
          return (
            <button
              id={`nav-link-${item.id}`}
              key={item.id}
              onClick={() => {
                // If it is a real screen, set it
                if (['dashboard', 'projects', 'approvals', 'insights', 'chat_ai', 'user_profile', 'settings'].includes(item.id)) {
                  setScreen(item.id);
                } else {
                  alert(`"${item.label}" screen placeholder clicked. Navigating is simulated.`);
                }
              }}
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-[13px] font-semibold tracking-wide transition-all duration-150 cursor-pointer ${
                isActive
                  ? 'bg-[#FAF4F0] text-[#3F5E53] font-bold shadow-2xs'
                  : 'text-zinc-500 hover:bg-zinc-50 hover:text-zinc-900'
              }`}
            >
              <div className="flex items-center gap-3">
                <Icon className={`h-[18px] w-[18px] stroke-[2px] ${isActive ? 'text-[#3F5E53]' : 'text-zinc-400'}`} />
                <span className={isActive ? 'text-zinc-800' : 'text-zinc-600'}>{item.label}</span>
              </div>
              {item.badge !== undefined && item.badge > 0 && (
                <span
                  id={`nav-badge-${item.id}`}
                  className={`inline-flex items-center justify-center font-bold rounded-full font-mono text-[9px] h-4.5 min-w-4.5 px-1.5 ${
                    isActive ? 'bg-[#3F5E53] text-white' : 'bg-zinc-100 text-zinc-600 border border-zinc-200/60'
                  }`}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Bottom Subsystems / Settings & Support */}
      <div className="p-3 border-t border-zinc-150 flex flex-col gap-0.5">
        <button
          id="nav-settings"
          onClick={() => setScreen('settings')}
          className={`w-full flex items-center gap-3 px-3 py-2.5 text-[13px] font-semibold rounded-lg transition-colors cursor-pointer ${
            currentScreen === 'settings'
              ? 'bg-[#FAF4F0] text-[#3F5E53] font-bold'
              : 'text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900'
          }`}
        >
          <Settings className={`h-[18px] w-[18px] stroke-[2px] ${currentScreen === 'settings' ? 'text-[#3F5E53]' : 'text-zinc-400'}`} />
          <span>Settings</span>
        </button>

        <button
          id="nav-support"
          onClick={() => alert('Opening live technical support portal...')}
          className="w-full flex items-center gap-3 px-3 py-2.5 text-[13px] font-semibold text-zinc-650 rounded-lg hover:bg-zinc-50 transition-colors cursor-pointer"
        >
          <HelpCircle className="h-[18px] w-[18px] text-zinc-400 stroke-[2px]" />
          <span className="text-zinc-600">Support</span>
        </button>
      </div>
    </aside>
  );
}
