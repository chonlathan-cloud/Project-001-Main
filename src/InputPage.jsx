import React, { useState, useEffect } from 'react';
import { ArrowUp } from 'lucide-react';
import Loading from './components/Loading';

const InputField = ({ label, placeholder, type = 'text', style = {} }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', ...style }}>
    {label && <label style={{ fontSize: '14px', fontWeight: '600', color: '#1a1a1a' }}>{label}</label>}
    <input 
      type={type}
      placeholder={placeholder}
      style={{
        width: '100%',
        padding: '8px 16px',
        borderRadius: '12px',
        backgroundColor: '#e6decb',
        border: '1px solid #bba684',
        fontSize: '14px',
        outline: 'none',
        textAlign: 'center',
        color: '#333'
      }}
    />
  </div>
);

const SelectField = ({ label, placeholder, style = {} }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', ...style }}>
    {label && <label style={{ fontSize: '14px', fontWeight: '600', color: '#1a1a1a' }}>{label}</label>}
    <select 
      style={{
        width: '100%',
        padding: '8px 16px',
        borderRadius: '12px',
        backgroundColor: '#e6decb',
        border: '1px solid #bba684',
        fontSize: '14px',
        outline: 'none',
        textAlign: 'center',
        appearance: 'none',
        color: '#666',
        cursor: 'pointer'
      }}
    >
      <option value="">{placeholder}</option>
    </select>
  </div>
);

const InputPage = () => {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setLoading(false);
    }, 1000);
    return () => clearTimeout(timer);
  }, []);

  if (loading) return <Loading />;

  return (
    <>
      <h1 style={{ fontSize: '32px', marginBottom: '24px' }}>Input</h1>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
        
        {/* Left Side: Form Container */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          
          {/* Main Form Card */}
          <div className="card" style={{ 
            backgroundColor: 'white', 
            padding: '32px 24px', 
            display: 'flex', 
            flexDirection: 'column', 
            gap: '20px' 
          }}>
            
            <SelectField label="รายจ่าย / รายรับ" placeholder="เลือกรายการที่ทำ" style={{ width: '60%' }} />
            <SelectField label="โครงการ" placeholder="กรุณาเลือกโครงการ" style={{ width: '60%' }} />
            <InputField label="ชื่อ - นามสกุล" placeholder="กรุณากรอกชื่อ-นามสกุล" style={{ width: '60%' }} />
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
              <InputField label="เบอร์ติดต่อ" placeholder="กรุณากรอกเบอร์โทรศัพท์" />
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <label style={{ fontSize: '14px', fontWeight: '600', color: '#1a1a1a' }}>วัน/เดือน/ปี</label>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <SelectField placeholder="วัน" style={{ flex: 1 }} />
                  <SelectField placeholder="เดือน" style={{ flex: 1.5 }} />
                  <SelectField placeholder="ปี" style={{ flex: 1 }} />
                </div>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
              <SelectField label="ประเภทงาน" placeholder="กรุณาเลือก" />
              <SelectField label="ประเภทการเบิก" placeholder="กรุณาเลือก" />
            </div>

            <InputField label="อื่น ๆ" placeholder="ถ้ามี กรุณากรอกรายละเอียด" style={{ width: '60%' }} />

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
              <InputField label="บัญชีธนาคาร" placeholder="กรุณากรอก" />
              <InputField label="จำนวนเงินที่ขอเบิก" placeholder="กรุณากรอก" />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '8px' }}>
              <label style={{ fontSize: '14px', fontWeight: '600', color: '#1a1a1a' }}>Upload Image</label>
              <div style={{
                width: '100%',
                height: '140px',
                backgroundColor: '#e6decb',
                border: '1px solid #bba684',
                borderRadius: '12px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                cursor: 'pointer'
              }}>
                <span style={{ fontSize: '14px', fontWeight: '500' }}>Upload Image bank bill</span>
                <ArrowUp size={16} />
              </div>
            </div>

          </div>

          {/* Submit Button */}
          <div style={{ display: 'flex', justifyContent: 'center' }}>
            <button style={{
              backgroundColor: '#c9a15c',
              color: 'black',
              border: '1px solid #8c6e3d',
              borderRadius: '12px',
              padding: '12px 48px',
              fontSize: '20px',
              fontWeight: '700',
              cursor: 'pointer',
              width: '120px',
              boxShadow: 'var(--shadow-sm)'
            }}>
              ส่ง
            </button>
          </div>

        </div>

        {/* Right Side: Empty Card */}
        <div className="card" style={{ backgroundColor: 'white', minHeight: '800px' }}></div>
        
      </div>
    </>
  );
};

export default InputPage;
