const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

// Helper for temporary mock data until backend is ready
const getMockData = (type) => {
  const mocks = {
    dashboard: { total_projects: 0, total_expenses: 0, projects: [] },
    projects: [],
    insights: { data: [] },
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
