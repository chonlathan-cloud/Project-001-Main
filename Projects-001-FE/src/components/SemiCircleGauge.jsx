import React from 'react';

const defaultValueFormatter = (value) =>
  `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const SemiCircleGauge = ({
  value,
  max,
  size = 240,
  strokeWidth = 16,
  color = '#4f6f64',
  bgColor = '#c7eadc',
  label = 'spent',
  remainingLabel = 'left',
  valueFormatter = defaultValueFormatter,
}) => {
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * Math.PI;
  const percentage = max > 0 ? Math.min(value / max, 1) : 0;
  const offset = circumference - percentage * circumference;

  return (
    <div style={{ position: 'relative', width: size, height: size / 2 + 20, margin: '0 auto', display: 'flex', justifyContent: 'center' }}>
      <svg width={size} height={size / 2 + strokeWidth / 2} style={{ overflow: 'visible' }}>
        <path
          d={`M ${strokeWidth/2} ${size/2} A ${radius} ${radius} 0 0 1 ${size - strokeWidth/2} ${size/2}`}
          fill="none"
          stroke={bgColor}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        <path
          d={`M ${strokeWidth/2} ${size/2} A ${radius} ${radius} 0 0 1 ${size - strokeWidth/2} ${size/2}`}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 0.5s ease-in-out' }}
        />
      </svg>
      
      <div style={{ 
        position: 'absolute', 
        bottom: '0px', 
        left: '50%', 
        transform: 'translateX(-50%)', 
        textAlign: 'center' 
      }}>
        <div style={{ fontSize: '12px', color: '#888', marginBottom: '4px' }}>{Math.round(percentage * 100)}% {label}</div>
        <div style={{ fontSize: '24px', fontWeight: 'bold' }}>
          {valueFormatter(value)}
        </div>
      </div>
      
      {/* Left indicator text on the right side of the arc */}
      <div style={{ 
        position: 'absolute', 
        right: '0px', 
        top: '20px', 
        textAlign: 'right',
        backgroundColor: 'rgba(255,255,255,0.8)',
        padding: '2px 6px',
        borderRadius: '8px'
      }}>
        <div style={{ fontSize: '10px', color: '#888' }}>{Math.round((1 - percentage) * 100)}% {remainingLabel}</div>
        <div style={{ fontSize: '12px', fontWeight: 'bold' }}>{valueFormatter(Math.max(max - value, 0))}</div>
      </div>
    </div>
  );
};

export default SemiCircleGauge;
