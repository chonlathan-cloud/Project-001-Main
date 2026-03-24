import React, { useState, useEffect } from 'react';
import { PlusCircle, ArrowRight } from 'lucide-react';
import Loading from './components/Loading';

const ChatAIPage = () => {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setLoading(false);
    }, 1000);
    return () => clearTimeout(timer);
  }, []);

  if (loading) return <Loading />;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <h1 style={{ fontSize: '32px', marginBottom: '24px' }}>Chat AI</h1>

      <div className="card" style={{ 
        flex: 1, 
        backgroundColor: 'white', 
        position: 'relative',
        minHeight: '600px',
        display: 'flex',
        flexDirection: 'column'
      }}>
        
        {/* Chat Message Area (Empty for now) */}
        <div style={{ flex: 1, padding: '24px', overflowY: 'auto' }}>
        </div>

        {/* Input Area */}
        <div style={{ padding: '24px' }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            backgroundColor: '#e8e8e8',
            borderRadius: '24px',
            padding: '12px 20px',
            border: '1px solid #ccc'
          }}>
            <PlusCircle size={24} style={{ color: '#333', cursor: 'pointer', flexShrink: 0 }} />
            <input 
              type="text" 
              placeholder="" 
              style={{ 
                flex: 1, 
                backgroundColor: 'transparent', 
                border: 'none', 
                outline: 'none', 
                padding: '0 16px',
                fontSize: '16px',
                color: '#333'
              }} 
            />
            <ArrowRight size={24} style={{ color: '#333', cursor: 'pointer', flexShrink: 0 }} />
          </div>
        </div>

      </div>
    </div>
  );
};

export default ChatAIPage;
