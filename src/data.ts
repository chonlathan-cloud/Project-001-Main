import { Project, ApprovalRequest, ActivityLog, Subcontractor } from './types';

export const INITIAL_PROJECTS: Project[] = [
  {
    id: 'PRJ-001',
    name: 'Commercial Tower A',
    code: 'PRJ-24-001',
    status: 'active',
    budget: 12400000,
    spent: 5580000,
    progress: 45,
    owner: 'Marcus Vance (Senior PM)',
    subcontractorCount: 14,
    startDate: '2024-01-15',
    endDate: '2026-08-30',
    description: 'A 42-story mixed-use commercial tower in the downtown metro area. Incorporates a high-efficiency double-skin glass facade, geothermal cooling wells, and adaptive smart building operations.',
    boqSynced: true,
    boqLastSync: 'May 25, 2026 at 11:24 AM',
    location: 'Downtown Metro',
    boqItems: [
      { id: 'boq-001', itemCode: '03.3000', description: 'Cast-in-Place Structural Concrete (Grade C40/50, high slump, water-resistant)', unit: 'm3', quantity: 24500, rate: 185, amount: 4532500, status: 'synced' },
      { id: 'boq-002', itemCode: '05.1200', description: 'Structural Steel Framing (Grade ASTM A992, W-shapes)', unit: 'ton', quantity: 3800, rate: 2100, amount: 7980000, status: 'synced' },
      { id: 'boq-003', itemCode: '08.4413', description: 'Double-Skin Unitized Curtain Wall Facade (Triple-glazed, low-E, argon-filled)', unit: 'm2', quantity: 18400, rate: 450, amount: 8280000, status: 'modified' },
      { id: 'boq-004', itemCode: '23.6423', description: 'Centrifugal Water-Cooled Chillers (1200 RT capacity, eco-friendly refrigerant)', unit: 'set', quantity: 3, rate: 310000, amount: 930000, status: 'synced' },
      { id: 'boq-005', itemCode: '09.3000', description: 'Premium Terrazzo Flooring (High-traffic formulation, custom marble aggregates)', unit: 'm2', quantity: 12500, rate: 95, amount: 1187500, status: 'pending_sync' },
      { id: 'boq-006', itemCode: '26.0519', description: 'Low-Voltage Copper Power Conductors & Cabling (LSOH insulated)', unit: 'm', quantity: 82000, rate: 12, amount: 984000, status: 'synced' },
    ]
  },
  {
    id: 'PRJ-002',
    name: 'Residential Complex',
    code: 'PRJ-24-042',
    status: 'draft',
    budget: 8100000,
    spent: 972000,
    progress: 12,
    owner: 'Sarah Lin (Associate PM)',
    subcontractorCount: 4,
    startDate: '2026-07-01',
    endDate: '2027-12-15',
    description: 'An premium luxury residential complex consisting of multi-family low-rise structures, featuring sustainable green roofs, smart home integrations, integrated community parks, and net-zero energy offsets.',
    boqSynced: false,
    location: 'North Suburbs',
    boqItems: []
  },
  {
    id: 'PRJ-003',
    name: 'Logistics Hub',
    code: 'PRJ-23-118',
    status: 'on_hold',
    budget: 22000000,
    spent: 19360000,
    progress: 88,
    owner: 'Elena Rostova (Lead Civil Designer)',
    subcontractorCount: 8,
    startDate: '2024-10-01',
    endDate: '2026-11-20',
    description: 'Expansion of dual-lane municipal thoroughfares, drainage mains, integrated bicycle paths, automated sorting hubs, and LED smart light poles across the industrial development corridor.',
    boqSynced: true,
    boqLastSync: 'May 24, 2026 at 4:15 PM',
    location: 'Industrial Zone',
    boqItems: [
      { id: 'boq-201', itemCode: '31.2300', description: 'Mass Civil Excavation and Unclassified Fill Materials', unit: 'm3', quantity: 155000, rate: 45, amount: 6975000, status: 'synced' },
      { id: 'boq-202', itemCode: '32.1216', description: 'Superpave Asphalt Concrete Paving (Binder coarse and high SBS modified wearing)', unit: 'ton', quantity: 48000, rate: 115, amount: 5520000, status: 'synced' },
    ]
  },
  {
    id: 'PRJ-004',
    name: 'Water Reclamation Facility',
    code: 'PRJ-24-099',
    status: 'active',
    budget: 57500000,
    spent: 49200000,
    progress: 85,
    owner: 'David Vance (Director of Infrastructure)',
    subcontractorCount: 19,
    startDate: '2023-03-10',
    endDate: '2026-07-30',
    description: 'A cutting-edge advanced tertiary water purification facility. Capable of processing 12 Million Gallons Daily (MGD) using multi-tier biological active sediment systems, reverse osmosis, and ultraviolet sanitation loops.',
    boqSynced: true,
    boqLastSync: 'May 10, 2026 at 9:00 AM',
    location: 'Industrial Buffer Area, East Zone',
    boqItems: [
      { id: 'boq-301', itemCode: '46.2111', description: 'Submerged Disc Fine Screening Machinery Assembly', unit: 'set', quantity: 6, rate: 145000, amount: 870000, status: 'synced' },
      { id: 'boq-302', itemCode: '46.3300', description: 'Tertiary Membrane Bioreactor UV Disinfection Grid', unit: 'set', quantity: 4, rate: 520000, amount: 2080000, status: 'synced' },
      { id: 'boq-303', itemCode: '40.0513', description: 'Stainless Steel Liquid Process Piping (Grade 316L, sanitary weld)', unit: 'ton', quantity: 650, rate: 4200, amount: 2730000, status: 'synced' },
    ]
  }
];

export const INITIAL_APPROVALS: ApprovalRequest[] = [
  {
    id: 'APP-101',
    projectId: 'PRJ-001',
    projectName: 'Commercial Tower A',
    title: 'Reinforced Steel Foundations Increment',
    subcontractor: 'Apex Builders Co.',
    amount: 24000,
    status: 'pending',
    date: '2026-05-25',
    category: 'Structural',
    requestedBy: 'Timothy O\'Connor (Lead Structural Eng.)',
    description: 'Structural foundation design adjustments required additional high-strength steel rebar detailing for seismic buffer plates in columns C2 through C6.'
  },
  {
    id: 'APP-102',
    projectId: 'PRJ-001',
    projectName: 'Commercial Tower A',
    title: 'HVAC Duct Reselect Expansion',
    subcontractor: 'BreezeAir Thermal Solutions',
    amount: 14500,
    status: 'pending',
    date: '2026-05-24',
    category: 'HVAC',
    requestedBy: 'Helena Vance (Mechanical Consult)',
    description: 'Change order request to update raw ductwork insulation specifications from mineral wool wraps to low-emissivity elastomeric foam jackets inside ceiling plenums.'
  },
  {
    id: 'APP-103',
    projectId: 'PRJ-003',
    projectName: 'Suburban Infrastructure Expansion',
    title: 'Geotextile Silt Filtration Fabric Overrun',
    subcontractor: 'TerraFirm Earthworkers',
    amount: 8700,
    status: 'approved',
    date: '2026-05-22',
    category: 'Civil',
    requestedBy: 'Michael K. (Civil Inspector)',
    description: 'Extra safety barrier silt containment required due to high local runoff under unexpected season precipitation cycles around Section 3.'
  },
  {
    id: 'APP-104',
    projectId: 'PRJ-004',
    projectName: 'Water Reclamation Facility',
    title: 'Process Control SCADA Cabinet Upgrades',
    subcontractor: 'Integratech Automation Ltd',
    amount: 42500,
    status: 'pending',
    date: '2026-05-20',
    category: 'Electrical',
    requestedBy: 'Gregory Finch (SCADA Specialist)',
    description: 'Integration of critical secondary emergency automatic power-trip circuits on industrial backplanes to safeguard fine disc microfilter systems from grid surges.'
  },
  {
    id: 'APP-105',
    projectId: 'PRJ-001',
    projectName: 'Commercial Tower A',
    title: 'Double-Skin Glass Facade Spec Modification',
    subcontractor: 'Apex Builders Co.',
    amount: 115000,
    status: 'rejected',
    date: '2026-05-15',
    category: 'Finishes',
    requestedBy: 'Marcus Vance (Senior PM)',
    description: 'Alternate facade supplier پیشنهاد for acoustic glaze core panels was rejected. Performance metrics failed structural sound transmission coefficients (FSTC) thresholds.'
  }
];

export const INITIAL_ACTIVITY: ActivityLog[] = [
  {
    id: 'ACT-001',
    type: 'sync',
    projectCode: 'PRJ-001-A',
    projectName: 'Commercial Tower A',
    user: 'Autodesk Integration',
    message: 'Synchronized curtain wall assemblies with AutoCAD Revit master model',
    timestamp: 'May 25, 2026 at 11:24 AM'
  },
  {
    id: 'ACT-002',
    type: 'approval',
    projectCode: 'PRJ-001-C',
    projectName: 'Suburban Infrastructure Expansion',
    user: 'James Harrison (Dir. Governance)',
    message: 'Approved silt geo-textile change request of $8,700 for TerraFirm',
    timestamp: 'May 22, 2026 at 4:32 PM'
  },
  {
    id: 'ACT-003',
    type: 'budget_alteration',
    projectCode: 'PRJ-001-A',
    projectName: 'Commercial Tower A',
    user: 'Sarah Lin',
    message: 'Updated terrestrial flooring line item quantity estimate (+500 m2)',
    timestamp: 'May 21, 2026 at 1:15 PM'
  },
  {
    id: 'ACT-004',
    type: 'status_change',
    projectCode: 'PRJ-001-B',
    projectName: 'Grand Residence Phase 1',
    user: 'James Harrison',
    message: 'Authorized Project Charter creation. System state set to Draft',
    timestamp: 'May 18, 2026 at 9:30 AM'
  }
];

export const SUBCONTRACTORS: Subcontractor[] = [
  {
    id: '4',
    name: 'Apex Builders Co.',
    registeredName: 'Apex Builders Company Limited',
    taxId: '0105526089451',
    status: 'approved',
    primaryContact: 'Somchai Prasert',
    phone: '+66 81 234 5678',
    email: 'contact@apexbuilders.co.th',
    compliance: [
      {
        id: 'comp-001',
        name: 'Commercial Registration',
        status: 'verified'
      },
      {
        id: 'comp-002',
        name: 'VAT Registration (P.P.20)',
        status: 'verified'
      },
      {
        id: 'comp-003',
        name: 'Professional License',
        status: 'verified'
      },
      {
        id: 'comp-004',
        name: 'Bank Account Verification',
        status: 'verified'
      }
    ],
    projects: [
      {
        id: 'PRJ-2023-045',
        code: 'PRJ-2023-045',
        name: 'Sathorn Tower Complex',
        role: 'Structural Framework',
        contractValue: 12500000,
        status: 'active'
      },
      {
        id: 'PRJ-2022-112',
        code: 'PRJ-2022-112',
        name: 'Riverside Condominium Phase 2',
        role: 'Foundation Pilling',
        contractValue: 8250000,
        status: 'completed'
      },
      {
        id: 'PRJ-2021-088',
        code: 'PRJ-2021-088',
        name: 'Sukhumvit Retail Mall',
        role: 'Structural Framework',
        contractValue: 24000000,
        status: 'completed'
      }
    ]
  }
];
