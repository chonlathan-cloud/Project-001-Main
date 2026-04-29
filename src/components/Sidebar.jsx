import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, FolderKanban, BarChart3, PenSquare, MessageSquare, Settings, User } from 'lucide-react';
import Logo from './Logo';

const Sidebar = () => {
  const [userName, setUserName] = useState('Loading...');

  useEffect(() => {
    // Simulate fetching user name from API/Login state
    const storedName = localStorage.getItem('userName');
    if (storedName) {
      setUserName(storedName);
    } else {
      setUserName('Guest User');
    }
  }, []);

  const navItems = [
    { name: 'Dashboard', icon: LayoutDashboard, path: '/' },
    { name: 'Project', icon: FolderKanban, path: '/project' },
    { name: 'Insights', icon: BarChart3, path: '/insights' },
    { name: 'Input', icon: PenSquare, path: '/input' },
    { name: 'Profile', icon: User, path: '/profile' },
    { name: 'Chat AI', icon: MessageSquare, path: '/chat-ai' },
    { name: 'Setting', icon: Settings, path: '/setting' },
  ];

  return (
    <aside style={{
      width: '240px',
      backgroundColor: 'var(--sidebar-bg)',
      color: 'white',
      display: 'flex',
      flexDirection: 'column',
      height: '100vh',
      position: 'sticky',
      top: 0,
      zIndex: 100
    }}>
      <div style={{ padding: '40px 0 20px 0', flex: 1, display: 'flex', flexDirection: 'column' }}>
        <Logo />
        
        <div style={{ padding: '0 20px', marginTop: '20px' }}>
          <p style={{ 
            fontSize: '11px', 
            fontWeight: '700', 
            color: 'var(--text-sidebar)', 
            letterSpacing: '1px',
            marginBottom: '16px',
            paddingLeft: '12px'
          }}>MANAGE</p>
          
          <nav style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {navItems.map((item) => (
              <NavLink 
                key={item.name} 
                to={item.path}
                style={({ isActive }) => ({
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  padding: '12px 16px',
                  borderRadius: '12px',
                  cursor: 'pointer',
                  backgroundColor: isActive ? 'var(--accent-gold)' : 'transparent',
                  color: isActive ? 'white' : 'var(--text-sidebar)',
                  transition: 'all 0.2s ease',
                  textDecoration: 'none'
                })}
              >
                <item.icon size={20} />
                <span style={{ fontWeight: '500', fontSize: '14px' }}>{item.name}</span>
              </NavLink>
            ))}
          </nav>
        </div>
      </div>

      {/* User Profile Section at Bottom */}
      <div style={{
        backgroundColor: 'var(--accent-gold)',
        padding: '20px',
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        color: 'var(--text-main)'
      }}>
        <div style={{
          width: '56px',
          height: '56px',
          borderRadius: '50%',
          backgroundColor: '#e2e2e2',
          flexShrink: 0
        }} />
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <span style={{ fontSize: '14px', fontWeight: '500', lineHeight: '1.2' }}>{userName}</span>
          <span style={{ fontSize: '14px', lineHeight: '1.2' }}>User</span>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
