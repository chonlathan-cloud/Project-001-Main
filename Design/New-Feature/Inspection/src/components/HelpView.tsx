/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { HelpCircle, Key, FileText, CheckSquare, Compass } from "lucide-react";

export default function HelpView() {
  const faqs = [
    {
      question: "How do I drop custom inspection pins on a floor plan?",
      answer: "Navigate to the 'Inspect' tab inside the left sidebar. Move your cursor to the interactive blueprint map and click on any point of interest. A modal form will automatically pop up allowing you to specify a custom defect description, severity level, assigned subcontractor trade, and additional comments before saving."
    },
    {
      question: "What dictates the project readiness percentage?",
      answer: "Dynamic scoring is calculated automatically through defect containment rates. Resolving outstanding Critical and Major defect items directly increases the rating. Keep severity-level resolutions on-schedule to reach the threshold handover milestones faster."
    },
    {
      question: "Can I print or save reports as a PDF format?",
      answer: "Yes. Navigate to the 'Report' tab and click on the 'Print Report' button. Your browser's printer configuration screen will launch. The document utilizes tailor-made '@media print' custom overlays, immediately stripping all menu buttons, bars, and non-printable sidebar navigation for a crisp official site-handover document."
    },
    {
      question: "How do I update the status of active defect markers?",
      answer: "Go to the 'Defects' tab from the sidebar to view the interactive records. Locate your target issue and click on the vertical dot navigation menu in the far right action column. You can instantly pivot statuses between 'Open', 'In Progress', and 'Resolved', which dynamically update the dashboard score totals and reporting metrics instantly."
    }
  ];

  return (
    <div className="space-y-6 max-w-3xl animate-fade-in pb-10">
      <div>
        <h2 className="text-3xl font-extrabold text-brand-on-background flex items-center gap-2">
          <HelpCircle className="w-8 h-8 text-brand-primary" />
          Technical Guidelines & Support
        </h2>
        <p className="text-sm font-medium text-brand-text-secondary mt-1">
          Learn detailed operation processes for managing construction defect items, scores, and handover protocols.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-semibold text-xs">
        <div className="p-4 bg-brand-surface border border-brand-border-subtle rounded-lg flex flex-col justify-between">
          <div>
            <Compass className="w-6 h-6 text-brand-primary mb-3" />
            <h4 className="text-brand-on-background font-bold mb-1">Interactive Triggers</h4>
            <p className="text-brand-on-surface-variant font-medium leading-relaxed">
              Drop defect locations with clickable crosshair pins directly onto active floor layers.
            </p>
          </div>
        </div>
        <div className="p-4 bg-brand-surface border border-brand-border-subtle rounded-lg flex flex-col justify-between">
          <div>
            <CheckSquare className="w-6 h-6 text-brand-secondary mb-3" />
            <h4 className="text-brand-on-background font-bold mb-1">State Synchronizations</h4>
            <p className="text-brand-on-surface-variant font-medium leading-relaxed">
              Updates to database states are reflected instantly in Category widgets, severity charts, and metrics.
            </p>
          </div>
        </div>
        <div className="p-4 bg-brand-surface border border-brand-border-subtle rounded-lg flex flex-col justify-between">
          <div>
            <FileText className="w-6 h-6 text-brand-tertiary-container mb-3" />
            <h4 className="text-brand-on-background font-bold mb-1">Print Readiness</h4>
            <p className="text-brand-on-surface-variant font-medium leading-relaxed">
              Tailor-made document media formatting produces crisp reports for stakeholder distribution.
            </p>
          </div>
        </div>
      </div>

      <div className="bg-brand-surface p-6 rounded-lg border border-brand-border-subtle shadow-xs space-y-4">
        <h3 className="text-sm font-bold text-brand-primary uppercase tracking-wider border-b border-brand-border-subtle pb-2">
          Frequently Answered Inquiries
        </h3>
        
        <div className="space-y-4 divide-y divide-brand-border-subtle">
          {faqs.map((faq, index) => (
            <div key={faq.question} className={`${index > 0 ? "pt-4" : ""} space-y-1.5`}>
              <h4 className="text-sm font-bold text-brand-on-background flex items-center gap-2">
                <span className="text-brand-primary font-black">Q:</span>
                {faq.question}
              </h4>
              <p className="text-xs text-brand-on-surface-variant leading-relaxed font-semibold pl-5">
                {faq.answer}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
