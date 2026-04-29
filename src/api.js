const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

// Helper for temporary mock data until backend is ready
const getMockData = (type) => {
  const mocks = {
    dashboard: { 
      total_projects: 0, 
      total_expenses: 0, 
      projects: [],
      stats: [
        { title: 'Total Revenue', value: '$0' },
        { title: 'Active Projects', value: '0' },
        { title: 'Pending Tasks', value: '0' },
        { title: 'Team Members', value: '0' }
      ],
      shipmentData: [],
      budgetData: [],
      wagesData: [],
      valueData: [],
      workPeriodData: []
    },
    projects: [
      { name: 'Example Project', spent: 500, total: 1000, status: 'on track' }
    ],
    insights: { 
      summary: {
        new: { count: 0, amount: '0' },
        pending: { count: 0, amount: '0' },
        approved: { count: 0, amount: '0' }
      },
      filters: {
        users: ['All Users'],
        months: ['Jan', 'Feb', 'Mar'],
        years: ['2026']
      },
      tableData: [],
      tableName: "รายการทั้งหมด"
    },
    settings: {}
  };
  return mocks[type] || [];
};


export const fetchData = async (type, param = null) => {
  try {
    let url = `${API_BASE_URL}/api/${type}`;
    if (param) url += `?param=${encodeURIComponent(param)}`;

    const response = await fetch(url);
    
    // Check if response is JSON to prevent crashes when backend is not ready
    const contentType = response.headers.get("content-type");
    if (!response.ok || !contentType || !contentType.includes("application/json")) {
      console.warn(`Backend not ready or invalid response for ${type}. Returning mock data.`);
      return getMockData(type);
    }
    
    return await response.json();
  } catch (error) {
    console.error('API Error:', error);
    return getMockData(type);
  }
};

export const postData = async (type, data) => {
  try {
    const url = `${API_BASE_URL}/api/${type}`;
    const options = {
      method: 'POST',
      headers: data instanceof FormData ? {} : { 'Content-Type': 'application/json' },
      body: data instanceof FormData ? data : JSON.stringify(data),
    };

    const response = await fetch(url, options);
    const contentType = response.headers.get("content-type");
    
    if (!response.ok || !contentType || !contentType.includes("application/json")) {
      console.warn(`Backend not ready for POST ${type}. Simulating success.`);
      return { success: true, message: 'Mock success' };
    }
    
    return await response.json();
  } catch (error) {
    console.error('API Post Error:', error);
    return { success: true, message: 'Mock success' };
  }
};

// --- Mock functions for InputPage ---

export const getInputProjectOptions = async () => {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 500));
  return [
    { project_id: 'proj_001', name: 'Project Alpha' },
    { project_id: 'proj_002', name: 'Project Beta' },
  ];
};

export const extractInputReceipt = async (file) => {
  await new Promise(resolve => setTimeout(resolve, 1500));
  return {
    file_name: file.name,
    content_type: file.type,
    vendor_name: 'Mock Vendor Co.',
    receipt_no: 'INV-MOCK-1234',
    document_date: new Date().toISOString().slice(0, 10),
    total_amount: 1500,
    suggested_request_type: 'ค่าวัสดุ',
    suggested_entry_type: 'EXPENSE',
    items: [
      { description: 'Mock Item 1', qty: 1, price: 1000 },
      { description: 'Mock Item 2', qty: 1, price: 500 }
    ]
  };
};

export const submitInputRequest = async (payload) => {
  await new Promise(resolve => setTimeout(resolve, 1000));
  return {
    request_id: 'REQ-' + Math.floor(Math.random() * 10000),
    project_name: 'Selected Project',
    entry_type: payload.entry_type,
    requester_name: payload.requester_name,
    vendor_name: payload.vendor_name,
    receipt_no: payload.receipt_no,
    document_date: payload.document_date,
    amount: payload.amount,
    status: 'PENDING_ADMIN',
    is_duplicate_flag: false
  };
};
