import React from 'react';

const CircularProgress = ({
  value,
  max,
  size = 80,
  strokeWidth = 8,
  color = '#4f6f64',
  bgColor = '#c7eadc',
  label = 'spent',
}) => {
  const safeValue = Number.isFinite(Number(value)) ? Number(value) : 0;
  const safeMax = Number.isFinite(Number(max)) ? Number(max) : 0;
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const rawPercentage = safeMax > 0 ? (safeValue / safeMax) * 100 : 0;
  const percentage = Math.min(rawPercentage / 100, 1);
  const offset = circumference - percentage * circumference;
  const percentageLabel = rawPercentage > 100
    ? '100%+'
    : `${rawPercentage.toLocaleString('en-US', {
        minimumFractionDigits: rawPercentage > 0 && rawPercentage < 100 ? 1 : 0,
        maximumFractionDigits: 1,
      })}%`;

  return (
    <div style={{ position: 'relative', width: size, height: size, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
      <svg width={size} height={size}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={bgColor}
          strokeWidth={strokeWidth}
          fill="none"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={color}
          strokeWidth={strokeWidth}
          fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transform: 'rotate(-90deg)', transformOrigin: '50% 50%', transition: 'stroke-dashoffset 0.5s ease-in-out' }}
        />
      </svg>
      <div
        style={{
          position: 'absolute',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          width: size - strokeWidth * 3,
          textAlign: 'center',
          color: '#333',
          pointerEvents: 'none',
        }}
      >
        <span
          style={{
            color,
            fontSize: '14px',
            fontWeight: 'bold',
            lineHeight: 1.1,
            whiteSpace: 'nowrap',
          }}
        >
          {percentageLabel}
        </span>
        <span
          style={{
            marginTop: '3px',
            color: '#888',
            fontSize: '10px',
            fontWeight: 700,
            lineHeight: 1.15,
            textTransform: 'lowercase',
            whiteSpace: 'nowrap',
          }}
        >
          {label}
        </span>
      </div>
    </div>
  );
};

export default CircularProgress;
