import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { User, Lock, ArrowRight, ArrowLeft, Briefcase } from 'lucide-react';
import logoImage from './assets/Logo.png';

const SignUpPage = () => {
  const [formData, setFormData] = useState({
    name: '',
    position: '',
    email: '',
    password: '',
    confirmPassword: ''
  });
  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSignUp = (e) => {
    e.preventDefault();
    // Simulate signup and navigate to login
    navigate('/login');
  };

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      backgroundColor: 'var(--bg-primary)',
      width: '100%',
      padding: '40px 20px'
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
          <form onSubmit={handleSignUp}>
            
            {/* Name - Surname Field */}
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: '700', marginBottom: '8px', color: 'var(--text-main)' }}>Name - Surname</label>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                backgroundColor: '#f3f4f6',
                borderRadius: '12px',
                padding: '10px 16px',
                border: '1px solid var(--border-color)'
              }}>
                <User size={18} color="var(--text-main)" style={{ marginRight: '12px' }} />
                <input 
                  type="text" 
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  placeholder="John Doe"
                  style={{
                    border: 'none',
                    background: 'transparent',
                    width: '100%',
                    outline: 'none',
                    fontSize: '13px',
                    color: 'var(--text-main)'
                  }}
                  required
                />
              </div>
            </div>

            {/* Position Field */}
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: '700', marginBottom: '8px', color: 'var(--text-main)' }}>Position</label>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                backgroundColor: '#f3f4f6',
                borderRadius: '12px',
                padding: '10px 16px',
                border: '1px solid var(--border-color)'
              }}>
                <Briefcase size={18} color="var(--text-main)" style={{ marginRight: '12px' }} />
                <input 
                  type="text" 
                  name="position"
                  value={formData.position}
                  onChange={handleChange}
                  placeholder="executive"
                  style={{
                    border: 'none',
                    background: 'transparent',
                    width: '100%',
                    outline: 'none',
                    fontSize: '13px',
                    color: 'var(--text-main)'
                  }}
                  required
                />
              </div>
            </div>

            {/* Email Field */}
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: '700', marginBottom: '8px', color: 'var(--text-main)' }}>Email</label>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                backgroundColor: '#f3f4f6',
                borderRadius: '12px',
                padding: '10px 16px',
                border: '1px solid var(--border-color)'
              }}>
                <User size={18} color="var(--text-main)" style={{ marginRight: '12px' }} />
                <input 
                  type="email" 
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="name@email.com"
                  style={{
                    border: 'none',
                    background: 'transparent',
                    width: '100%',
                    outline: 'none',
                    fontSize: '13px',
                    color: 'var(--text-main)'
                  }}
                  required
                />
              </div>
            </div>

            {/* Password Field */}
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: '700', marginBottom: '8px', color: 'var(--text-main)' }}>Password</label>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                backgroundColor: '#f3f4f6',
                borderRadius: '12px',
                padding: '10px 16px',
                border: '1px solid var(--border-color)'
              }}>
                <Lock size={18} color="var(--text-main)" style={{ marginRight: '12px' }} />
                <input 
                  type="password" 
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  placeholder="At least 8 characters"
                  style={{
                    border: 'none',
                    background: 'transparent',
                    width: '100%',
                    outline: 'none',
                    fontSize: '13px',
                    color: 'var(--text-main)'
                  }}
                  required
                />
              </div>
            </div>

            {/* Confirm Password Field */}
            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: '700', marginBottom: '8px', color: 'var(--text-main)' }}>Confirm Password</label>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                backgroundColor: '#f3f4f6',
                borderRadius: '12px',
                padding: '10px 16px',
                border: '1px solid var(--border-color)'
              }}>
                <Lock size={18} color="var(--text-main)" style={{ marginRight: '12px' }} />
                <input 
                  type="password" 
                  name="confirmPassword"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  placeholder="Re-enter password"
                  style={{
                    border: 'none',
                    background: 'transparent',
                    width: '100%',
                    outline: 'none',
                    fontSize: '13px',
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
              Sign Up <ArrowRight size={18} />
            </button>
          </form>

          {/* Footer Link */}
          <div style={{ textAlign: 'center', marginTop: '24px', fontSize: '14px' }}>
            <Link to="/login" style={{ color: '#0066cc', textDecoration: 'none', fontWeight: '600', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
              <ArrowLeft size={16} /> Back to Login
            </Link>
          </div>

        </div>
      </div>
    </div>
  );
};

export default SignUpPage;
