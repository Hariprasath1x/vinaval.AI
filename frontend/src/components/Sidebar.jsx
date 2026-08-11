import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { LayoutDashboard, FileText, User, LogOut } from 'lucide-react';

export default function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const { logout } = useAuth();

  const isActive = (path) => location.pathname === path;

  return (
    <aside className="dashboard-sidebar">
      <div className="sidebar-brand">
        <div className="brand-logo">VA</div>
        <h2>Vinaval AI</h2>
      </div>
      
      <nav className="sidebar-nav">
        <button 
          className={`nav-item ${isActive('/dashboard') ? 'active' : ''}`}
          onClick={() => navigate('/dashboard')}
        >
          <LayoutDashboard size={20} />
          <span>Learning Spaces</span>
        </button>
        <button 
          className={`nav-item ${isActive('/mock-tests') ? 'active' : ''}`}
          onClick={() => navigate('/mock-tests')}
        >
          <FileText size={20} />
          <span>Mock Tests</span>
        </button>
        <button 
          className={`nav-item ${isActive('/profile') ? 'active' : ''}`}
          onClick={() => navigate('/profile')}
        >
          <User size={20} />
          <span>Profile</span>
        </button>
      </nav>

      <div className="sidebar-footer">
        <button className="nav-item text-danger" onClick={logout}>
          <LogOut size={20} />
          <span>Logout</span>
        </button>
      </div>
    </aside>
  );
}
