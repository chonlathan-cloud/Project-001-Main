/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

export enum DefectSeverity {
  CRITICAL = "Critical",
  MAJOR = "Major",
  MINOR = "Minor",
  COSMETIC = "Cosmetic"
}

export enum DefectStatus {
  OPEN = "Open",
  IN_PROGRESS = "In Progress",
  RESOLVED = "Resolved"
}

export enum ActiveTab {
  INSPECT = "Inspect",
  DASHBOARD = "Dashboard",
  DEFECTS = "Defects",
  REPORT = "Report",
  SETTINGS = "Settings",
  HELP = "Help"
}

export enum ReportTab {
  CLIENT = "Client",
  CONTRACTOR = "Contractor",
  MANAGEMENT = "Management"
}

export interface Defect {
  id: string; // e.g., "#DF-102"
  description: string;
  category: string; // e.g. "Plumbing", "Electrical", "Finishes"
  severity: DefectSeverity;
  responsibleParty: string;
  dueDate: string; // Formatted date
  status: DefectStatus;
  pictureUrl?: string;
  zone: string; // e.g. "Level 4 - North Wing"
  x: number; // percentage position on floor plan
  y: number; // percentage position on floor plan
  details?: string;
}

export interface Contractor {
  name: string;
  openDefectsCount: number;
  avgDays: number;
  status: "At Risk" | "Monitor" | "On Track";
}

export interface CategoryPercentage {
  name: string;
  percentage: number;
  colorClass: string;
}
