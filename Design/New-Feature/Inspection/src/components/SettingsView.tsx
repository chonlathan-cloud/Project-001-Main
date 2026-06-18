/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from "react";
import { Settings, Save, RefreshCw, CheckCircle2, User, Building, Phone } from "lucide-react";

interface SettingsViewProps {
  inspectorName: string;
  setInspectorName: (name: string) => void;
  onResetData: () => void;
}

export default function SettingsView({
  inspectorName,
  setInspectorName,
  onResetData
}: SettingsViewProps) {
  const [phone, setPhone] = useState("+1 (555) 234-5678");
  const [company, setCompany] = useState("Rayadee Site Management Services");
  const [success, setSuccess] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSuccess(true);
    setTimeout(() => setSuccess(false), 3000);
  };

  return (
    <div className="space-y-6 max-w-2xl animate-fade-in pb-10">
      <div>
        <h2 className="text-3xl font-extrabold text-brand-on-background flex items-center gap-2">
          <Settings className="w-8 h-8 text-brand-primary" />
          Project Settings
        </h2>
        <p className="text-sm font-medium text-brand-text-secondary mt-1">
          Configure inspector profile details, notification preferences, and system storage.
        </p>
      </div>

      <div className="bg-brand-surface p-6 rounded-lg border border-brand-border-subtle shadow-xs space-y-6">
        <form onSubmit={handleSave} className="space-y-4">
          <h3 className="text-sm font-bold text-brand-primary uppercase tracking-wider flex items-center gap-2 border-b border-brand-border-subtle pb-2">
            <User className="w-4 h-4" />
            Inspector Information
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-brand-on-surface-variant mb-1">
                Inspector Name
              </label>
              <input
                type="text"
                className="w-full px-3 py-2 border border-brand-border-subtle rounded-md text-sm bg-brand-surface focus:ring-2 focus:ring-brand-primary outline-hidden font-semibold"
                value={inspectorName}
                onChange={(e) => setInspectorName(e.target.value)}
              />
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-brand-on-surface-variant mb-1">
                Active Company
              </label>
              <input
                type="text"
                className="w-full px-3 py-2 border border-brand-border-subtle rounded-md text-sm bg-brand-surface focus:ring-2 focus:ring-brand-primary outline-hidden font-semibold"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-brand-on-surface-variant mb-1">
                Contact Phone
              </label>
              <input
                type="text"
                className="w-full px-3 py-2 border border-brand-border-subtle rounded-md text-sm bg-brand-surface focus:ring-2 focus:ring-brand-primary outline-hidden font-semibold"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
              />
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-brand-on-surface-variant mb-1">
                Site Location Access
              </label>
              <select className="w-full px-3 py-2 border border-brand-border-subtle rounded-md text-sm bg-brand-background focus:ring-2 focus:ring-brand-primary outline-hidden font-semibold">
                <option>Block A (Level 1-4)</option>
                <option>Block B (Foundation Level)</option>
                <option>Full Station Access</option>
              </select>
            </div>
          </div>

          <div className="flex items-center justify-between pt-2">
            {success && (
              <span className="text-xs text-brand-primary font-bold flex items-center gap-1.5 animate-bounce">
                <CheckCircle2 className="w-4 h-4 text-brand-primary" />
                Profile changes saved successfully!
              </span>
            )}
            <button
              type="submit"
              className="ml-auto bg-brand-primary text-brand-on-primary px-5 py-2.5 rounded-lg text-xs font-bold hover:bg-brand-surface-tint shadow-xs flex items-center gap-2 cursor-pointer transition-all active:scale-[0.98]"
            >
              <Save className="w-4 h-4" />
              Save Configurations
            </button>
          </div>
        </form>

        <div className="border-t border-brand-border-subtle pt-6">
          <h3 className="text-xs font-bold text-brand-error uppercase tracking-wider flex items-center gap-2 mb-2">
            ⚠️ Diagnostic Storage Management
          </h3>
          <p className="text-xs text-brand-on-surface-variant leading-relaxed font-semibold mb-4">
            To view the exact default defect layout from the startup state or discard your current custom added blueprint marker pins, proceed with factory state diagnostics tool reset.
          </p>
          <button
            type="button"
            onClick={() => {
              if (confirm("Reset current site inspection variables back to default template mock values?")) {
                onResetData();
                alert("Data reverted successfully!");
              }
            }}
            className="flex items-center gap-2 px-4 py-2 border border-brand-error text-brand-error font-bold text-xs rounded-lg hover:bg-red-50 transition-colors cursor-pointer"
          >
            <RefreshCw className="w-4 h-4" />
            Reset Factory Dataset
          </button>
        </div>
      </div>
    </div>
  );
}
