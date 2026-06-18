/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { Search, Bell, Grid, Menu } from "lucide-react";
import { ActiveTab } from "../types";

interface NavbarProps {
  activeTab: ActiveTab;
  setActiveTab: (tab: ActiveTab) => void;
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  onExportClick: () => void;
  onToggleMobileMenu?: () => void;
}

export default function Navbar({
  activeTab,
  setActiveTab,
  searchQuery,
  setSearchQuery,
  onExportClick,
  onToggleMobileMenu
}: NavbarProps) {
  return (
    <header className="no-print bg-brand-background dark:bg-brand-on-background fixed top-0 right-0 left-0 md:left-[260px] h-16 border-b border-brand-border-subtle flex justify-between items-center px-6 z-10">
      {/* Left: Mobile menu toggle + Title + Top navigation links */}
      <div className="flex items-center gap-6">
        {onToggleMobileMenu && (
          <button
            onClick={onToggleMobileMenu}
            className="md:hidden p-2 -ml-2 text-brand-on-surface-variant hover:text-brand-primary"
          >
            <Menu className="w-5 h-5" />
          </button>
        )}
        <span className="md:hidden font-bold text-lg text-brand-primary">
          Rayadee Defect
        </span>

        {/* Global Navigation links (Project Overview, Team, Timeline) */}
        <nav className="hidden lg:flex gap-6 items-center">
          <button
            onClick={() => alert("Project Overview Info:\n- Contractor Count: 4\n- Total Zones: 12\n- Next Handover Phase: Oct 2024\n- Phase 2 status: active")}
            className="text-brand-on-surface-variant hover:text-brand-primary transition-colors cursor-pointer text-sm font-medium py-5 hover:-translate-y-0.5"
          >
            Project Overview
          </button>
          <button
            onClick={() => alert("Project Team assigned:\n- Jane Doe (Site Inspection Lead)\n- John Smith (MEP Lead)\n- Robert Garcia (General Foreman)\n- Apex Structural Team")}
            className="text-brand-on-surface-variant hover:text-brand-primary transition-colors cursor-pointer text-sm font-medium py-5 hover:-translate-y-0.5"
          >
            Team
          </button>
          <button
            onClick={() => alert("Inspection Milestone Timeline:\nP1: Completed (Aug 2023)\nP2: In Progress (Oct-Nov 2023)\nP3: Handover Audit (Oct 24, 2024)")}
            className="text-brand-on-surface-variant hover:text-brand-primary transition-colors cursor-pointer text-sm font-medium py-5 hover:-translate-y-0.5"
          >
            Timeline
          </button>
        </nav>
      </div>

      {/* Middle/Right: Search bar, settings button, and notification controls */}
      <div className="flex items-center gap-4">
        {/* Dynamic Search Proxy */}
        <div className="relative flex items-center">
          <Search className="absolute left-3 w-4 h-4 text-brand-outline" />
          <input
            type="text"
            className="pl-10 pr-4 py-1.5 border border-brand-border-subtle rounded-lg bg-brand-surface focus:ring-2 focus:ring-brand-primary focus:border-brand-primary outline-hidden text-sm w-44 sm:w-64 text-brand-on-surface transition-all placeholder:text-brand-outline"
            placeholder="Search defects..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              if (activeTab !== ActiveTab.DEFECTS && activeTab !== ActiveTab.INSPECT) {
                // Instantly pivot user to defects view if they start searching
                setActiveTab(ActiveTab.DEFECTS);
              }
            }}
          />
        </div>

        {/* Action button triggers Settings panel */}
        <button
          onClick={() => setActiveTab(ActiveTab.SETTINGS)}
          className="hidden md:block px-4 py-1.5 border border-brand-secondary text-brand-secondary font-semibold text-xs rounded-lg hover:bg-brand-surface-container-low transition-colors cursor-pointer"
        >
          Project Settings
        </button>

        {/* Export Action */}
        <button
          onClick={onExportClick}
          className="bg-brand-primary text-brand-on-primary px-4 py-1.5 rounded-lg text-xs font-semibold hover:opacity-95 transition-opacity flex items-center gap-2 cursor-pointer active:scale-95"
        >
          Export
        </button>

        {/* Notifications and Profile */}
        <div className="flex items-center gap-2 border-l border-brand-border-subtle pl-4">
          <button
            onClick={() => alert("Notifications Summary:\n- 3 New critical defects found today.\n- 5 Outstanding items over 10 days due.\n- Elevate MEP has updated 3 contractor responses.")}
            className="p-1.5 text-brand-on-surface-variant hover:text-brand-primary hover:bg-brand-surface-container-low rounded-full transition-all cursor-pointer relative"
          >
            <Bell className="w-5 h-5" />
            <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-brand-error"></span>
          </button>
          
          <button
            className="p-1.5 text-brand-on-surface-variant hover:text-brand-primary hover:bg-brand-surface-container-low rounded-full transition-all cursor-pointer"
            onClick={() => alert("Rayadee Defect Management Suite. Current active site session: Block A.")}
          >
            <Grid className="w-5 h-5" />
          </button>

          <img
            alt="User profile avatar"
            className="w-8 h-8 rounded-full border border-brand-border-subtle cursor-pointer transition-transform hover:scale-105"
            referrerPolicy="no-referrer"
            onClick={() => setActiveTab(ActiveTab.SETTINGS)}
            src="https://lh3.googleusercontent.com/aida-public/AB6AXuB8r9egZ2XNUhkzNt8pNzwpLmNfu1cintq364N0fMvoOfGTZpOBS-a22XacD6w9Xq7wJh5CHr8mRjuFA4oUGRRDuaw3P0L0JAI7qCHbMh2ID_etZ7n8iY42GENU4OSgtb9KeiV9FdLjiuAO2K3q9yloA9VhQf5yBURaKWXVKhwxLO4lusYfOrYycpa72e6ymEb15iu4i46g8Rf50U9CS8yVPqMTsMYZ21izlaNrtiyvK-uvW26nEgbJm2w4JffOas0alsRcvLLDHvI"
          />
        </div>
      </div>
    </header>
  );
}
