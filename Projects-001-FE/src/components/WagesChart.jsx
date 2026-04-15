import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import { ArrowUpRight } from 'lucide-react';

const WagesChart = ({ data }) => {
  const chartData = data || [];

  return (
    <div 
      className="card" 
      style={{ height: '300px', display: 'flex', flexDirection: 'column' }}
    >
      <div className="flex justify-between items-center" style={{ marginBottom: '16px' }}>
        <h3 style={{ fontSize: '16px', fontWeight: '600' }}>Wages</h3>
        <div className="flex items-center gap-2" style={{ fontSize: '12px', color: '#666', cursor: 'pointer' }}>
          <span>see all</span>
          <ArrowUpRight size={14} />
        </div>
      </div>
      
      <div style={{ flex: 1 }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              innerRadius={60}
              outerRadius={80}
              paddingAngle={2}
              dataKey="value"
            >
              {chartData.map((entry) => (
                <Cell key={entry.id} fill={entry.color} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default WagesChart;
