import React, { useMemo } from 'react';
import { motion as Motion } from 'framer-motion';
import { Hammer, Wrench, HardHat, Pickaxe, Ruler, Drill } from 'lucide-react';
import logoImage from '../assets/Logo.png';

const ToolIcon = ({ icon, radius, duration, delay, color }) => {
  const IconComponent = icon;

  return (
    <Motion.div
      className="construction-animation-tool"
      style={{
        color: color,
        border: `1px solid ${color}44`,
        boxShadow: `0 4px 15px ${color}22`,
      }}
      animate={{
        rotate: 360,
        x: [
          Math.cos(0) * radius,
          Math.cos(Math.PI / 2) * radius,
          Math.cos(Math.PI) * radius,
          Math.cos(3 * Math.PI / 2) * radius,
          Math.cos(2 * Math.PI) * radius,
        ],
        y: [
          Math.sin(0) * radius,
          Math.sin(Math.PI / 2) * radius,
          Math.sin(Math.PI) * radius,
          Math.sin(3 * Math.PI / 2) * radius,
          Math.sin(2 * Math.PI) * radius,
        ],
      }}
      transition={{
        duration: duration,
        repeat: Infinity,
        ease: 'linear',
        delay: delay,
      }}
    >
      <IconComponent size={24} />
    </Motion.div>
  );
};

const ConstructionAnimation = () => {
  const tools = useMemo(() => [
    { icon: Hammer, radius: 92, duration: 25, delay: 0, color: '#c9a15c' },
    { icon: Wrench, radius: 128, duration: 35, delay: 5, color: '#bba684' },
    { icon: HardHat, radius: 108, duration: 45, delay: 10, color: '#8c6e3d' },
    { icon: Pickaxe, radius: 145, duration: 55, delay: 15, color: '#c9a15c' },
    { icon: Ruler, radius: 118, duration: 40, delay: 20, color: '#e6decb' },
    { icon: Drill, radius: 152, duration: 65, delay: 25, color: '#bba684' },
  ], []);

  const particles = useMemo(() => {
    return [...Array(12)].map((_, i) => ({
      x: [(i * 41) % 320 - 160, (i * 57 + 80) % 320 - 160],
      y: [(i * 49) % 320 - 160, (i * 63 + 120) % 320 - 160],
      duration: 15 + (i % 10),
    }));
  }, []);

  return (
    <div className="construction-animation" aria-hidden="true">
      <div className="construction-animation-glow" />

      {[92, 108, 124, 140, 156].map((r) => (
        <div
          key={r}
          className="construction-animation-ring"
          style={{ width: `${r * 2}px`, height: `${r * 2}px` }}
        />
      ))}

      <Motion.div
        className="construction-animation-logo"
        animate={{
          y: [-10, 10, -10],
          scale: [1, 1.04, 1],
        }}
        transition={{
          duration: 6,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      >
        <img src={logoImage} alt="RAYADEE" />
      </Motion.div>

      {tools.map((tool, index) => (
        <ToolIcon
          key={index}
          icon={tool.icon}
          radius={tool.radius}
          duration={tool.duration}
          delay={tool.delay}
          color={tool.color}
        />
      ))}

      {particles.map((p, i) => (
        <Motion.div
          key={i}
          className="construction-animation-particle"
          animate={{
            x: p.x,
            y: p.y,
            opacity: [0.1, 0.4, 0.1],
          }}
          transition={{
            duration: p.duration,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
      ))}
    </div>
  );
};


export default ConstructionAnimation;
