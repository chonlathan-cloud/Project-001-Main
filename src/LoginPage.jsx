import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { User, Lock, ArrowRight } from 'lucide-react';
import logoImage from './assets/Logo.png';

const LoginPage = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const navigate = useNavigate();

  const handleLogin = (e) => {
    e.preventDefault();
    // Simulate login
    localStorage.setItem('isAuthenticated', 'true');
    const nameFromEmail = email.split('@')[0] || 'User';
    localStorage.setItem('userName', nameFromEmail);
    // Navigate to dashboard
    navigate('/');
    // Force a reload to update App state if needed, but since we are handling state in App it might be better to pass a prop or just rely on state. Actually window.location.href = '/' is simpler if we don't have global state.
    window.location.href = '/';
  };

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      backgroundColor: 'var(--bg-primary)',
      width: '100%',
      padding: '20px'
    }}>
      <div style={{
        backgroundColor: 'var(--card-bg)',
        borderRadius: '32px',
        width: '100%',
        maxWidth: '420px',
        border: '1px solid var(--border-color)',
        boxShadow: '0 10px 40px rgba(0,0,0,0.05)',
        overflow: 'hidden'
      }}>
        
        {/* Logo Section */}
        <div style={{ 
          display: 'flex', 
          justifyContent: 'center', 
          padding: '40px 0',
          borderBottom: '1px solid var(--border-color)'
        }}>
          <img src={logoImage} alt="DOUBLEBO" style={{ height: '110px', objectFit: 'contain' }} />
        </div>

        {/* Form Section */}
        <div style={{ padding: '32px' }}>
          <form onSubmit={handleLogin}>
            
            {/* Email Field */}
            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'block', fontSize: '14px', fontWeight: '700', marginBottom: '8px', color: 'var(--text-main)' }}>Email</label>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                backgroundColor: '#f3f4f6',
                borderRadius: '12px',
                padding: '12px 16px',
                border: '1px solid var(--border-color)'
              }}>
                <User size={18} color="var(--text-main)" style={{ marginRight: '12px' }} />
                <input 
                  type="email" 
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@email.com"
                  style={{
                    border: 'none',
                    background: 'transparent',
                    width: '100%',
                    outline: 'none',
                    fontSize: '14px',
                    color: 'var(--text-main)'
                  }}
                  required
                />
              </div>
            </div>

            {/* Password Field */}
            <div style={{ marginBottom: '32px' }}>
              <label style={{ display: 'block', fontSize: '14px', fontWeight: '700', marginBottom: '8px', color: 'var(--text-main)' }}>Password</label>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                backgroundColor: '#f3f4f6',
                borderRadius: '12px',
                padding: '12px 16px',
                border: '1px solid var(--border-color)'
              }}>
                <Lock size={18} color="var(--text-main)" style={{ marginRight: '12px' }} />
                <input 
                  type="password" 
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  style={{
                    border: 'none',
                    background: 'transparent',
                    width: '100%',
                    outline: 'none',
                    fontSize: '14px',
                    color: 'var(--text-main)'
                  }}
                  required
                />
              </div>
            </div>

            {/* Submit Button */}
            <button 
              type="submit"
              style={{
                width: '100%',
                backgroundColor: 'var(--accent-gold)',
                color: 'var(--text-main)',
                border: 'none',
                borderRadius: '12px',
                padding: '14px',
                fontSize: '16px',
                fontWeight: '700',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                transition: 'opacity 0.2s ease'
              }}
              onMouseOver={(e) => e.currentTarget.style.opacity = '0.9'}
              onMouseOut={(e) => e.currentTarget.style.opacity = '1'}
            >
              sign in <ArrowRight size={18} />
            </button>
          </form>

          {/* Footer Link */}
          <div style={{ textAlign: 'center', marginTop: '32px', fontSize: '14px', color: 'var(--text-main)' }}>
            Don't have an account? <Link to="/signup" style={{ color: '#0066cc', textDecoration: 'none', fontWeight: '500' }}>Sign Up</Link>
          </div>

        </div>
      </div>
    </div>
  );
};

export default LoginPage;
