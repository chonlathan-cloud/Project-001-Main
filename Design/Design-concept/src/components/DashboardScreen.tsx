import { motion } from 'motion/react';
import { ArrowUpRight, TrendingUp, DollarSign, Briefcase, FileClock, CheckSquare, Plus, Check, X } from 'lucide-react';
import { Project, ApprovalRequest, ActivityLog } from '../types';

interface DashboardScreenProps {
  projects: Project[];
  approvals: ApprovalRequest[];
  activities: ActivityLog[];
  setScreen: (screen: 'dashboard' | 'projects' | 'approvals' | 'insights') => void;
  handleApprove: (id: string) => void;
  handleReject: (id: string) => void;
  openNewProjectModal: () => void;
}

export default function DashboardScreen({
  projects,
  approvals,
  activities,
  setScreen,
  handleApprove,
  handleReject,
  openNewProjectModal,
}: DashboardScreenProps) {
  // Aggregate stats
  const totalBudget = projects.reduce((acc, p) => acc + p.budget, 0);
  const totalSpent = projects.reduce((acc, p) => acc + p.spent, 0);
  const budgetUtilization = (totalSpent / totalBudget) * 100;
  
  const activeCount = projects.filter((p) => p.status === 'active').length;
  const pendingApprovals = approvals.filter((a) => a.status === 'pending');
  const pendingAmount = pendingApprovals.reduce((acc, a) => acc + a.amount, 0);

  // Formatting helpers
  const formatCurrency = (val: number) => {
    if (val >= 1000000) {
      return `$${(val / 1000000).toFixed(1)}M`;
    }
    return `$${val.toLocaleString()}`;
  };

  return (
    <div id="dashboard-view" className="space-y-8">
      {/* Upper Title Section */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h2 className="font-sans font-bold text-3xl text-zinc-900 tracking-tight">Program Dashboard</h2>
          <p className="font-mono text-xs text-zinc-500 mt-1">Master analytics & governance for Projects-001</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            id="view-analytics-shortcut-btn"
            onClick={() => setScreen('insights')}
            className="px-4 py-2 border border-zinc-200 bg-white text-zinc-700 font-medium text-xs rounded-lg hover:border-zinc-300 hover:text-zinc-900 transition-all flex items-center gap-1.5 shadow-2xs"
          >
            <TrendingUp className="h-3.5 w-3.5" />
            <span>Interactive Insights</span>
          </button>
          <button
            id="create-project-dashboard-btn"
            onClick={openNewProjectModal}
            className="px-4 py-2 bg-zinc-900 text-white font-medium text-xs rounded-lg hover:bg-zinc-800 transition-all flex items-center gap-1.5 shadow-sm"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>New Project</span>
          </button>
        </div>
      </div>

      {/* Primary Program Metrics Dashboard Grid */}
      <div id="metrics-grid" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        {[
          {
            id: 'metric-budget',
            title: 'Allocated Budget',
            value: formatCurrency(totalBudget),
            subtitle: 'Across program entities',
            icon: DollarSign,
            colorClass: 'bg-zinc-900 text-white',
            accentClass: 'text-zinc-400',
          },
          {
            id: 'metric-spent',
            title: 'Actual Spend',
            value: formatCurrency(totalSpent),
            subtitle: `${budgetUtilization.toFixed(1)}% program utilization`,
            icon: ArrowUpRight,
            colorClass: 'bg-white text-zinc-950 border border-zinc-200',
            accentClass: 'text-zinc-400 bg-zinc-100',
          },
          {
            id: 'metric-progress',
            title: 'Active Projects',
            value: `${activeCount} / ${projects.length}`,
            subtitle: `In structural progress`,
            icon: Briefcase,
            colorClass: 'bg-white text-zinc-950 border border-zinc-200',
            accentClass: 'text-zinc-400 bg-zinc-100',
          },
          {
            id: 'metric-pending-approvals',
            title: 'Pending Approvals',
            value: pendingApprovals.length.toString(),
            subtitle: `${formatCurrency(pendingAmount)} unapproved modifications`,
            icon: FileClock,
            colorClass: 'bg-white text-zinc-950 border border-zinc-200',
            accentClass: 'text-zinc-400 bg-zinc-100',
          },
        ].map((m, idx) => {
          const Icon = m.icon;
          return (
            <motion.div
              id={m.id}
              key={m.title}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.05 }}
              className={`p-6 rounded-2xl flex flex-col justify-between h-36 ${m.colorClass}`}
            >
              <div className="flex justify-between items-start">
                <span className="font-mono text-[10px] tracking-wide uppercase font-semibold text-zinc-400">{m.title}</span>
                <div className={`p-1.5 rounded-lg ${m.accentClass}`}>
                  <Icon className="h-4 w-4" />
                </div>
              </div>
              <div>
                <span className="font-sans font-bold text-2xl tracking-tight block mt-2">{m.value}</span>
                <span className="font-mono text-[10px] text-zinc-400 block mt-0.5">{m.subtitle}</span>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Visualization & Activity Split Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Core Visual Progress Chart */}
        <div id="chart-card" className="lg:col-span-2 p-6 bg-white border border-zinc-200 rounded-2xl space-y-6">
          <div className="flex justify-between items-center">
            <div>
              <h3 className="font-sans font-bold text-sm text-zinc-900 tracking-tight">Financial Allocation & Burn Ratio</h3>
              <p className="font-mono text-[10px] text-zinc-400">Budget vs actual spent overview per entity</p>
            </div>
            <span className="text-[10px] font-mono font-medium text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-100">
              Synced with ERP
            </span>
          </div>

          {/* Precision Visual Chart (Custom SVG & Stack Bars) */}
          <div className="space-y-4 pt-2">
            {projects.map((proj) => {
              const spentPct = proj.budget > 0 ? (proj.spent / proj.budget) * 100 : 0;
              return (
                <div key={proj.id} className="space-y-2">
                  <div className="flex justify-between items-baseline">
                    <div className="flex items-center gap-2">
                      <span className={`w-2.5 h-2.5 rounded-xs ${
                        proj.status === 'active' ? 'bg-zinc-900' : 'bg-zinc-300'
                      }`} />
                      <span className="font-sans font-semibold text-xs text-zinc-800">{proj.name}</span>
                      <span className="font-mono text-[10px] text-zinc-400">{proj.code}</span>
                    </div>
                    <div className="flex items-center gap-3 font-mono text-xs">
                      <span className="text-zinc-400">Spent: <strong className="text-zinc-650 font-medium">{formatCurrency(proj.spent)}</strong></span>
                      <span className="text-zinc-300">/</span>
                      <span className="text-zinc-500">Budget: <strong className="text-zinc-800 font-medium">{formatCurrency(proj.budget)}</strong></span>
                      <span className="text-zinc-300">|</span>
                      <span className="font-semibold text-zinc-900">{spentPct.toFixed(0)}%</span>
                    </div>
                  </div>

                  {/* Progressive indicator bar */}
                  <div className="relative w-full h-8 bg-zinc-100 rounded-lg overflow-hidden border border-zinc-200/50">
                    {/* Spent bar */}
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${spentPct}%` }}
                      transition={{ duration: 0.8, ease: 'easeOut' }}
                      className="absolute top-0 left-0 h-full bg-zinc-900 flex items-center pl-3"
                    >
                      {spentPct > 15 && (
                        <span className="font-mono text-[9px] text-white/90 font-medium tracking-wider">
                          {spentPct.toFixed(1)}% SPENT
                        </span>
                      )}
                    </motion.div>
                    {spentPct <= 15 && (
                      <div className="absolute top-0 left-0 h-full flex items-center pl-3">
                        <span className="font-mono text-[9px] text-zinc-500 font-medium tracking-wider">
                          {spentPct.toFixed(1)}% SPENT
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Color Guides / Legends */}
          <div className="flex items-center gap-6 pt-3 border-t border-zinc-100 font-mono text-[10px] text-zinc-400">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 bg-zinc-900 rounded-sm" />
              <span>Capital Expenditure (Spent)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 bg-zinc-105 border border-zinc-200 rounded-sm" />
              <span>Remaining Budget Cap</span>
            </div>
            <div className="ml-auto text-[10px] text-zinc-400 italic">
              Values rounded to $0.1M increments
            </div>
          </div>
        </div>

        {/* Recent Operations Activity Log Panel */}
        <div id="activity-log-card" className="p-6 bg-white border border-zinc-200 rounded-2xl space-y-6 flex flex-col justify-between">
          <div className="space-y-1">
            <h3 className="font-sans font-bold text-sm text-zinc-900 tracking-tight">Recent Operations</h3>
            <p className="font-mono text-[10px] text-zinc-400">Live system sync & governance log</p>
          </div>

          <div className="space-y-4 flex-1 overflow-y-auto max-h-[260px] pr-1 mt-4">
            {activities.slice(0, 4).map((log) => {
              let dotColor = 'bg-zinc-400';
              if (log.type === 'sync') dotColor = 'bg-blue-500';
              if (log.type === 'approval') dotColor = 'bg-emerald-500';
              if (log.type === 'budget_alteration') dotColor = 'bg-amber-500';

              return (
                <div id={`activity-item-${log.id}`} key={log.id} className="flex gap-3 text-xs leading-relaxed">
                  <div className="relative flex flex-col items-center">
                    <span className={`w-2 h-2 rounded-full mt-1.5 ${dotColor}`} />
                    <span className="w-[1px] bg-zinc-200 flex-1 my-1" />
                  </div>
                  <div>
                    <span className="font-medium text-zinc-800 font-sans block">{log.message}</span>
                    <div className="flex items-center gap-2 mt-0.5 font-mono text-[10px] text-zinc-400">
                      <span>{log.user}</span>
                      <span>•</span>
                      <span>{log.timestamp}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          <button
            id="view-all-projects-dashboard-shortcut"
            onClick={() => setScreen('projects')}
            className="w-full py-2.5 text-center text-xs font-semibold text-zinc-700 bg-zinc-50 border border-zinc-150 rounded-lg hover:bg-zinc-100 hover:text-zinc-950 transition-colors mt-auto font-mono"
          >
            Manage Structural Entities
          </button>
        </div>
      </div>

      {/* Interactive Quick Approvals Shelf */}
      <div id="quick-approvals-shelf" className="p-6 bg-amber-50/50 border border-amber-200/60 rounded-2xl space-y-4">
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-2">
            <CheckSquare className="h-4.5 w-4.5 text-amber-600" />
            <h3 className="font-sans font-bold text-sm text-zinc-900 tracking-tight">Urgent Actions</h3>
            <span className="font-mono text-[10px] text-amber-500 font-semibold bg-amber-100 px-2 py-0.5 rounded-full">
              {pendingApprovals.length} PENDING
            </span>
          </div>
          <button
            id="go-to-approvals-shortcut"
            onClick={() => setScreen('approvals')}
            className="text-xs font-mono font-medium text-amber-700 hover:text-amber-900 transition-colors"
          >
            Open Approvals Panel →
          </button>
        </div>

        {pendingApprovals.length === 0 ? (
          <div className="text-zinc-500 font-sans text-xs py-2">
            No pending structural adjustments or change-orders need your immediate signature. All active entities parameters are verified.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {pendingApprovals.slice(0, 3).map((req) => (
              <div
                id={`quick-add-approval-${req.id}`}
                key={req.id}
                className="p-4 bg-white border border-zinc-200 rounded-xl flex flex-col justify-between hover:shadow-2xs transition-all space-y-3"
              >
                <div>
                  <div className="flex justify-between items-start">
                    <span className="font-mono text-[9px] font-semibold tracking-wider text-zinc-400 uppercase bg-zinc-100 px-1.5 py-0.5 rounded">
                      {req.category}
                    </span>
                    <span className="font-mono text-xs font-semibold text-zinc-900">${req.amount.toLocaleString()}</span>
                  </div>
                  <h4 className="font-sans font-semibold text-xs text-zinc-800 mt-2 truncate">{req.title}</h4>
                  <p className="font-mono text-[10px] text-zinc-500 mt-0.5 truncate">{req.projectName}</p>
                </div>

                <div className="flex gap-2">
                  <button
                    id={`quick-reject-btn-${req.id}`}
                    onClick={() => handleReject(req.id)}
                    className="flex-1 py-1.5 border border-zinc-200 bg-white hover:bg-zinc-50 text-zinc-650 hover:text-zinc-950 rounded-md flex items-center justify-center transition-colors text-xs font-medium"
                    title="Reject"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                  <button
                    id={`quick-approve-btn-${req.id}`}
                    onClick={() => handleApprove(req.id)}
                    className="flex-1 py-1.5 bg-zinc-900 text-white hover:bg-zinc-800 rounded-md flex items-center justify-center transition-colors text-xs font-medium gap-1"
                  >
                    <Check className="h-3.5 w-3.5" />
                    <span>Approve</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
