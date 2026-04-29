import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';

const BudgetChart = ({ data }) => {
  const chartData = data || [];

  return (
    <div className="card" style={{ height: '400px', display: 'flex', flexDirection: 'column', position: 'relative' }}>
      <h3 style={{ fontSize: '20px', fontWeight: '600', marginBottom: '24px' }}>Budget</h3>
      
      <div className="flex" style={{ flex: 1 }}>
        <div style={{ width: '100px', display: 'flex', flexDirection: 'column', gap: '16px', justifyContent: 'center' }}>
          {chartData.map((item, index) => (
            <div key={index} style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: item.color }} />
          ))}
        </div>
        
        <div style={{ flex: 1, position: 'relative' }}>
          {/* Custom Callout Balloon */}
          {chartData.length > 0 && (
            <div style={{
              position: 'absolute',
              top: '20%',
              left: '10%',
              backgroundColor: 'white',
              boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
              padding: '6px 12px',
              borderRadius: '12px',
              zIndex: 10,
              fontSize: '11px',
              textAlign: 'center',
              border: '1px solid #eee'
            }}>
              <p style={{ color: '#ccc', fontWeight: 'bold' }}>7%</p>
              <p style={{ fontWeight: 'bold' }}>$400</p>
            </div>
          )}

          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={70}
                outerRadius={100}
                paddingAngle={5}
                dataKey="value"
                startAngle={90}
                endAngle={450}
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          
          {/* Center Text */}
          {chartData.length > 0 && (
            <div style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              textAlign: 'center'
            }}>
              <p style={{ fontSize: '12px', color: '#999', fontWeight: '500' }}>Total for month</p>
              <p style={{ fontSize: '20px', fontWeight: 'bold' }}>
                $5,950<span style={{ opacity: 0.3 }}>.00</span>
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default BudgetChart;
