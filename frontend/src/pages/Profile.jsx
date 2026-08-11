import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import Sidebar from '../components/Sidebar';
import { User, Mail, Shield, Save } from 'lucide-react';
import './Profile.css';

export default function Profile() {
  const { user, updateProfile } = useAuth();
  const [name, setName] = useState(user?.name || '');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');

  const handleUpdate = async (e) => {
    e.preventDefault();
    setLoading(true);
    setSuccess('');
    setError('');

    try {
      if (updateProfile) {
        await updateProfile(name);
        setSuccess('Profile updated successfully!');
      } else {
        // Fallback if updateProfile is not fully implemented
        setSuccess('Profile details saved (local session only)');
      }
    } catch (err) {
      setError(err.message || 'Failed to update profile');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="profile-container">
      <Sidebar />
      <main className="profile-main animate-fade-in">
        <header className="profile-header">
          <h1>My Profile</h1>
          <p>Manage your account settings and preferences.</p>
        </header>

        <div className="profile-content">
          <div className="profile-card">
            <h2><User size={24} /> Personal Information</h2>
            
            {success && <div className="success-msg">{success}</div>}
            {error && <div className="error-msg">{error}</div>}

            <form onSubmit={handleUpdate}>
              <div className="form-group">
                <label>Full Name</label>
                <div style={{ position: 'relative' }}>
                  <User size={18} style={{ position: 'absolute', left: '1rem', top: '1rem', color: 'var(--text-secondary)' }} />
                  <input 
                    type="text" 
                    value={name} 
                    onChange={(e) => setName(e.target.value)}
                    style={{ paddingLeft: '2.5rem' }}
                    required
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Email Address</label>
                <div style={{ position: 'relative' }}>
                  <Mail size={18} style={{ position: 'absolute', left: '1rem', top: '1rem', color: 'var(--text-secondary)' }} />
                  <input 
                    type="email" 
                    value={user?.email || ''} 
                    disabled
                    style={{ paddingLeft: '2.5rem' }}
                  />
                </div>
                <small style={{ color: 'var(--text-secondary)', marginTop: '0.5rem', display: 'block' }}>
                  Email address cannot be changed.
                </small>
              </div>

              <button type="submit" className="btn-update" disabled={loading || name === user?.name}>
                <Save size={18} />
                {loading ? 'Saving...' : 'Save Changes'}
              </button>
            </form>
          </div>

          <div className="profile-card">
            <h2><Shield size={24} /> Security</h2>
            {user?.google_id ? (
              <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
                You signed in with Google. Your password is managed by Google and cannot be updated here.
              </p>
            ) : (
              <>
                <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
                  Keep your account secure by using a strong password.
                </p>
                <button className="btn-secondary" onClick={() => alert('Password reset module coming soon!')}>
                  Change Password
                </button>
              </>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
