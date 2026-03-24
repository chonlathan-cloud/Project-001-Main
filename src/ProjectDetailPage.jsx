import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import StatCard from './components/StatCard';
import ShipmentChart from './components/ShipmentChart';
import SalesChart from './components/SalesChart';
import WagesChart from './components/WagesChart';
import ValueChart from './components/ValueChart';
import WorkPeriodChart from './components/WorkPeriodChart';
import { fetchData } from './api';
import Loading from './components/Loading';

const ProjectDetailPage = () => {
  const location = useLocation();
  const passedProjectName = location.state?.projectName;

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      const result = await fetchData('project_detail', passedProjectName);
      setData(result);
      setLoading(false);
    };
    loadData();
  }, [passedProjectName]);

  if (loading) return <Loading />;

  return (
    <>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginBottom: '24px' }}>
        <h1 style={{ fontSize: '32px' }}>Project</h1>
        <div style={{ 
          display: 'inline-flex', 
          alignItems: 'center', 
          gap: '8px', 
          backgroundColor: 'white', 
          padding: '8px 40px', 
          borderRadius: '12px',
          border: '1.5px solid var(--border-color)',
          width: 'fit-content',
          fontSize: '24px'
        }}>
          {passedProjectName || data.name}
        </div>
      </div>
      
      <div className="dashboard-grid">
        {data.stats.map((stat, index) => (
          <StatCard key={index} index={index} title={stat.title} value={stat.value} />
        ))}
      </div>

      <div className="chart-section">
        <ShipmentChart data={data.shipmentData} />
        <SalesChart data={data.salesData} />
      </div>

      <div className="bottom-section" style={{ marginBottom: '40px' }}>
        <WagesChart data={data.wagesData} />
        <ValueChart data={data.valueData} />
        <WorkPeriodChart data={data.workPeriodData} />
      </div>
    </>
  );
};

export default ProjectDetailPage;
