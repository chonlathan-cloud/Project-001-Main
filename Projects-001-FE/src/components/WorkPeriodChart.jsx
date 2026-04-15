import React from 'react';
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell } from 'recharts';
import { ArrowUpRight } from 'lucide-react';

const WorkPeriodChart = ({ data }) => {
  const chartData = data || [];

  return (
    <div className="card" style={{ height: '300px', display: 'flex', flexDirection: 'column' }}>
      <div className="flex justify-between items-center" style={{ marginBottom: '16px' }}>
        <h3 style={{ fontSize: '16px', fontWeight: '600' }}>Work period</h3>
        <div className="flex items-center gap-2" style={{ fontSize: '12px', color: '#666', cursor: 'pointer' }}>
          <span>see all</span>
          <ArrowUpRight size={14} />
        </div>
      </div>
      
      <div style={{ flex: 1, padding: '10px 0' }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} layout="vertical" margin={{ left: -40 }}>
            <XAxis type="number" hide />
            <YAxis dataKey="name" type="category" hide />
            <Bar dataKey="value" radius={[0, 10, 10, 0]} barSize={20}>
              {chartData.map((entry) => (
                <Cell key={entry.name} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default WorkPeriodChart;
