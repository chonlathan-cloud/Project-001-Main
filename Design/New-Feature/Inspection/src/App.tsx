/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useState, useEffect } from "react";
import Sidebar from "./components/Sidebar";
import Navbar from "./components/Navbar";
import DashboardView from "./components/DashboardView";
import InspectView from "./components/InspectView";
import DefectsView from "./components/DefectsView";
import ReportView from "./components/ReportView";
import SettingsView from "./components/SettingsView";
import HelpView from "./components/HelpView";
import { ActiveTab, Defect, DefectStatus, DefectSeverity } from "./types";
import { initialDefects, zoneList } from "./data";
import { ClipboardCheck, LayoutDashboard, ShieldAlert, FileText, Settings, HelpCircle, X } from "lucide-react";

export default function App() {
  // Navigation states
  const [activeTab, setActiveTab] = useState<ActiveTab>(ActiveTab.DASHBOARD);
  const [activeZone, setActiveZone] = useState<string>(zoneList[0]);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [inspectorName, setInspectorName] = useState<string>("Jane Doe");
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);

  // Initialize state with localStorage persistence if available, else initialDefects dataset
  const [defects, setDefects] = useState<Defect[]>(() => {
    const saved = localStorage.getItem("rayadee_defects");
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (err) {
        console.error("Parsed error in offline state. Reverting to base seed.", err);
      }
    }
    return initialDefects;
  });

  // Keep state synced with localStorage
  useEffect(() => {
    localStorage.setItem("rayadee_defects", JSON.stringify(defects));
  }, [defects]);

  // Handle adding new custom defects pins to blueprint map
  const handleAddDefect = (newDefect: Omit<Defect, "id">) => {
    const nextNumericId = 103 + defects.length;
    const computedId = `#DF-${nextNumericId}`;

    const completedDefect: Defect = {
      ...newDefect,
      id: computedId
    };

    setDefects((prev) => [completedDefect, ...prev]);
  };

  // Update defect status dynamically (Open, In Progress, Resolved)
  const handleUpdateStatus = (id: string, status: DefectStatus) => {
    setDefects((prev) =>
      prev.map((defect) =>
        defect.id === id ? { ...defect, status } : defect
      )
    );
  };

  // Delete site defect pin from state
  const handleDeleteDefect = (id: string) => {
    setDefects((prev) => prev.filter((defect) => defect.id !== id));
  };

  // Re-seed original mock data
  const handleResetData = () => {
    localStorage.removeItem("rayadee_defects");
    setDefects(initialDefects);
    setActiveTab(ActiveTab.DASHBOARD);
  };

  // Universal Export action handler
  const handleExport = () => {
    if (activeTab === ActiveTab.REPORT) {
      window.print();
    } else {
      const confirmPrint = confirm(
        "Generate & Print Official Inspection PDF?\n\nThis will take you to the Report section configured with crisp PDF formatting ready to print or save."
      );
      if (confirmPrint) {
        setActiveTab(ActiveTab.REPORT);
        // Delay printing slightly to let tab mount fully
        setTimeout(() => {
          window.print();
        }, 300);
      }
    }
  };

  const handleNewInspectionTrigger = () => {
    const newRegionName = prompt(
      "Create New Inspection Wing / Zone:\nInput descriptive level designation:",
      `Level 4 - West Core`
    );
    if (newRegionName && newRegionName.trim()) {
      alert(`Newly created Zone: "${newRegionName}" is now active!`);
      // Add a dummy blueprint item to get started quickly
      handleAddDefect({
        description: "Initial walkthrough inspection item",
        category: "Architectural",
        severity: defects[0]?.severity || DefectSeverity.MINOR,
        responsibleParty: "General Trade Subcontractor",
        dueDate: new Date(Date.now() + 6 * 24 * 60 * 60 * 1000).toISOString().split("T")[0],
        status: DefectStatus.OPEN,
        zone: newRegionName,
        x: 50,
        y: 50,
        details: "Walldrop calibration indicator."
      });
      setActiveZone(newRegionName);
      setActiveTab(ActiveTab.INSPECT);
    }
  };

  // Helper renderer to pivot views
  const renderTabContent = () => {
    switch (activeTab) {
      case ActiveTab.INSPECT:
        return (
          <InspectView
            defects={defects}
            addDefect={handleAddDefect}
            activeZone={activeZone}
            setActiveZone={setActiveZone}
          />
        );
      case ActiveTab.DASHBOARD:
        return <DashboardView defects={defects} setActiveTab={setActiveTab} />;
      case ActiveTab.DEFECTS:
        return (
          <DefectsView
            defects={defects}
            updateDefectStatus={handleUpdateStatus}
            deleteDefect={handleDeleteDefect}
            searchQuery={searchQuery}
            setSearchQuery={setSearchQuery}
          />
        );
      case ActiveTab.REPORT:
        return <ReportView defects={defects} />;
      case ActiveTab.SETTINGS:
        return (
          <SettingsView
            inspectorName={inspectorName}
            setInspectorName={setInspectorName}
            onResetData={handleResetData}
          />
        );
      case ActiveTab.HELP:
        return <HelpView />;
      default:
        return <DashboardView defects={defects} setActiveTab={setActiveTab} />;
    }
  };

  return (
    <div className="flex min-h-screen bg-brand-background text-brand-on-background relative overflow-x-hidden select-none">
      {/* 1. Left Sidebar Navigation Panel (Main Desktop Layout) */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={(tab) => {
          setActiveTab(tab);
          setMobileMenuOpen(false);
        }}
        onNewInspectionClick={handleNewInspectionTrigger}
      />

      {/* Mobile Drawer Slide Navigation sidebar */}
      {mobileMenuOpen && (
        <div className="no-print fixed inset-0 z-40 flex md:hidden">
          {/* Overlay mask */}
          <div
            className="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity duration-300"
            onClick={() => setMobileMenuOpen(false)}
          />
          {/* Menu Drawer Content */}
          <div className="relative flex w-64 max-w-xs flex-col bg-[#fdf9f5] border-r border-brand-border-subtle p-5 animate-slide-right text-brand-on-background">
            <button
              onClick={() => setMobileMenuOpen(false)}
              className="absolute top-4 right-4 text-brand-on-surface-variant hover:text-brand-on-background"
            >
              <X className="w-5 h-5 bg-brand-surface rounded p-1" />
            </button>

            {/* Profile */}
            <div className="pt-2 pb-6 border-b border-brand-border-subtle mb-4">
              <div className="flex items-center gap-3">
                <img
                  alt="Site Manager profile avatar representation"
                  className="w-10 h-10 rounded-full object-cover"
                  src="https://lh3.googleusercontent.com/aida-public/AB6AXuApaSFHHD8x2qDbMCWXvxo_DIg8ORNoXZ4ypnqqfG2847ibuKliJEdZvKGq6764opsYC7Nt25c80QuU6nzauT07EYYOuq9ZlGMyDiZOuE_UEy1iIpiCVeDNSeMStgXvh0eqHYHa4FwbpttqzT7dz4iPLqaIUTydeNswzuNmVfyJ08vUIDSLKsiLqzqQ3rYLLJHRtWMnzS4MipICGdFbohFf53PPaP5kAdsx4JqC60kdJOA5Aji8QAsalpwfJ7HuI8Xj8XrvUHv2cp8"
                />
                <div>
                  <h1 className="font-extrabold text-sm text-brand-primary">Rayadee Defect</h1>
                  <p className="text-[10px] text-brand-on-surface-variant font-medium">Site Admin</p>
                </div>
              </div>
            </div>

            {/* Links */}
            <nav className="space-y-1.5 flex-1 select-none">
              <button
                onClick={() => {
                  setActiveTab(ActiveTab.DASHBOARD);
                  setMobileMenuOpen(false);
                }}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-xs font-bold text-left ${
                  activeTab === ActiveTab.DASHBOARD ? "bg-brand-surface-container text-brand-primary" : "text-brand-on-surface-variant"
                }`}
              >
                <LayoutDashboard className="w-4 h-4" />
                Dashboard
              </button>
              <button
                onClick={() => {
                  setActiveTab(ActiveTab.INSPECT);
                  setMobileMenuOpen(false);
                }}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-xs font-bold text-left ${
                  activeTab === ActiveTab.INSPECT ? "bg-brand-surface-container text-brand-primary" : "text-brand-on-surface-variant"
                }`}
              >
                <ClipboardCheck className="w-4 h-4" />
                Inspect Map
              </button>
              <button
                onClick={() => {
                  setActiveTab(ActiveTab.DEFECTS);
                  setMobileMenuOpen(false);
                }}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-xs font-bold text-left ${
                  activeTab === ActiveTab.DEFECTS ? "bg-brand-surface-container text-brand-primary" : "text-brand-on-surface-variant"
                }`}
              >
                <ShieldAlert className="w-4 h-4" />
                Defects Catalog
              </button>
              <button
                onClick={() => {
                  setActiveTab(ActiveTab.REPORT);
                  setMobileMenuOpen(false);
                }}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-xs font-bold text-left ${
                  activeTab === ActiveTab.REPORT ? "bg-brand-surface-container text-brand-primary" : "text-brand-on-surface-variant"
                }`}
              >
                <FileText className="w-4 h-4" />
                Report Verifier
              </button>
              <div className="h-px bg-brand-border-subtle my-2" />
              <button
                onClick={() => {
                  setActiveTab(ActiveTab.SETTINGS);
                  setMobileMenuOpen(false);
                }}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-xs font-bold text-left ${
                  activeTab === ActiveTab.SETTINGS ? "bg-brand-surface-container text-brand-primary" : "text-brand-on-surface-variant"
                }`}
              >
                <Settings className="w-4 h-4" />
                Settings
              </button>
              <button
                onClick={() => {
                  setActiveTab(ActiveTab.HELP);
                  setMobileMenuOpen(false);
                }}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-xs font-bold text-left ${
                  activeTab === ActiveTab.HELP ? "bg-brand-surface-container text-brand-primary" : "text-brand-on-surface-variant"
                }`}
              >
                <HelpCircle className="w-4 h-4" />
                Technical Help
              </button>
            </nav>
          </div>
        </div>
      )}

      {/* 2. Main Content Stage Container (Offset on Desktop left offset width) */}
      <div className="flex-1 flex flex-col md:pl-[260px] min-h-screen overflow-x-hidden relative">
        {/* Top Header Navigation controls bar */}
        <Navbar
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
          onExportClick={handleExport}
          onToggleMobileMenu={() => setMobileMenuOpen(true)}
        />

        {/* Dynamic content scroll frame area */}
        <main className="flex-1 overflow-y-auto px-6 py-6 mt-16 bg-brand-background custom-scrollbar">
          <div className="max-w-6xl mx-auto">
            {renderTabContent()}
          </div>
        </main>
      </div>
    </div>
  );
}
