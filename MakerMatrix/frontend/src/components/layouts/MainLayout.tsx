import React, { useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import {
  Menu,
  X,
  Package,
  MapPin,
  Tags,
  Users,
  Home,
  LogOut,
  ChevronRight,
  Cpu,
  Binary,
  Code2,
  Terminal,
  CircuitBoard,
  Settings
} from 'lucide-react';
import { useAuthStore } from '../../store/authStore';
import { motion, AnimatePresence } from 'framer-motion';
import { clsx } from 'clsx';
import QuakeConsole from '../console/QuakeConsole';

interface NavItem {
  label: string;
  path: string;
  icon: React.ReactNode;
  children?: NavItem[];
}

const MainLayout: React.FC = () => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [expandedItems, setExpandedItems] = useState<string[]>([]);
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout, hasRole } = useAuthStore();

  const navItems: NavItem[] = [
    {
      label: 'Dashboard',
      path: '/',
      icon: <Home className="w-5 h-5" />
    },
    {
      label: 'Parts',
      path: '/parts',
      icon: <CircuitBoard className="w-5 h-5" />
    },
    {
      label: 'Locations',
      path: '/locations',
      icon: <MapPin className="w-5 h-5" />
    },
    {
      label: 'Categories',
      path: '/categories',
      icon: <Tags className="w-5 h-5" />
    },
    {
      label: 'Settings',
      path: '/settings',
      icon: <Settings className="w-5 h-5" />
    }
  ];

  // Admin-only nav items
  if (hasRole('Admin')) {
    navItems.push({
      label: 'Users',
      path: '/users',
      icon: <Users className="w-5 h-5" />
    });
  }

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/login');
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  const toggleExpanded = (path: string) => {
    setExpandedItems(prev =>
      prev.includes(path)
        ? prev.filter(item => item !== path)
        : [...prev, path]
    );
  };

  const isActive = (path: string) => {
    return location.pathname === path || location.pathname.startsWith(path + '/');
  };

  const renderNavItem = (item: NavItem, depth = 0) => {
    const hasChildren = item.children && item.children.length > 0;
    const isExpanded = expandedItems.includes(item.path);
    const active = isActive(item.path);

    return (
      <div key={item.path}>
        <div
          className={clsx(
            'flex items-center justify-between px-4 py-3 cursor-pointer transition-all duration-200',
            'hover:bg-primary-10',
            active && 'bg-primary-20 border-l-4 border-primary',
            depth > 0 && 'pl-8'
          )}
          onClick={() => {
            if (hasChildren) {
              toggleExpanded(item.path);
            } else {
              navigate(item.path);
            }
          }}
        >
          <div className="flex items-center space-x-3">
            <div className={clsx(
              'transition-colors duration-200',
              active ? 'text-primary-accent' : 'text-theme-secondary'
            )}>
              {item.icon}
            </div>
            {isSidebarOpen && (
              <span className={clsx(
                'font-medium transition-colors duration-200',
                active ? 'text-theme-primary' : 'text-theme-secondary'
              )}>
                {item.label}
              </span>
            )}
          </div>
          {hasChildren && isSidebarOpen && (
            <motion.div
              animate={{ rotate: isExpanded ? 90 : 0 }}
              transition={{ duration: 0.2 }}
              className="text-theme-secondary"
            >
              <ChevronRight className="w-4 h-4" />
            </motion.div>
          )}
        </div>
        
        <AnimatePresence>
          {hasChildren && isExpanded && isSidebarOpen && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              {item.children!.map(child => renderNavItem(child, depth + 1))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-theme-secondary text-theme-primary transition-colors duration-300">
      {/* Battle With Bytes Themed Background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 left-0 w-96 h-96 bg-purple-600/10 dark:bg-purple-600/20 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-0 right-0 w-96 h-96 bg-blue-600/10 dark:bg-blue-600/20 rounded-full blur-3xl animate-pulse" />
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-gradient-to-r from-purple-600/5 dark:from-purple-600/10 to-blue-600/5 dark:to-blue-600/10 rounded-full blur-3xl" />
      </div>

      {/* Sidebar */}
      <motion.aside
        initial={false}
        animate={{ width: isSidebarOpen ? 280 : 80 }}
        transition={{ duration: 0.3, ease: 'easeInOut' }}
        className="fixed left-0 top-0 h-full bg-theme-primary/80 backdrop-blur-xl border-r border-theme-primary z-20"
      >
        {/* Logo/Header */}
        <div className="h-20 flex items-center justify-between px-4 border-b border-theme-primary">
          <div className="flex items-center space-x-3">
            <div className="relative">
              <Cpu className="w-8 h-8 text-purple-500" />
              <Binary className="w-4 h-4 text-blue-500 absolute -bottom-1 -right-1" />
            </div>
            {isSidebarOpen && (
              <div>
                <h1 className="text-xl font-bold bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent font-theme-display">
                  MakerMatrix
                </h1>
                <p className="text-xs text-theme-muted">Battle With Bytes</p>
              </div>
            )}
          </div>
          <button
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            className="p-2 rounded-lg hover:bg-theme-secondary transition-colors"
          >
            {isSidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>

        {/* Navigation */}
        <nav className="mt-8 flex-1">
          {navItems.map(item => renderNavItem(item))}
        </nav>

        {/* User Section */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-theme-primary">
          <div className="flex items-center justify-between">
            <div className={clsx(
              'flex items-center space-x-3',
              !isSidebarOpen && 'justify-center'
            )}>
              <div className="w-8 h-8 rounded-full bg-gradient-to-r from-purple-500 to-blue-500 flex items-center justify-center">
                <span className="text-sm font-medium">
                  {user?.username?.charAt(0).toUpperCase()}
                </span>
              </div>
              {isSidebarOpen && (
                <div>
                  <p className="text-sm font-medium">{user?.username}</p>
                  <p className="text-xs text-theme-muted">{user?.roles?.[0]?.name || 'No Role'}</p>
                </div>
              )}
            </div>
            {isSidebarOpen && (
              <button
                onClick={handleLogout}
                className="p-2 rounded-lg hover:bg-theme-secondary transition-colors text-theme-secondary hover:text-error"
              >
                <LogOut className="w-5 h-5" />
              </button>
            )}
          </div>
        </div>
      </motion.aside>

      {/* Main Content */}
      <main
        className={clsx(
          'min-h-screen transition-all duration-300 relative z-10',
          isSidebarOpen ? 'ml-[280px]' : 'ml-20'
        )}
      >
        {/* Top Bar */}
        <header className="h-20 bg-theme-primary/50 backdrop-blur-lg border-b border-theme-primary px-8 flex items-center justify-between">
          <div className="flex items-center space-x-2 text-theme-secondary">
        
          </div>
          <div className="flex items-center space-x-4">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            <span className="text-sm text-theme-muted">
              {new Date().toLocaleString()}
            </span>
          </div>
        </header>

        {/* Page Content */}
        <div className="p-8">
          <Outlet />
        </div>
      </main>

      {/* Quake Console */}
      <QuakeConsole />
    </div>
  );
};

export default MainLayout;