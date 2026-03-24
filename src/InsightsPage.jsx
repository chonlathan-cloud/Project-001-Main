import React, { useState, useEffect } from 'react';
import { ChevronDown } from 'lucide-react';
import { fetchData } from './api';
import Loading from './components/Loading';

const InsightsDropdown = ({ label }) => (
  <div style={{
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '16px',
    padding: '8px 16px',
    borderRadius: '20px',
    backgroundColor: 'white',
    border: '1px solid var(--border-color)',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: '500',
    minWidth: '100px'
  }}>
    <span>{label}</span>
    <ChevronDown size={16} />
  </div>
);

const InsightsPage = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      const result = await fetchData('insights');
      setData(result);
      setLoading(false);
    };
    loadData();
  }, []);

  if (loading) return <Loading />;

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px' }}>
        <h1 style={{ fontSize: '32px' }}>Insights</h1>
        
        <div style={{ display: 'flex', gap: '16px' }}>
          {data.filters.map((filter, index) => (
            <InsightsDropdown key={index} label={filter} />
          ))}
        </div>
      </div>

      {/* Top 3 Cards Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '24px', marginBottom: '24px' }}>
        <div className="card" style={{ height: '140px', backgroundColor: 'white' }}></div>
        <div className="card" style={{ height: '140px', backgroundColor: 'white' }}></div>
        <div className="card" style={{ height: '140px', backgroundColor: 'white' }}></div>
      </div>

      {/* Large Bottom Card */}
      <div className="card" style={{ height: '500px', backgroundColor: 'white' }}></div>
    </>
  );
};

export default InsightsPage;
