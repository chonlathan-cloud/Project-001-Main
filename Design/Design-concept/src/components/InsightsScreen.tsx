import { useState } from 'react';
import { motion } from 'motion/react';
import { ArrowUpRight, ArrowDownRight, RefreshCw, BarChart2 } from 'lucide-react';
import { Project } from '../types';

interface InsightsScreenProps {
  projects: Project[];
}

export default function InsightsScreen({ projects }: InsightsScreenProps) {
  const [selectedProjectId, setSelectedProjectId] = useState<string>('all');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [forecastInflation, setForecastInflation] = useState<number>(2.5); // slider parameter! Great interactivity

  // Compute stats based on project filters
  const filteredProjects = selectedProjectId === 'all' 
    ? projects 
    : projects.filter(p => p.id === selectedProjectId);

  const totalBudget = filteredProjects.reduce((acc, p) => acc + p.budget, 0);
  const totalSpent = filteredProjects.reduce((acc, p) => acc + p.spent, 0);
  const remainingBudget = totalBudget - totalSpent;

  // Let's mock cost categories inside these projects for distribution
  const categories = [
    { label: 'Structural & Core', pct: 40, color: 'bg-zinc-900', stroke: '#18181b' },
    { label: 'Finishes & Curtain Walls', pct: 25, color: 'bg-zinc-600', stroke: '#52525b' },
    { label: 'HVAC & Plumbing', pct: 15, color: 'bg-zinc-400', stroke: '#a1a1aa' },
    { label: 'Electrical & Automation', pct: 12, color: 'bg-zinc-300', stroke: '#d4d4d8' },
    { label: 'Civil Works & Prep', pct: 8, color: 'bg-zinc-200', stroke: '#e4e4e7' }
  ];

  // Calculated forecasting with inflation slider
  const forecastFinalSpent = totalSpent + (remainingBudget * (1 + forecastInflation / 100));
  const costVariance = totalBudget - forecastFinalSpent;

  return (
    <div id="insights-view" className="space-y-8">
      {/* Upper Title */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h2 className="font-sans font-bold text-3xl text-zinc-900 tracking-tight">Governance & Cost Insights</h2>
          <p className="font-mono text-xs text-zinc-500 mt-1">Predictive cost modeling & compliance matrices</p>
        </div>
        
        {/* Active Filters Panel */}
        <div className="flex flex-wrap items-center gap-2.5 bg-white p-2 border border-zinc-200 rounded-xl shadow-2xs">
          <div className="flex items-center gap-1.5 px-2 text-zinc-400">
            <BarChart2 className="h-3.5 w-3.5" />
            <span className="font-mono text-[10px] tracking-wider uppercase font-semibold">Controls:</span>
          </div>

          {/* Project Selector */}
          <select
            id="insights-project-selector"
            value={selectedProjectId}
            onChange={(e) => setSelectedProjectId(e.target.value)}
            className="px-3 py-1.5 border border-zinc-200 rounded-lg text-xs font-sans font-medium text-zinc-700 bg-zinc-50 focus:outline-none focus:border-zinc-400"
          >
            <option value="all">Project Entity: All</option>
            {projects.map(p => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>

          {/* Cost Category */}
          <select
            id="insights-category-selector"
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="px-3 py-1.5 border border-zinc-200 rounded-lg text-xs font-sans font-medium text-zinc-700 bg-zinc-50 focus:outline-none focus:border-zinc-400"
          >
            <option value="all">Cost Sub-Group: All</option>
            <option value="structural">Structural</option>
            <option value="finishes">Finishes</option>
            <option value="hvac">HVAC & MEP</option>
            <option value="electrical">Electrical</option>
            <option value="civil">Civil</option>
          </select>
        </div>
      </div>

      {/* Main Grid: Forecast parameters & KPI indicators */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Predictive Simulator Engine (Slider Control) */}
        <div id="predictive-simulator-block" className="p-6 bg-white border border-zinc-200 rounded-2xl flex flex-col justify-between space-y-4 shadow-2xs">
          <div>
            <h3 className="font-sans font-bold text-sm text-zinc-900 tracking-tight">Active Forecast Simulator</h3>
            <p className="font-mono text-[10px] text-zinc-400">Simulate inflation on remaining unspent budget ($ { (remainingBudget/1000000).toFixed(1) }M)</p>
          </div>

          <div className="bg-zinc-50 p-4 rounded-xl border border-zinc-150 space-y-4 my-2">
            <div className="flex justify-between items-center">
              <span className="font-mono text-xs text-zinc-500">Buffer Overrun Rate:</span>
              <span className="font-mono text-xs font-bold text-zinc-900">{forecastInflation.toFixed(1)}%</span>
            </div>
            <input
              id="forecast-inflation-slider"
              type="range"
              min="0"
              max="15"
              step="0.5"
              value={forecastInflation}
              onChange={(e) => setForecastInflation(parseFloat(e.target.value))}
              className="w-full accent-zinc-905 bg-zinc-200 h-1.5 rounded-lg cursor-pointer"
            />
            <div className="flex justify-between text-[10px] font-mono text-zinc-400">
              <span>0% (Target)</span>
              <span>7.5%</span>
              <span>15% (Extreme)</span>
            </div>
          </div>

          <div className="space-y-2 pt-2 border-t border-zinc-100">
            <div className="flex justify-between items-center text-xs">
              <span className="font-sans text-zinc-500">Estimated Final Program Cost:</span>
              <span className="font-mono font-semibold text-zinc-900">${(forecastFinalSpent / 1000000).toFixed(2)}M</span>
            </div>
            <div className="flex justify-between items-center text-xs">
              <span className="font-sans text-zinc-500">Allocated Ceiling:</span>
              <span className="font-mono text-zinc-400">${(totalBudget / 1000000).toFixed(2)}M</span>
            </div>
            <div className="flex justify-between items-center text-xs pt-1.5 border-t border-dashed border-zinc-200">
              <span className="font-sans font-semibold text-zinc-700">Projected Variance:</span>
              <div className="flex items-center gap-1 font-mono font-bold">
                {costVariance >= 0 ? (
                  <span className="text-emerald-600 flex items-center gap-0.5">
                    <ArrowDownRight className="h-3.5 w-3.5" />
                    +${(costVariance / 1000000).toFixed(2)}M Surplus
                  </span>
                ) : (
                  <span className="text-red-500 flex items-center gap-0.5">
                    <ArrowUpRight className="h-3.5 w-3.5" />
                    -${(Math.abs(costVariance) / 1000000).toFixed(2)}M Deficit
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Schedule & Cost Index Gauges (SPI/CPI) */}
        <div id="efficiency-indexes" className="p-6 bg-white border border-zinc-200 rounded-2xl space-y-6 shadow-2xs">
          <div>
            <h3 className="font-sans font-bold text-sm text-zinc-900 tracking-tight">Program Control Indexes</h3>
            <p className="font-mono text-[10px] text-zinc-400">Schedule & cost resource metrics (Target: &gt;1.0)</p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* SPI */}
            <div className="p-4 bg-zinc-50 rounded-xl border border-zinc-150 flex flex-col justify-between items-center text-center space-y-3">
              <div>
                <span className="font-sans font-semibold text-xs text-zinc-500 block">Schedule Index (SPI)</span>
                <span className="font-mono text-[9px] text-zinc-400">Earned / Planned</span>
              </div>
              <div className="relative flex items-center justify-center">
                {/* Visual gauge representation matching high quality builder */}
                <div className="w-20 h-20 rounded-full border-4 border-emerald-500/20 flex items-center justify-center border-t-emerald-500 rotate-45">
                  <span className="font-mono font-bold text-lg text-emerald-600 -rotate-45">1.04</span>
                </div>
              </div>
              <span className="font-mono text-[10px] text-emerald-600 font-semibold uppercase tracking-wider bg-emerald-50 px-2 py-0.5 rounded border border-emerald-100">
                On Schedule
              </span>
            </div>

            {/* CPI */}
            <div className="p-4 bg-zinc-50 rounded-xl border border-zinc-150 flex flex-col justify-between items-center text-center space-y-3">
              <div>
                <span className="font-sans font-semibold text-xs text-zinc-500 block">Cost Index (CPI)</span>
                <span className="font-mono text-[9px] text-zinc-400">Value / Actual Spent</span>
              </div>
              <div className="relative flex items-center justify-center">
                <div className="w-20 h-20 rounded-full border-4 border-amber-500/20 flex items-center justify-center border-t-amber-500 rotate-180">
                  <span className="font-mono font-bold text-lg text-amber-600 -rotate-180">0.98</span>
                </div>
              </div>
              <span className="font-mono text-[10px] text-amber-655 font-semibold uppercase tracking-wider bg-amber-50 px-2 py-0.5 rounded border border-amber-100">
                Slight Overrun
              </span>
            </div>
          </div>
        </div>

        {/* Cost Subcategory Allocation */}
        <div id="cost-subcategories-list" className="p-6 bg-white border border-zinc-200 rounded-2xl space-y-4 shadow-2xs">
          <div>
            <h3 className="font-sans font-bold text-sm text-zinc-900 tracking-tight">Sub-Group Allocation Breakdown</h3>
            <p className="font-mono text-[10px] text-zinc-400">Budget weight across civil & finish trades</p>
          </div>

          <div className="space-y-3 pt-1">
            {categories.map((cat) => (
              <div key={cat.label} className="space-y-1">
                <div className="flex justify-between items-center font-mono text-[10px]">
                  <span className="font-sans font-medium text-zinc-600">{cat.label}</span>
                  <span className="font-semibold text-zinc-800">{cat.pct}%</span>
                </div>
                <div className="h-2 w-full bg-zinc-100 rounded-full overflow-hidden border border-zinc-200/55">
                  <div className={`h-full ${cat.color}`} style={{ width: `${cat.pct}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Advanced Visual Timeline (Custom SVG Forecast curve) */}
      <div className="p-6 bg-white border border-zinc-200 rounded-2xl space-y-4 shadow-2xs">
        <div>
          <h3 className="font-sans font-bold text-sm text-zinc-900 tracking-tight">Capital Expenditure Forecast Curve</h3>
          <p className="font-mono text-[10px] text-zinc-400">Target project S-Curve vs baseline spent forecast (May 2024 - Dec 2026)</p>
        </div>

        {/* Dynamic high quality SVG drawing curve */}
        <div className="relative w-full h-64 bg-zinc-50 rounded-xl overflow-hidden border border-zinc-150 p-4">
          <svg className="w-full h-full" viewBox="0 0 800 200" preserveAspectRatio="none">
            {/* Grid Lines */}
            <line x1="0" y1="50" x2="800" y2="50" stroke="#f1f1f1" strokeWidth="1" />
            <line x1="0" y1="100" x2="800" y2="100" stroke="#f1f1f1" strokeWidth="1" />
            <line x1="0" y1="150" x2="800" y2="150" stroke="#f1f1f1" strokeWidth="1" />
            
            {/* Baseline S-Curve line */}
            <path
              d="M 50 180 Q 200 170 350 120 T 650 40 T 780 20"
              fill="none"
              stroke="#e4e4e7"
              strokeWidth="3"
              strokeDasharray="6,4"
            />

            {/* Actual spent trajectory curve */}
            <path
              d="M 50 180 Q 200 174 350 115 T 530 80"
              fill="none"
              stroke="#18181b"
              strokeWidth="4.5"
            />

            {/* Projection Forecast line */}
            <path
              d="M 530 80 Q 600 65 680 45 T 780 28"
              fill="none"
              stroke="#d4d4d8"
              strokeWidth="3"
            />

            {/* Data Anchor Points */}
            <circle cx="50" cy="180" r="5" fill="#18181b" />
            <circle cx="205" cy="173" r="5" fill="#18181b" />
            <circle cx="350" cy="115" r="5" fill="#18181b" />
            <circle cx="530" cy="80" r="6" fill="#10b981" /> {/* Current Time Locator */}

            {/* Labels inside SVG */}
            <text x="60" y="175" fill="#a1a1aa" fontSize="9" fontFamily="monospace">Kickoff Q1 24</text>
            <text x="360" y="110" fill="#a1a1aa" fontSize="9" fontFamily="monospace">Structural Milestone Q1 26</text>
            <text x="545" y="85" fill="#10b981" fontSize="9" fontFamily="monospace" fontWeight="bold">Current Point (Q2 2026)</text>
          </svg>

          {/* S-Curve Labels below index map */}
          <div className="absolute bottom-2 left-6 right-6 flex justify-between text-[10px] font-mono text-zinc-400">
            <span>May 2024</span>
            <span>Nov 2024</span>
            <span>May 2025</span>
            <span>Nov 2025</span>
            <span>May 2026 (Live)</span>
            <span>Nov 2026</span>
          </div>

          <div className="absolute top-4 right-4 flex items-center gap-4 bg-white px-3 py-1.5 border border-zinc-200 rounded-lg shadow-sm text-[10px] font-mono text-zinc-400 leading-none">
            <div className="flex items-center gap-1.5">
              <span className="w-3.5 h-[3px] bg-zinc-900 inline-block" />
              <span className="text-zinc-700">Actual Accumulated Spend</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3.5 h-[2px] border-b-2 border-dashed border-zinc-300 inline-block" />
              <span>Target Baseline Projection</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
