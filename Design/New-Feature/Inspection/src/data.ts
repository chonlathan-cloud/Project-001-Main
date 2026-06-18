/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { Defect, DefectSeverity, DefectStatus, Contractor, CategoryPercentage } from "./types";

export const initialDefects: Defect[] = [
  {
    id: "#DF-102",
    description: "Water leak in Level 3 toilet ceiling",
    category: "Plumbing",
    severity: DefectSeverity.CRITICAL,
    responsibleParty: "Apex Builders Ltd.",
    dueDate: "2023-10-24",
    status: DefectStatus.OPEN,
    pictureUrl: "https://lh3.googleusercontent.com/aida-public/AB6AXuDIR1vx__pSytWqEXzYss0WxzzuyyfRHvprKnDGg3qrNMGFx0SAipltSE1lmqBrfZp-UTlKVXu3geUpo456DwtCkiSJpHMt189ANT7FO5fI9yPCCcyEhy148taX0V7gIzQ4JxNQY73pwV7d_ZAFEi39KPHx5IU5MjDfkpwdl38zI1JCcf4vkrlxAc_kwc2KrU1rm84qqfTaZQbtyircvkLhweu_HcZLCuli4qtKI2t1TUa_iuMhmgzEjUTZuHkuwLF_SXDEYZqtODY",
    zone: "Level 4 - North Wing",
    x: 45,
    y: 30,
    details: "Significant slow drip reported above sink row 2, staining sheetrock and causing ceiling frame corrosion risk."
  },
  {
    id: "#DF-101",
    description: "Cracked drywall near elevator lobby",
    category: "Finishes",
    severity: DefectSeverity.MAJOR,
    responsibleParty: "Interior Decorators Inc.",
    dueDate: "2023-10-26",
    status: DefectStatus.IN_PROGRESS,
    zone: "Level 4 - North Wing",
    x: 25,
    y: 60,
    details: "Drywall plaster crack running diagonally down the left side elevator bank. Needs taping, floating, and repaint."
  },
  {
    id: "#DF-098",
    description: "Exposed wiring in server room",
    category: "Electrical",
    severity: DefectSeverity.CRITICAL,
    responsibleParty: "Volt Systems",
    dueDate: "2023-10-20",
    status: DefectStatus.RESOLVED,
    pictureUrl: "https://lh3.googleusercontent.com/aida-public/AB6AXuC8GnN-KyyEILI2wdSsXsd7cK8ytO04_duIlHF0My5GxM2TRxZy0WFtoqQRG2jAnMu-lqwPlnItkPWMBQdnYklMP2ey2gBD6muFs_AF_TRkMkxwd5gZONZ1P5aTnw91m6Ki4GBT5xg5iAvf_mIXiK7e_xrC2-rdzfbhd7r3ANzBH3rpiJTOv5Y7KhASa1ypfE1ccTXAqA2jxCr2y3u1s-VKm1p9CVSlrKeazKYSvjJiWechShZKuY17MWM1SEOoaCQsCDG-1FBWO_g",
    zone: "Level 4 - North Wing",
    x: 60,
    y: 75,
    details: "Temporary electrical routing is hanging direct from structural ceiling grid without proper junction box enclosure."
  },
  {
    id: "#DF-103",
    description: "HVAC seal leak in Corridor B ceiling",
    category: "Mechanical / HVAC",
    severity: DefectSeverity.MINOR,
    responsibleParty: "Elevate MEP",
    dueDate: "2023-10-28",
    status: DefectStatus.OPEN,
    zone: "Level 4 - North Wing",
    x: 70,
    y: 20,
    details: "Duct segment seal integrity at junction 12 failed smoke test. Recommend mastic application."
  },
  {
    id: "#DF-097",
    description: "Window pane seal compromise in meeting room",
    category: "Architectural",
    severity: DefectSeverity.COSMETIC,
    responsibleParty: "Apex Builders Ltd.",
    dueDate: "2023-10-18",
    status: DefectStatus.OPEN,
    zone: "Level 4 - North Wing",
    x: 82,
    y: 45,
    details: "Thermal glazing seal compromised on the second window bay. Moisture is visible within active glass layers."
  }
];

export const initialContractors: Contractor[] = [
  { name: "Apex Builders Ltd.", openDefectsCount: 42, avgDays: 14.5, status: "At Risk" },
  { name: "Elevate MEP", openDefectsCount: 28, avgDays: 8.2, status: "Monitor" },
  { name: "Structura Co.", openDefectsCount: 15, avgDays: 4.1, status: "On Track" },
  { name: "Prime Finishes", openDefectsCount: 12, avgDays: 5.0, status: "On Track" }
];

export const initialCategoryPercentages: CategoryPercentage[] = [
  { name: "Architectural", percentage: 45, colorClass: "bg-brand-primary" },
  { name: "Electrical", percentage: 25, colorClass: "bg-brand-secondary-fixed-dim" },
  { name: "Plumbing", percentage: 15, colorClass: "bg-brand-outline" },
  { name: "Mechanical / HVAC", percentage: 10, colorClass: "bg-brand-tertiary-container" },
  { name: "Structural", percentage: 5, colorClass: "bg-brand-outline-variant" }
];

export const zoneList = [
  "Level 4 - North Wing",
  "Level 4 - South Wing",
  "Level 3 - Main Lobby",
  "Level 3 - Restrooms",
  "Level 2 - Conference Center"
];

export const quickAddPresets = [
  { description: "Paint Scuff / Touch-up", category: "Architectural", severity: DefectSeverity.MINOR },
  { description: "Tile Grout Incomplete", category: "Finishes", severity: DefectSeverity.MAJOR },
  { description: "Door Frame Misaligned", category: "Carpentry", severity: DefectSeverity.MAJOR },
  { description: "Power Socket Untested", category: "Electrical", severity: DefectSeverity.CRITICAL }
];
