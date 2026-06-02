import { useState } from 'react';
import { 
  Search, 
  Loader2,
  Bell, 
  HelpCircle, 
  Calendar, 
  Landmark, 
  TrendingUp, 
  DollarSign, 
  ClipboardCheck, 
  AlertTriangle, 
  ArrowUpRight, 
  CheckCircle2, 
  FileText, 
  Camera as CameraIcon, 
  ChevronRight 
} from 'lucide-react';
import { Project, ApprovalRequest, ActivityLog } from '../types';

interface DashboardStats {
  totalBudget: string;
  budgetChangeLabel: string; // เช่น "+2.4% vs last quarter"
  actualCost: string;
  pendingRequests: number;
  pendingReviewersExtra: number; // เช่น 5 (สำหรับ +5 ใน avatar stack)
  pastDueInvoices: number; // เช่น 12
  cashFlow: string;
  budgetUsagePercentage: number;
  lastUpdated: string;
}

interface ZoneStatus {
  name: string;
  percentage: number;
  color: string;
}

interface DashboardScreenProps {
  projects: Project[]; 
  approvals: ApprovalRequest[];
  activities: ActivityLog[];
  stats: DashboardStats;
  chartData: {
    month: string;
    planned: number;
    actual: number;
  }[];
  zones: ZoneStatus[];
  setScreen: (screen: 'dashboard' | 'projects' | 'approvals' | 'insights') => void;
  handleApprove: (id: string) => void;
  handleReject: (id: string) => void;
  openNewProjectModal: () => void;
  isLoading?: boolean;
}

export default function DashboardScreen({
  projects = [],
  approvals = [],
  activities = [],
  stats,
  chartData = [],
  zones = [],
  setScreen,
  handleApprove,
  handleReject,
  openNewProjectModal,
  isLoading = false,
}: DashboardScreenProps) {
  const [activeTab, setActiveTab] = useState<'Q1' | 'Q2' | 'Q3'>('Q1');

  // ถ้ากำลังโหลด หรือ ข้อมูลสำคัญ (stats) ยังไม่มา ให้แสดง Loading
  if (isLoading || !stats) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Loader2 className="w-10 h-10 text-[#3F5E53] animate-spin" />
      </div>
    );
  }

  return (
    <div id="dashboard-view" className="space-y-6">
      {/* 1. TOP HEADER SECTION (Search & Profile Actions) */}
      <div className="flex flex-col md:flex-row justify-between items-stretch md:items-center gap-4">
        {/* Search Bar Input */}
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-[15px] w-[15px] text-zinc-400" />
          <input
            type="text"
            placeholder="Search..."
            className="w-full pl-9 pr-4 py-2 border border-zinc-200 rounded-lg text-sm bg-white focus:outline-none focus:border-zinc-300 focus:ring-1 focus:ring-zinc-300 transition-all font-sans placeholder-zinc-400 font-medium"
          />
        </div>

        {/* Profile Icons and Notifications */}
        <div className="flex items-center justify-end gap-5">
          {/* Notification Bell */}
          <button className="relative p-1 text-zinc-700 hover:text-zinc-950 transition-colors cursor-pointer">
            <Bell className="h-[21px] w-[21px] stroke-[1.75px]" />
            <span className="absolute top-[2px] right-[2px] h-2 w-2 rounded-full bg-red-600 border border-white" />
          </button>

          {/* Help Center Icon */}
          <button className="p-1 text-zinc-700 hover:text-zinc-950 transition-colors cursor-pointer">
            <HelpCircle className="h-[21px] w-[21px] stroke-[1.75px]" />
          </button>

          {/* User Avatar */}
          <div className="flex items-center gap-1 cursor-pointer">
            <img
              src="https://ui-avatars.com/api/?name=User&background=3F5E53&color=fff"
              alt="User profile"
              className="h-8 w-8 rounded-full border border-zinc-200 object-cover shadow-2xs"
            />
          </div>
        </div>
      </div>

      {/* 2. SUB-HEADER TITLE SECTION */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center border-t border-zinc-200/40 pt-5 gap-3">
        <div>
          <h2 className="font-sans font-bold text-[31px] text-zinc-900 leading-tight tracking-tight">
            Dashboard Overview
          </h2>
          <p className="font-sans text-[13px] text-zinc-500 font-medium mt-0.5">
            Financial summary and critical alerts across all active zones.
          </p>
        </div>
        <div className="flex items-center gap-1.5 font-sans font-semibold text-[11px] text-zinc-500 uppercase tracking-wider bg-white border border-zinc-200/80 px-3 py-1.5 rounded-lg shadow-2xs">
          <Calendar className="h-3.5 w-3.5 text-zinc-400 stroke-[2px]" />
          <span>Last Updated: {stats?.lastUpdated || 'Loading...'}</span>
        </div>
      </div>

      {/* 3. FOUR METRICS DASHBOARD GRID */}
      <div id="metrics-grid" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 pt-1">
        {/* Card 1: TOTAL BUDGET */}
        <div className="bg-white border border-zinc-200/80 rounded-2xl p-5 shadow-2xs flex flex-col justify-between h-[155px] relative overflow-hidden group hover:shadow-xs transition-shadow">
          <div className="flex justify-between items-start">
            <div className="h-[38px] w-[38px] bg-zinc-50 border border-zinc-200/60 rounded-xl flex items-center justify-center text-zinc-650">
              <Landmark className="h-5 w-5 stroke-[2px]" />
            </div>
            <span className="font-sans text-[11px] font-bold text-[#2E7D32] bg-[#E8F5E9] px-2 py-0.5 rounded tracking-wide">
              YTD
            </span>
          </div>
          <div className="mt-4">
            <span className="font-sans text-[11px] font-bold text-zinc-400 tracking-wider block uppercase">
              Total Budget
            </span>
            <span className="font-sans font-extrabold text-[27px] text-zinc-900 leading-none block mt-1 tracking-tight">
              {stats?.totalBudget || '$0.0M'}
            </span>
            <div className="flex items-center gap-1 mt-1 text-[11px] font-bold text-[#2E7D32]">
              <TrendingUp className="h-3.5 w-3.5 stroke-[2.5px]" />
              <span>{stats?.budgetChangeLabel}</span>
            </div>
          </div>
        </div>

        {/* Card 2: ACTUAL COST */}
        <div className="bg-white border border-zinc-200/80 rounded-2xl p-5 shadow-2xs flex flex-col justify-between h-[155px] hover:shadow-xs transition-shadow">
          <div className="flex justify-between items-start">
            <div className="h-[38px] w-[38px] bg-[#FAF6F0] border border-[#F3EBE0] rounded-xl flex items-center justify-center text-[#8C7047]">
              <DollarSign className="h-5 w-5 stroke-[2px]" />
            </div>
          </div>
          <div className="mt-2">
            <span className="font-sans text-[11px] font-bold text-zinc-400 tracking-wider block uppercase">
              Actual Cost
            </span>
            <span className="font-sans font-extrabold text-[27px] text-zinc-900 leading-none block mt-1 tracking-tight">
              {stats?.actualCost || '$0.0M'}
            </span>
            {/* Custom forest green progress indicator */}
            <div className="mt-2 space-y-1">
              <div className="w-full h-1.5 bg-zinc-100 rounded-full overflow-hidden">
                <div className="h-full bg-[#3F5E53] rounded-full" style={{ width: `${stats?.budgetUsagePercentage || 0}%` }} />
              </div>
              <span className="font-sans text-[11px] font-semibold text-zinc-500 block">
                {stats?.budgetUsagePercentage || 0}% of total budget consumed
              </span>
            </div>
          </div>
        </div>

        {/* Card 3: PENDING REQUESTS */}
        <div className="bg-white border border-zinc-200/80 rounded-2xl p-5 shadow-2xs flex flex-col justify-between h-[155px] hover:shadow-xs transition-shadow">
          <div className="flex justify-between items-start">
            <div className="h-[38px] w-[38px] bg-red-50 border border-red-100 rounded-xl flex items-center justify-center text-[#C5221F]">
              <ClipboardCheck className="h-5 w-5 stroke-[2px]" />
            </div>
            <span className="font-sans text-[10px] font-bold text-[#C5221F] bg-[#FCE8E6] px-2 py-0.5 rounded tracking-wide">
              ACTION REQ
            </span>
          </div>
          <div className="mt-3">
            <span className="font-sans text-[11px] font-bold text-zinc-400 tracking-wider block uppercase">
              Pending Requests
            </span>
            <span className="font-sans font-extrabold text-[27px] text-zinc-900 leading-none block mt-1 tracking-tight">
              {stats?.pendingRequests || 0}
            </span>
            <div className="flex items-center gap-2 mt-2">
              {/* Profile Avatars overlapping Stack */}
              <div className="flex -space-x-2 overflow-hidden">
                <img
                  className="inline-block h-[20px] w-[20px] rounded-full ring-2 ring-white object-cover"
                  src="https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=40&h=40&q=80"
                  alt="Reviewer 1"
                />
                <img
                  className="inline-block h-[20px] w-[20px] rounded-full ring-2 ring-white object-cover"
                  src="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=40&h=40&q=80"
                  alt="Reviewer 2"
                />
                <div className="inline-flex h-[20px] w-[20px] rounded-full ring-2 ring-white bg-zinc-200 items-center justify-center text-[9px] font-bold text-zinc-650">
                  +{stats?.pendingReviewersExtra || 0}
                </div>
              </div>
              <span className="font-sans text-[11px] font-semibold text-zinc-500">
                awaiting review
              </span>
            </div>
          </div>
        </div>

        {/* Card 4: CASH FLOW (Red Left Border) */}
        <div className="bg-white border-y border-r border-l-4 border-l-[#C5221F] border-zinc-200/80 rounded-2xl p-5 shadow-2xs flex flex-col justify-between h-[155px] hover:shadow-xs transition-shadow">
          <div className="flex justify-between items-start">
            <div className="h-[38px] w-[38px] bg-red-50 border border-red-100 rounded-xl flex items-center justify-center text-[#C5221F]">
              <AlertTriangle className="h-5 w-5 stroke-[2px]" />
            </div>
          </div>
          <div className="mt-4">
            <span className="font-sans text-[11px] font-bold text-zinc-400 tracking-wider block uppercase">
              Cash F
            </span>
            <span className="font-sans font-extrabold text-[27px] text-zinc-900 leading-none block mt-1 tracking-tight">
              {stats?.cashFlow || '$0.0M'}
            </span>
            <div className="flex items-center gap-1 mt-2 text-[11px] font-semibold text-zinc-500">
              <span className="text-[#C5221F] font-bold">{stats?.pastDueInvoices || 0}</span>
              <span>invoices past 30 days</span>
            </div>
          </div>
        </div>
      </div>

      {/* 4. VISUALIZATION AND ZONE STATUS SPLIT */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 pt-1">
        {/* Left Side: Cashflow Projection Bar Chart (Width 2/3) */}
        <div className="lg:col-span-2 bg-white border border-zinc-200/80 rounded-2xl p-6 shadow-2xs flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <div>
              <h3 className="font-sans font-bold text-base text-zinc-900 tracking-tight">
                Cashflow Projection
              </h3>
            </div>
            {/* Tabs matching reference styling */}
            <div className="flex border border-zinc-200 rounded-lg p-0.5 bg-zinc-50/50 shadow-3xs">
              {(['Q1', 'Q2', 'Q3'] as const).map((q) => (
                <button
                  key={q}
                  onClick={() => setActiveTab(q)}
                  className={`px-3 py-1 text-xs font-bold rounded-md transition-all cursor-pointer ${
                    activeTab === q
                      ? 'bg-zinc-900 text-white shadow-2xs'
                      : 'text-zinc-500 hover:text-zinc-900 hover:bg-zinc-100/50'
                  }`}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>

          {/* Precision Grouped Bar Chart Rendered with Pure CSS/HTML for crisp alignment */}
          <div className="relative h-[240px] mt-6 flex flex-col justify-between">
            {/* Horizontal Gridlines */}
            <div className="absolute inset-0 flex flex-col justify-between pointer-events-none pr-1">
              {[40, 30, 20, 10, 0].map((val) => (
                <div key={val} className="flex items-center w-full">
                  <span className="w-10 font-sans text-[10px] font-bold text-zinc-400 text-left">
                    ${val}M
                  </span>
                  <div className="flex-1 border-t border-zinc-100" />
                </div>
              ))}
            </div>

            {/* Bars Column Wrapper */}
            <div className="absolute left-10 right-0 top-0 bottom-4 flex justify-around items-end px-3">
              {chartData.map((data) => {
                // Height percentage calculations based on 40M limit
                const plannedHeight = (data.planned / 40) * 100;
                const actualHeight = (data.actual / 40) * 100;

                return (
                  <div key={data.month} className="flex flex-col items-center h-full justify-end w-[60px] group">
                    <div className="flex items-end gap-1.5 h-full pb-1">
                      {/* Planned Bar (Warm Beige) */}
                      <div 
                        className="w-[18px] bg-[#E8E5DF] hover:bg-[#DDD9D1] transition-all rounded-xs relative group/bar cursor-pointer"
                        style={{ height: `${plannedHeight}%` }}
                      >
                        <div className="absolute -top-7 left-1/2 -translate-x-1/2 bg-zinc-900 text-white text-[9px] font-bold py-1 px-1.5 rounded opacity-0 group-hover/bar:opacity-100 transition-opacity whitespace-nowrap shadow-sm pointer-events-none z-10">
                          Planned: ${data.planned}M
                        </div>
                      </div>

                      {/* Actual Bar (Forest Green) */}
                      <div 
                        className="w-[18px] bg-[#3F5E53] hover:bg-[#324C42] transition-all rounded-xs relative group/bar cursor-pointer"
                        style={{ height: `${actualHeight}%` }}
                      >
                        <div className="absolute -top-7 left-1/2 -translate-x-1/2 bg-zinc-900 text-white text-[9px] font-bold py-1 px-1.5 rounded opacity-0 group-hover/bar:opacity-100 transition-opacity whitespace-nowrap shadow-sm pointer-events-none z-10">
                          Actual: ${data.actual}M
                        </div>
                      </div>
                    </div>
                    {/* Month Label */}
                    <span className="font-sans text-[10px] font-bold text-zinc-400 tracking-wider mt-1.5">
                      {data.month}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Legends */}
          <div className="flex items-center justify-center gap-6 pt-5 border-t border-zinc-100 font-sans text-[11px] font-bold text-zinc-500 mt-2">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 bg-[#E8E5DF] rounded-xs" />
              <span>Planned</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 bg-[#3F5E53] rounded-xs" />
              <span>Actual</span>
            </div>
          </div>
        </div>

        {/* Right Side: Zone Status Panel (Width 1/3) */}
        <div className="bg-white border border-zinc-200/80 rounded-2xl p-5 shadow-2xs flex flex-col justify-between">
          <div>
            <h3 className="font-sans font-bold text-base text-zinc-900 tracking-tight mb-5">
              Zone Status
            </h3>
            {/* Zone Status Tracks */}
            <div className="space-y-5">
              {zones.map((zone, index) => (
                <div key={index} className="space-y-1.5">
                  <div className="flex justify-between items-baseline font-sans text-[13px]">
                    <span className="font-bold text-zinc-700">{zone.name}</span>
                    <span className="font-extrabold text-sm" style={{ color: zone.color }}>{zone.percentage}%</span>
                  </div>
                  <div className="w-full h-2 bg-zinc-100 rounded-full overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: `${zone.percentage}%`, backgroundColor: zone.color }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Action button styled with premium bronze outline */}
          <button
            id="zone-status-report-btn"
            onClick={() => setScreen('insights')}
            className="w-full py-2.5 text-center text-xs font-bold text-[#8C7047] border border-[#A88B60]/70 hover:border-[#A88B60] bg-white hover:bg-[#FAF7F2] active:scale-[0.99] rounded-lg tracking-wider transition-all uppercase mt-6 cursor-pointer"
          >
            View Detailed Report
          </button>
        </div>
      </div>

      {/* 5. BOTTOM SECTION: RISKY PROJECTS AND RECENT ACTIONS */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 pt-1">
        {/* Left Side: Risky Projects Alert Grid (Width 3/5) */}
        <div className="lg:col-span-3 bg-white border border-zinc-200/80 rounded-2xl p-5 shadow-2xs flex flex-col justify-between">
          <div>
            <div className="flex justify-between items-center mb-4">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-red-500 stroke-[2px]" />
                <h3 className="font-sans font-bold text-base text-zinc-900 tracking-tight">
                  Risky Projects
                </h3>
              </div>
              <button
                onClick={() => setScreen('projects')}
                className="text-xs font-bold text-[#8C7047] hover:underline flex items-center gap-0.5 cursor-pointer"
              >
                <span>View All</span>
                <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>

            {/* Table structure matching screenshot */}
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-zinc-100">
                    <th className="py-2.5 font-sans font-extrabold text-[11px] text-zinc-400 tracking-wider uppercase w-5/12">
                      Project Code
                    </th>
                    <th className="py-2.5 font-sans font-extrabold text-[11px] text-zinc-400 tracking-wider uppercase text-center w-4/12">
                      Risk Factor
                    </th>
                    <th className="py-2.5 font-sans font-extrabold text-[11px] text-zinc-400 tracking-wider uppercase text-right w-3/12">
                      Variance
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-50">
                  {projects.filter(p => p.status === 'Delayed' || (p.budgetUsed / p.totalBudget > 0.9)).slice(0, 3).map((project) => (
                    <tr key={project.id}>
                      <td className="py-3 font-sans">
                        <div className="font-bold text-[13px] text-zinc-900">{project.id}</div>
                        <div className="text-[11px] font-semibold text-zinc-400">{project.name}</div>
                      </td>
                      <td className="py-3 text-center">
                        <span className={`inline-block font-sans text-[11px] font-extrabold px-2 py-0.5 rounded tracking-wide ${
                          project.status === 'Delayed' ? 'text-[#C5221F] bg-[#FCE8E6]' : 'text-[#8F6B00] bg-[#FFF8E1]'
                        }`}>
                          {project.status === 'Delayed' ? 'Schedule Delay' : 'Budget Warning'}
                        </span>
                      </td>
                      <td className={`py-3 text-right font-sans font-bold text-[13px] ${
                        project.status === 'Delayed' ? 'text-[#C5221F]' : 'text-[#8F6B00]'
                      }`}>
                        {project.status === 'Delayed' ? '-14 Days' : `+${Math.round((project.budgetUsed/project.totalBudget)*100)}%`}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Right Side: Recent Actions Feed (Width 2/5) */}
        <div className="lg:col-span-2 bg-white border border-zinc-200/80 rounded-2xl p-5 shadow-2xs flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-5">
              {/* Timeline icon */}
              <svg 
                xmlns="http://www.w3.org/2000/svg" 
                viewBox="0 0 24 24" 
                fill="none" 
                stroke="currentColor" 
                strokeWidth="2" 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                className="h-5 w-5 text-zinc-700 stroke-[2px]"
              >
                <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
                <path d="M3 3v5h5" />
                <path d="M12 7v5l4 2" />
              </svg>
              <h3 className="font-sans font-bold text-base text-zinc-900 tracking-tight">
                Recent Actions
              </h3>
            </div>

            {/* Custom Vertical Timeline Checklist */}
            <div className="relative pl-7 space-y-5 border-l border-zinc-100 ml-3.5">
              {activities.slice(0, 3).map((activity) => (
                <div key={activity.id} className="relative">
                  <div className={`absolute -left-10.5 top-0.5 h-7 w-7 rounded-full border flex items-center justify-center shadow-3xs z-10 ${
                    activity.type === 'approval' ? 'bg-[#E8F5E9] border-[#C8E6C9] text-[#2E7D32]' :
                    activity.type === 'update' ? 'bg-[#FAF6F0] border-[#F3EBE0] text-[#8C7047]' :
                    'bg-zinc-50 border-zinc-200/60 text-zinc-500'
                  }`}>
                    {activity.type === 'approval' ? <CheckCircle2 className="h-4 w-4 stroke-[2.5px]" /> :
                     activity.type === 'update' ? <CameraIcon className="h-3.5 w-3.5 stroke-[2.25px]" /> :
                     <FileText className="h-4 w-4 stroke-[2px]" />}
                  </div>
                  <div className="flex justify-between items-start gap-2">
                    <div className="font-sans text-[13px] leading-tight text-zinc-700">
                      <span className="font-extrabold text-zinc-900">{activity.user}</span> {activity.action}
                      <div className="text-[11px] font-semibold text-zinc-400 mt-0.5">
                        {activity.target}
                      </div>
                    </div>
                    <span className="font-sans text-[10px] font-bold text-zinc-400 whitespace-nowrap">
                      {activity.timestamp}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
