/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useState } from "react";
import { Printer, MapPin, Download, FileText, CheckCircle } from "lucide-react";
import { Defect, DefectStatus, ReportTab } from "../types";

interface ReportViewProps {
  defects: Defect[];
}

export default function ReportView({ defects }: ReportViewProps) {
  const [activeReportTab, setActiveReportTab] = useState<ReportTab>(ReportTab.CLIENT);

  // Filter defects for the current report (e.g., active ones or all)
  const activeDefects = defects.filter((d) => d.status !== DefectStatus.RESOLVED);

  const getReportTabLabel = () => {
    switch (activeReportTab) {
      case ReportTab.CLIENT:
        return "Client Summary Report";
      case ReportTab.CONTRACTOR:
        return "Contractor Trade Defect Action List";
      default:
        return "Management Executive Handover Overview";
    }
  };

  return (
    <div className="space-y-6 animate-fade-in pb-10">
      {/* Report Switch Tabs (No Print) */}
      <div className="no-print border-b border-brand-border-subtle flex gap-8 pb-1">
        <button
          onClick={() => setActiveReportTab(ReportTab.CLIENT)}
          className={`pb-2 text-sm font-bold transition-all cursor-pointer ${
            activeReportTab === ReportTab.CLIENT
              ? "text-brand-primary border-b-2 border-brand-primary"
              : "text-brand-on-surface-variant hover:text-brand-primary"
          }`}
        >
          Client Report
        </button>
        <button
          onClick={() => setActiveReportTab(ReportTab.CONTRACTOR)}
          className={`pb-2 text-sm font-bold transition-all cursor-pointer ${
            activeReportTab === ReportTab.CONTRACTOR
              ? "text-brand-primary border-b-2 border-brand-primary"
              : "text-brand-on-surface-variant hover:text-brand-primary"
          }`}
        >
          Contractor Report
        </button>
        <button
          onClick={() => setActiveReportTab(ReportTab.MANAGEMENT)}
          className={`pb-2 text-sm font-bold transition-all cursor-pointer ${
            activeReportTab === ReportTab.MANAGEMENT
              ? "text-brand-primary border-b-2 border-brand-primary"
              : "text-brand-on-surface-variant hover:text-brand-primary"
          }`}
        >
          Management Report
        </button>
      </div>

      {/* Printable Report Wrapper */}
      <div className="space-y-6">
        {/* Print Header Action Row (No Print) */}
        <div className="no-print flex justify-between items-center bg-[#f5efe9] p-4 rounded-lg border border-brand-border-subtle">
          <span className="text-xs font-bold text-brand-primary flex items-center gap-2">
            <Printer className="w-4 h-4 text-brand-primary shrink-0" />
            Report is optimized for physical/PDF print output (Ctrl + P / Cmd + P)
          </span>
          <button
            onClick={() => window.print()}
            className="flex items-center gap-2 bg-brand-primary text-brand-on-primary font-bold text-xs px-4 py-2 rounded hover:opacity-95 cursor-pointer ml-4 shadow-xs"
          >
            <Printer className="w-4 h-4" />
            Print Report
          </button>
        </div>

        {/* Report Main Header */}
        <div className="bg-brand-surface p-6 rounded-lg border border-brand-border-subtle flex flex-col md:flex-row justify-between items-start gap-4 shadow-xs">
          <div>
            <h2 className="text-2xl font-black text-brand-on-surface leading-tight tracking-tight">
              Phase 2 Handover Inspection
            </h2>
            <p className="text-sm font-semibold text-brand-on-surface-variant mt-1.5 uppercase tracking-wide">
              {getReportTabLabel()}
            </p>
            <div className="mt-5 flex flex-wrap gap-5 text-xs font-semibold text-brand-on-surface-variant">
              <div>
                <span className="font-bold text-brand-outline">DATE:</span> Oct 24, 2023
              </div>
              <div>
                <span className="font-bold text-brand-outline">INSPECTOR:</span> Jane Doe
              </div>
              <div>
                <span className="font-bold text-brand-outline">LOCATION:</span> Block A, Level 4
              </div>
              <div>
                <span className="font-bold text-brand-outline">PHASE:</span> Handover Verification
              </div>
            </div>
          </div>
          <div className="self-stretch sm:self-auto flex items-center justify-center">
            <div className="flex flex-col items-center px-6 py-4 bg-brand-error-container rounded-lg border border-brand-error/20 shadow-xs text-center">
              <span className="text-3xl font-black text-brand-error leading-none mb-1">
                {activeDefects.length}
              </span>
              <span className="text-[10px] font-bold text-brand-on-error-container tracking-wider uppercase">
                Open Defects
              </span>
            </div>
          </div>
        </div>

        {/* Floor Plan Overview Blueprint section */}
        <div className="bg-brand-surface p-6 rounded-lg border border-brand-border-subtle shadow-xs">
          <h3 className="text-base font-extrabold text-brand-on-surface mb-3 flex items-center gap-2">
            <MapPin className="w-4 h-4 text-brand-primary" />
            Floor Plan Overview
          </h3>
          <div className="w-full h-80 bg-brand-surface-variant rounded-lg border border-brand-border-subtle relative overflow-hidden flex items-center justify-center">
            <img
              alt="Architectural Blueprint Drawing Layout"
              className="w-full h-full object-cover opacity-60 mix-blend-multiply"
              referrerPolicy="no-referrer"
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuDj6grcZ2ThzF94Do4a1dQ8xEJYjeCpoxRkoIsavRg4sjeNLr1u54S2e_z9pLbROJzomq3MJIG_eotbt2oYeQdjYFHAED0JD7BaFiInMH6obBnQ6s2q7OhSRTITOFhwpKrFkJjsGx7aDt1SPELVC0tJhKJ6j36wr3BzlL3Xg27gBiYOvy5HEHb1yZs8yajmDYf7mCiZ7_uaFiVvW2H6_Zmn_vXah0X7B8hXaE48jH8NIcdWQvEQb0R2j9wK2H6o40D5nWEz66Pon0Y"
            />
            
            {/* Render Map pins overlay representation on report */}
            {activeDefects.slice(0, 4).map((defect, index) => (
              <div
                key={defect.id}
                className="absolute flex flex-col items-center pointer-events-none"
                style={{
                  left: `${defect.x}%`,
                  top: `${defect.y}%`,
                  transform: "translate(-50%, -100%)"
                }}
              >
                <MapPin className="w-7 h-7 text-brand-error drop-shadow-md shrink-0" />
                <span className="bg-[#fdf9f5] text-brand-on-surface text-[9px] font-black px-1 py-0.5 rounded shadow-sm border border-brand-border-subtle leading-none mt-0.5">
                  D-0{index + 1}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Detailed Findings card list layout */}
        <div>
          <h3 className="text-base font-extrabold text-brand-on-surface mb-4 flex items-center gap-2">
            <FileText className="w-4 h-4 text-brand-primary" />
            Detailed Findings
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Findings Card 1: Structural crack near window */}
            <div className="bg-brand-surface rounded-lg border border-brand-brand-border-subtle overflow-hidden flex flex-col shadow-sm hover:shadow-md transition-shadow">
              <div className="h-44 bg-brand-surface-variant relative">
                <img
                  alt="Close up photo of drywall cracked settlement near load bearing frame window"
                  className="w-full h-full object-cover"
                  referrerPolicy="no-referrer"
                  src="https://lh3.googleusercontent.com/aida-public/AB6AXuC7f10kB3oYJDq-KhAtDHmrJge50oT40P3lhfgBugUlmXVQfSlvO7JVs3WJ1fRFPCFcGWFYWzB_GthqEd8MSo9qFigKYS7pe7-UxqoQXZ2L7F7pq6Rb_oDtZ-nor6xOusS6ojuqeKyMz8kl014LpItJSiNMy4JidVtkRD4M3x0g19pDx-opiLfUeOXGfbTNT3lAYbIgi1lWCAABFDKxD5inN3HOgzJFhJTtwYuTWfwLwJUwRaTHtHqLzMEsPu1S0bCEVKqJshMCWZw"
                />
                <div className="absolute top-3 left-3 bg-brand-error text-brand-on-primary font-bold px-2 py-0.5 rounded text-[9px] uppercase tracking-wider">
                  HIGH
                </div>
                <div className="absolute top-3 right-3 bg-brand-surface text-brand-on-surface font-bold px-2 py-0.5 rounded text-[9px]">
                  D-01
                </div>
              </div>
              <div className="p-4 flex-grow flex flex-col justify-between">
                <div>
                  <h4 className="text-sm font-bold text-brand-on-surface mb-1">
                    Structural Wall Crack - Meeting Room A Window
                  </h4>
                  <p className="text-xs text-brand-on-surface-variant leading-relaxed font-semibold">
                    Significant diagonal plaster cracking experienced adjacent to the north-facing window frame in meeting room wing. Suggests possible foundation load settlement issues.
                  </p>
                </div>
                <div className="pt-3 border-t border-brand-border-subtle text-[11px] text-brand-on-surface-variant flex justify-between font-bold mt-4">
                  <span>
                    Assigned: <span className="text-brand-primary">Structural Team</span>
                  </span>
                  <span>
                    Due: <span className="text-brand-on-background">Oct 26</span>
                  </span>
                </div>
              </div>
            </div>

            {/* Findings Card 2: Exposed wiring ceiling plenum */}
            <div className="bg-brand-surface rounded-lg border border-brand-brand-border-subtle overflow-hidden flex flex-col shadow-sm hover:shadow-md transition-shadow">
              <div className="h-44 bg-brand-surface-variant relative">
                <img
                  alt="Industrial construction layout showing exposed hanging grid wires"
                  className="w-full h-full object-cover"
                  referrerPolicy="no-referrer"
                  src="https://lh3.googleusercontent.com/aida-public/AB6AXuA_ZvF7TKzPoOeHpSMe5pRNgA6Ux58lgstPt1wR22N0WBkl7QBzzm25CVVRvUI-vZGUvR2VxyTafR8_mtFaRsrWrs8bForLfMZ4c9tCBl8CxE9WIG_UMYZqmkmPQkqBVz7DF0vHfVBelwvliH9MfHfjqndv7A4Ky_34xB3truubQJbLuEy5oj4rCK-gyM_NL0QVUsmhxuoVH_GRcYCea6-KSqB4tZ2SYqj71YveYfYAHNSORcrDnyC7qTT4oMVTddT7_l4qQemiBGw"
                />
                <div className="absolute top-3 left-3 bg-brand-secondary text-brand-on-primary font-bold px-2 py-0.5 rounded text-[9px] uppercase tracking-wider">
                  MEDIUM
                </div>
                <div className="absolute top-3 right-3 bg-brand-surface text-brand-on-surface font-bold px-2 py-0.5 rounded text-[9px]">
                  D-02
                </div>
              </div>
              <div className="p-4 flex-grow flex flex-col justify-between">
                <div>
                  <h4 className="text-sm font-bold text-brand-on-surface mb-1">
                    Exposed Conduit Wiring - Corridor B Ceiling
                  </h4>
                  <p className="text-xs text-brand-on-surface-variant leading-relaxed font-semibold">
                    HVAC controller electrical lines hanging directly in the Corridor B plenum lack safe code metallic conduit protection and are missing cable tray hangers.
                  </p>
                </div>
                <div className="pt-3 border-t border-brand-border-subtle text-[11px] text-brand-on-surface-variant flex justify-between font-bold mt-4">
                  <span>
                    Assigned: <span className="text-brand-primary">MEP Subcontractor</span>
                  </span>
                  <span>
                    Due: <span className="text-brand-on-background">Oct 28</span>
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Dynamic State Findings List addition (adds any local added pins as findings cards!) */}
        {activeDefects.length > 2 && (
          <div className="pt-2">
            <h4 className="text-xs font-bold text-brand-outline uppercase tracking-wider mb-3">
              Incremental Active Findings ({activeDefects.length - 2} Items)
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {activeDefects.slice(2).map((def, index) => (
                <div
                  key={def.id}
                  className="bg-brand-surface p-4 rounded-lg border border-brand-border-subtle shadow-xs relative"
                >
                  <span className="absolute top-3 right-3 bg-brand-surface-container-high px-2 py-0.5 rounded text-[9px] font-bold">
                    D-0{index + 3}
                  </span>
                  <p className="font-mono text-[10px] text-brand-outline uppercase tracking-wider font-bold">
                    {def.id} ({def.severity})
                  </p>
                  <h5 className="font-bold text-xs text-brand-on-surface mt-1">
                    {def.description}
                  </h5>
                  <p className="text-[11px] text-brand-on-surface-variant leading-relaxed mt-1 font-semibold">
                    Category: {def.category}. Location level: {def.zone}. Assigned trade: {def.responsibleParty} for restoration.
                  </p>
                  <div className="pt-2 border-t border-brand-border-subtle text-[10px] text-brand-outline flex justify-between font-bold mt-4">
                    <span>Due: {def.dueDate}</span>
                    <span className="text-brand-error uppercase font-black">{def.status}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
