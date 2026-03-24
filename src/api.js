// Mock API utility to simulate backend responses

const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

export const fetchData = async (type, param = null) => {
  await sleep(1000); // Simulate network latency

  switch (type) {
    case 'dashboard':
      return {
        stats: [
          { title: 'รายรับ', value: '...' },
          { title: 'รายจ่าย', value: '...' },
          { title: 'คงเหลือ', value: '...' },
          { title: 'BOQ', value: '...' }
        ],
        shipmentData: [],
        budgetData: [],
        wagesData: [],
        valueData: [],
        workPeriodData: []
      };
    case 'projects':
      return [];
    case 'project_detail':
      return {
        name: param || 'Name_Project',
        stats: [
          { title: 'รายรับ', value: '-' },
          { title: 'รายจ่าย', value: '-' },
          { title: 'คงเหลือ', value: '-' },
          { title: 'BOQ', value: '-' }
        ],
        shipmentData: [],
        salesData: [],
        wagesData: [],
        valueData: [],
        workPeriodData: []
      };
    case 'insights':
      return {
        filters: ['ผู้ทำรายการทั้งหมด', 'หมวดหมู่ทั้งหมด', 'เดือน', 'ปี']
      };
    case 'settings':
      return [1, 2, 3, 4, 5, 6];
    default:
      return null;
  }
};
