import React, { useState, useEffect } from 'react';
import { fetchData } from './api';
import Loading from './components/Loading';

const SettingPage = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      const result = await fetchData('settings');
      setItems(result);
      setLoading(false);
    };
    loadData();
  }, []);

  if (loading) return <Loading />;

  return (
    <>
      <div style={{ marginBottom: '32px' }}>
        <h1 style={{ fontSize: '32px', marginBottom: '8px' }}>Setting</h1>
        <p style={{ fontSize: '16px', color: '#666', fontWeight: '500' }}>จัดการ User</p>
      </div>

      {/* Grid of 6 Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '24px' }}>
        {items.map((item) => (
          <div key={item} className="card" style={{ height: '220px', backgroundColor: 'white' }}></div>
        ))}
      </div>
    </>
  );
};

export default SettingPage;
