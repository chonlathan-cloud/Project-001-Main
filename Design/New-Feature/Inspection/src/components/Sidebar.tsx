/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import {
  ClipboardCheck,
  LayoutDashboard,
  ShieldAlert,
  FileText,
  Settings,
  HelpCircle,
  Plus
} from "lucide-react";
import { ActiveTab } from "../types";

interface SidebarProps {
  activeTab: ActiveTab;
  setActiveTab: (tab: ActiveTab) => void;
  onNewInspectionClick: () => void;
}

export default function Sidebar({ activeTab, setActiveTab, onNewInspectionClick }: SidebarProps) {
  const mainNavItems = [
    { id: ActiveTab.INSPECT, label: "Inspect", icon: ClipboardCheck },
    { id: ActiveTab.DASHBOARD, label: "Dashboard", icon: LayoutDashboard },
    { id: ActiveTab.DEFECTS, label: "Defects", icon: ShieldAlert },
    { id: ActiveTab.REPORT, label: "Report", icon: FileText },
  ];

  const bottomNavItems = [
    { id: ActiveTab.SETTINGS, label: "Settings", icon: Settings },
    { id: ActiveTab.HELP, label: "Help", icon: HelpCircle },
  ];

  return (
    <nav className="no-print hidden md:flex bg-brand-surface text-brand-primary font-medium fixed left-0 top-0 h-full w-[260px] border-r border-brand-border-subtle flex-col py-4 z-20 shadow-xs">
      {/* Header Profile Section */}
      <div className="px-6 py-2 mb-4">
        <div className="flex items-center gap-3 mb-5">
          <img
            alt="Site Manager"
            className="w-10 h-10 rounded-full object-cover border border-brand-border-subtle"
            referrerPolicy="no-referrer"
            src="https://lh3.googleusercontent.com/aida-public/AB6AXuApaSFHHD8x2qDbMCWXvxo_DIg8ORNoXZ4ypnqqfG2847ibuKliJEdZvKGq6764opsYC7Nt25c80QuU6nzauT07EYYOuq9ZlGMyDiZOuE_UEy1iIpiCVeDNSeMStgXvh0eqHYHa4FwbpttqzT7dz4iPLqaIUTydeNswzuNmVfyJ08vUIDSLKsiLqzqQ3rYLLJHRtWMnzS4MipICGdFbohFf53PPaP5kAdsx4JqC60kdJOA5Aji8QAsalpwfJ7HuI8Xj8XrvUHv2cp8"
          />
          <div>
            <h1 className="font-semibold text-base text-brand-primary tracking-tight leading-tight">
              Rayadee Defect
            </h1>
            <p className="text-xs text-brand-on-surface-variant">Site Management</p>
          </div>
        </div>

        {/* Action Button */}
        <button
          onClick={onNewInspectionClick}
          className="w-full bg-brand-primary-container text-brand-on-primary font-semibold text-xs py-2 px-4 rounded hover:bg-brand-surface-tint active:scale-[0.98] transition-all flex items-center justify-center gap-2 shadow-xs cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          New Inspection
        </button>
      </div>

      {/* Main Navigation Links */}
      <div className="flex-1 px-4 space-y-1">
        {mainNavItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-semibold transition-all cursor-pointer text-left ${
                isActive
                  ? "text-brand-primary border-l-4 border-brand-primary bg-brand-surface-container-low"
                  : "text-brand-on-surface-variant hover:bg-brand-surface-container-highest hover:text-brand-on-surface"
              }`}
            >
              <Icon className={`w-5 h-5 ${isActive ? "text-brand-primary" : "text-brand-outline"}`} />
              {item.label}
            </button>
          );
        })}
      </div>

      {/* Custom Footer Navigation Links */}
      <div className="px-4 pb-2 space-y-1 mt-auto border-t border-brand-border-subtle pt-4">
        {bottomNavItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-semibold transition-all cursor-pointer text-left ${
                isActive
                  ? "text-brand-primary border-l-4 border-brand-primary bg-brand-surface-container-low"
                  : "text-brand-on-surface-variant hover:bg-brand-surface-container-highest hover:text-brand-on-surface"
              }`}
            >
              <Icon className="w-5 h-5 text-brand-outline" />
              {item.label}
            </button>
          );
        })}
      </div>
    </nav>
  );
}
