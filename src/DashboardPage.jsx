import React, { useState, useEffect } from 'react';
import StatCard from './components/StatCard';
import ShipmentChart from './components/ShipmentChart';
import BudgetChart from './components/BudgetChart';
import WagesChart from './components/WagesChart';
import ValueChart from './components/ValueChart';
import WorkPeriodChart from './components/WorkPeriodChart';
import { fetchData } from './api';
import Loading from './components/Loading';

const DashboardPage = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      const result = await fetchData('dashboard');
      setData(result);
      setLoading(false);
    };
    loadData();
  }, []);

  if (loading) return <Loading />;

  return (
    <>
      <h1 style={{ fontSize: '32px', marginBottom: '8px' }}>Dashboard</h1>
      
      <div className="dashboard-grid">
        {data.stats.map((stat, index) => (
          <StatCard key={index} index={index} title={stat.title} value={stat.value} />
        ))}
      </div>

      <div className="chart-section">
        <ShipmentChart data={data.shipmentData} />
        <BudgetChart data={data.budgetData} />
      </div>

      <div className="bottom-section">
        <WagesChart data={data.wagesData} />
        <ValueChart data={data.valueData} />
        <WorkPeriodChart data={data.workPeriodData} />
      </div>
    </>
  );
};

export default DashboardPage;
