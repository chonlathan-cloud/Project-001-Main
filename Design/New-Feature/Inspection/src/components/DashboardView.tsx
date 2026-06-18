/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import {
  TrendingUp,
  Clock,
  AlertCircle,
  AlertTriangle,
  CheckCircle,
  MoreVertical,
  ArrowDown,
  ArrowUp,
  Minus,
  Award,
  ArrowRight
} from "lucide-react";
import { Defect, DefectStatus, DefectSeverity, ActiveTab } from "../types";

interface DashboardViewProps {
  defects: Defect[];
  setActiveTab: (tab: ActiveTab) => void;
}

export default function DashboardView({ defects, setActiveTab }: DashboardViewProps) {
  // Dynamic aggregations syncing with state
  const unclosedList = defects.filter((d) => d.status !== DefectStatus.RESOLVED);
  const criticalUnclosed = unclosedList.filter((d) => d.severity === DefectSeverity.CRITICAL);
  const majorUnclosed = unclosedList.filter((d) => d.severity === DefectSeverity.MAJOR);
  const minorUnclosed = unclosedList.filter((d) => d.severity === DefectSeverity.MINOR);
  const cosmeticUnclosed = unclosedList.filter((d) => d.severity === DefectSeverity.COSMETIC);

  const resolvedCount = defects.filter((d) => d.status === DefectStatus.RESOLVED).length;

  // Reactivity offsets from initial design state
  const dynamicTotal = 1248 + (defects.length - 5);
  const dynamicUnclosed = Math.max(0, 342 + unclosedList.length - 4);
  const dynamicCritical = Math.max(0, 18 + criticalUnclosed.length - 2);
  const dynamicMajor = Math.max(0, 84 + majorUnclosed.length - 1);
  const dynamicReadiness = Math.min(100, Math.max(0, Math.round(82 + (resolvedCount * 2.5))));

  // Severities list
  const severitiesData = [
    {
      name: "Critical",
      count: dynamicCritical,
      percentage: "1.4%",
      color: "bg-brand-error",
      textColor: "text-brand-error",
      trend: "down"
    },
    {
      name: "Major",
      count: dynamicMajor,
      percentage: "6.7%",
      color: "bg-brand-secondary",
      textColor: "text-brand-secondary",
      trend: "up"
    },
    {
      name: "Minor",
      count: Math.max(0, 820 + minorUnclosed.length - 1),
      percentage: "65.7%",
      color: "bg-brand-outline-variant",
      textColor: "text-brand-outline",
      trend: "neutral"
    },
    {
      name: "Cosmetic",
      count: Math.max(0, 326 + cosmeticUnclosed.length - 1),
      percentage: "26.1%",
      color: "bg-brand-surface-container-highest",
      textColor: "text-brand-primary",
      trend: "up"
    }
  ];

  // Category percentages
  const categoriesData = [
    { name: "Architectural", percentage: 45, colorClass: "bg-brand-primary" },
    { name: "Electrical", percentage: 25, colorClass: "bg-brand-secondary-fixed-dim" },
    { name: "Plumbing", percentage: 15, colorClass: "bg-brand-outline" },
    { name: "Mechanical / HVAC", percentage: 10, colorClass: "bg-brand-tertiary-container" },
    { name: "Structural", percentage: 5, colorClass: "bg-brand-outline-variant" }
  ];

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header Title */}
      <div>
        <h2 className="text-3xl font-bold tracking-tight text-brand-on-background">
          Dashboard Overview
        </h2>
        <p className="text-sm font-medium text-brand-on-surface-variant mt-1">
          High-level project metrics and defect tracking.
        </p>
      </div>

      {/* Metrics Row (5 Cards) */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {/* Card 1 */}
        <div className="bg-brand-surface border border-brand-border-subtle rounded-lg p-5 hover:shadow-md transition-all">
          <div className="flex justify-between items-start mb-2">
            <span className="text-xs font-bold uppercase tracking-wider text-brand-on-surface-variant">
              Total Defects
            </span>
            <TrendingUp className="w-5 h-5 text-brand-outline" />
          </div>
          <div className="text-3xl font-bold text-brand-on-background tabular-nums">
            {dynamicTotal.toLocaleString()}
          </div>
          <div className="mt-2 flex items-center gap-1 text-xs text-brand-primary font-medium">
            <TrendingUp className="w-3.5 h-3.5" />
            <span>+12% this week</span>
          </div>
        </div>

        {/* Card 2 */}
        <div className="bg-brand-surface border border-brand-border-subtle rounded-lg p-5 hover:shadow-md transition-all">
          <div className="flex justify-between items-start mb-2">
            <span className="text-xs font-bold uppercase tracking-wider text-brand-on-surface-variant">
              Unclosed
            </span>
            <Clock className="w-5 h-5 text-brand-outline" />
          </div>
          <div className="text-3xl font-bold text-brand-on-background tabular-nums">
            {dynamicUnclosed.toLocaleString()}
          </div>
          <div className="mt-2 text-xs font-medium text-brand-on-surface-variant">
            Across 12 active zones
          </div>
        </div>

        {/* Card 3 */}
        <div className="bg-brand-surface border border-brand-border-subtle rounded-lg p-5 hover:shadow-md transition-all border-l-4 border-l-brand-error">
          <div className="flex justify-between items-start mb-2">
            <span className="text-xs font-bold uppercase tracking-wider text-brand-error">
              Critical
            </span>
            <AlertCircle className="w-5 h-5 text-brand-error" />
          </div>
          <div className="text-3xl font-bold text-brand-error tabular-nums">
            {dynamicCritical}
          </div>
          <div className="mt-2 flex items-center gap-1 text-xs font-medium text-brand-error">
            <span>Requires immediate action</span>
          </div>
        </div>

        {/* Card 4 */}
        <div className="bg-brand-surface border border-brand-border-subtle rounded-lg p-5 hover:shadow-md transition-all border-l-4 border-l-brand-secondary">
          <div className="flex justify-between items-start mb-2">
            <span className="text-xs font-bold uppercase tracking-wider text-brand-secondary">
              Major
            </span>
            <AlertTriangle className="w-5 h-5 text-brand-secondary" />
          </div>
          <div className="text-3xl font-bold text-brand-on-background tabular-nums">
            {dynamicMajor}
          </div>
          <div className="mt-2 text-xs font-medium text-brand-on-surface-variant">
            Pending contractor review
          </div>
        </div>

        {/* Card 5 */}
        <div className="bg-brand-surface border border-brand-border-subtle rounded-lg p-5 hover:shadow-md transition-all grid-cols-span-2 sm:grid-cols-span-1">
          <div className="flex justify-between items-start mb-2">
            <span className="text-xs font-bold uppercase tracking-wider text-brand-on-surface-variant">
              Readiness
            </span>
            <CheckCircle className="w-5 h-5 text-brand-primary" />
          </div>
          <div className="text-3xl font-bold text-brand-on-background tabular-nums">
            {dynamicReadiness}%
          </div>
          {/* Progress bar */}
          <div className="mt-3 w-full bg-brand-surface-container-high rounded-full h-1.5 overflow-hidden">
            <div
              className="bg-brand-primary h-1.5 rounded-full transition-all duration-500"
              style={{ width: `${dynamicReadiness}%` }}
            ></div>
          </div>
        </div>
      </div>

      {/* Main Grid: Severities and Contractors */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Severity Breakdown Table */}
        <div className="bg-brand-surface border border-brand-border-subtle rounded-lg flex flex-col shadow-xs">
          <div className="p-5 border-b border-brand-border-subtle flex justify-between items-center bg-brand-surface-container-low rounded-t-lg">
            <h3 className="text-lg font-bold text-brand-on-background">
              Severity Breakdown
            </h3>
            <button className="text-brand-primary hover:bg-brand-surface-container-high p-1 rounded-full transition-colors cursor-pointer">
              <MoreVertical className="w-4 h-4" />
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead className="bg-brand-surface-container-low border-b border-brand-border-subtle text-xs font-bold uppercase tracking-wider text-brand-on-surface-variant">
                <tr>
                  <th className="py-3.5 px-5 font-bold">Severity</th>
                  <th className="py-3.5 px-5 font-bold text-right">Count</th>
                  <th className="py-3.5 px-5 font-bold text-right">% of Total</th>
                  <th className="py-3.5 px-5 font-bold">Trend</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-brand-border-subtle text-sm text-brand-on-background">
                {severitiesData.map((item) => (
                  <tr
                    key={item.name}
                    className="hover:bg-brand-surface-container-lowest transition-colors h-[52px]"
                  >
                    <td className="py-3 px-5 flex items-center gap-3 font-semibold">
                      <div className={`w-2.5 h-2.5 rounded-full ${item.color}`} />
                      {item.name}
                    </td>
                    <td className="py-3 px-5 text-right font-medium tabular-nums">
                      {item.count.toLocaleString()}
                    </td>
                    <td className="py-3 px-5 text-right font-medium text-brand-on-surface-variant tabular-nums">
                      {item.percentage}
                    </td>
                    <td className="py-3 px-5">
                      {item.trend === "down" && (
                        <ArrowDown className="w-4 h-4 text-brand-error inline" />
                      )}
                      {item.trend === "up" && (
                        <ArrowUp className="w-4 h-4 text-brand-primary inline" />
                      )}
                      {item.trend === "neutral" && (
                        <Minus className="w-4 h-4 text-brand-outline inline" />
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Top Contractors Section */}
        <div className="bg-brand-surface border border-brand-border-subtle rounded-lg flex flex-col shadow-xs">
          <div className="p-5 border-b border-brand-border-subtle flex justify-between items-center bg-brand-surface-container-low rounded-t-lg">
            <h3 className="text-lg font-bold text-brand-on-background">
              Top Contractors by Open Defects
            </h3>
            <button
              onClick={() => setActiveTab(ActiveTab.DEFECTS)}
              className="text-xs font-semibold text-brand-on-surface-variant hover:text-brand-primary transition-colors cursor-pointer"
            >
              View All
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead className="bg-brand-surface-container-low border-b border-brand-border-subtle text-xs font-bold uppercase tracking-wider text-brand-on-surface-variant">
                <tr>
                  <th className="py-3.5 px-5 font-bold">Contractor</th>
                  <th className="py-3.5 px-5 font-bold text-right">Open</th>
                  <th className="py-3.5 px-5 font-bold text-right">Avg Days</th>
                  <th className="py-3.5 px-5 font-bold">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-brand-border-subtle text-sm text-brand-on-background">
                <tr className="hover:bg-brand-surface-container-lowest transition-colors h-[52px]">
                  <td className="py-3 px-5 font-semibold">Apex Builders Ltd.</td>
                  <td className="py-3 px-5 text-right text-brand-error font-bold tabular-nums">
                    42
                  </td>
                  <td className="py-3 px-5 text-right font-medium text-brand-on-surface-variant tabular-nums">
                    14.5
                  </td>
                  <td className="py-3 px-5">
                    <span className="inline-block px-2.5 py-1 bg-brand-error-container text-brand-on-error-container text-[10px] uppercase font-bold tracking-wider rounded-md">
                      At Risk
                    </span>
                  </td>
                </tr>
                <tr className="hover:bg-brand-surface-container-lowest transition-colors h-[52px]">
                  <td className="py-3 px-5 font-semibold">Elevate MEP</td>
                  <td className="py-3 px-5 text-right font-bold text-brand-on-background tabular-nums">
                    28
                  </td>
                  <td className="py-3 px-5 text-right font-medium text-brand-on-surface-variant tabular-nums">
                    8.2
                  </td>
                  <td className="py-3 px-5">
                    <span className="inline-block px-2.5 py-1 bg-brand-surface-container-high text-brand-on-surface-variant text-[10px] uppercase font-bold tracking-wider rounded-md">
                      Monitor
                    </span>
                  </td>
                </tr>
                <tr className="hover:bg-brand-surface-container-lowest transition-colors h-[52px]">
                  <td className="py-3 px-5 font-semibold">Structura Co.</td>
                  <td className="py-3 px-5 text-right font-bold text-brand-on-background tabular-nums">
                    15
                  </td>
                  <td className="py-3 px-5 text-right font-medium text-brand-on-surface-variant tabular-nums">
                    4.1
                  </td>
                  <td className="py-3 px-5">
                    <span className="inline-block px-2.5 py-1 bg-brand-primary-container text-brand-on-primary text-[10px] uppercase font-bold tracking-wider rounded-md opacity-90">
                      On Track
                    </span>
                  </td>
                </tr>
                <tr className="hover:bg-brand-surface-container-lowest transition-colors h-[52px]">
                  <td className="py-3 px-5 font-semibold">Prime Finishes</td>
                  <td className="py-3 px-5 text-right font-bold text-brand-on-background tabular-nums">
                    12
                  </td>
                  <td className="py-3 px-5 text-right font-medium text-brand-on-surface-variant tabular-nums">
                    5.0
                  </td>
                  <td className="py-3 px-5">
                    <span className="inline-block px-2.5 py-1 bg-brand-primary-container text-brand-on-primary text-[10px] uppercase font-bold tracking-wider rounded-md opacity-90">
                      On Track
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Categories and Handover Status Card */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Category Breakdown list */}
        <div className="bg-brand-surface border border-brand-border-subtle rounded-lg flex flex-col p-6 shadow-xs">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-lg font-bold text-brand-on-background">
              Defects by Category
            </h3>
          </div>
          <div className="space-y-4">
            {categoriesData.map((category) => (
              <div key={category.name}>
                <div className="flex justify-between text-xs font-semibold mb-1">
                  <span className="text-brand-on-background">{category.name}</span>
                  <span className="text-brand-on-surface-variant">
                    {category.percentage}%
                  </span>
                </div>
                <div className="w-full bg-brand-surface-container-high rounded-full h-2 overflow-hidden">
                  <div
                    className={`${category.colorClass} h-2 rounded-full transition-all duration-500`}
                    style={{ width: `${category.percentage}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Handover Status Card visualizer */}
        <div className="bg-brand-surface border border-brand-border-subtle rounded-lg flex flex-col p-6 justify-between bg-linear-to-br from-brand-surface to-brand-surface-container-low shadow-xs">
          <div className="flex items-start gap-4 mb-4">
            <div className="p-3 bg-brand-primary-container text-brand-on-primary rounded-full shadow-xs">
              <Award className="w-8 h-8 text-brand-on-primary" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-brand-on-background">
                Handover Status
              </h3>
              <p className="text-xs text-brand-on-surface-variant mt-0.5">
                Based on current defect closure velocity.
              </p>
            </div>
          </div>

          <div className="my-4 p-4 border border-brand-border-subtle bg-brand-background rounded-lg text-center shadow-xs">
            <span className="block text-[11px] font-bold tracking-wider text-brand-secondary uppercase mb-1">
              Projected Readiness Date
            </span>
            <span className="block text-2xl font-bold text-brand-on-background">
              Oct 24, 2024
            </span>
            <span className="block text-xs font-semibold text-brand-error mt-2">
              {dynamicCritical > 0
                ? `Delayed by 4 days due to ${dynamicCritical} open critical items.`
                : "Awaiting final handover inspection approval."}
            </span>
          </div>

          <div className="flex justify-end pt-2">
            <button
              onClick={() => setActiveTab(ActiveTab.REPORT)}
              className="px-5 py-2.5 bg-brand-primary-container text-brand-on-primary font-bold text-xs rounded-lg hover:bg-brand-surface-tint transition-all shadow-xs flex items-center gap-1.5 cursor-pointer active:scale-95"
            >
              Generate Full Report
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
