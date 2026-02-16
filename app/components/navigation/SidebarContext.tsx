import React, { createContext, useContext, useState, useCallback, useEffect, ReactNode } from 'react';
import { useResponsive, SidebarMode } from '@/hooks/useResponsive';

interface SidebarContextValue {
  // State
  isExpanded: boolean;
  isVisible: boolean;
  sidebarMode: SidebarMode;

  // Actions
  toggleExpanded: () => void;
  toggleVisible: () => void;
  setExpanded: (expanded: boolean) => void;
  setVisible: (visible: boolean) => void;
  closeMobileSidebar: () => void;
}

const SidebarContext = createContext<SidebarContextValue | null>(null);

interface SidebarProviderProps {
  children: ReactNode;
}

export function SidebarProvider({ children }: SidebarProviderProps) {
  const { sidebarMode, isMobile } = useResponsive();

  // Expanded state (desktop can toggle between expanded/collapsed)
  const [isExpanded, setIsExpanded] = useState(sidebarMode === 'expanded');

  // Visible state (mobile overlay visibility)
  const [isVisible, setIsVisible] = useState(false);

  // Sync expanded state with screen size changes
  useEffect(() => {
    if (sidebarMode === 'expanded') {
      setIsExpanded(true);
    } else if (sidebarMode === 'collapsed') {
      setIsExpanded(false);
    }
  }, [sidebarMode]);

  // Close mobile sidebar when switching to desktop/tablet
  useEffect(() => {
    if (!isMobile) {
      setIsVisible(false);
    }
  }, [isMobile]);

  const toggleExpanded = useCallback(() => {
    setIsExpanded((prev) => !prev);
  }, []);

  const toggleVisible = useCallback(() => {
    setIsVisible((prev) => !prev);
  }, []);

  const setExpandedValue = useCallback((expanded: boolean) => {
    setIsExpanded(expanded);
  }, []);

  const setVisibleValue = useCallback((visible: boolean) => {
    setIsVisible(visible);
  }, []);

  const closeMobileSidebar = useCallback(() => {
    if (isMobile) {
      setIsVisible(false);
    }
  }, [isMobile]);

  const value: SidebarContextValue = {
    isExpanded,
    isVisible,
    sidebarMode,
    toggleExpanded,
    toggleVisible,
    setExpanded: setExpandedValue,
    setVisible: setVisibleValue,
    closeMobileSidebar,
  };

  return (
    <SidebarContext.Provider value={value}>
      {children}
    </SidebarContext.Provider>
  );
}

export function useSidebar(): SidebarContextValue {
  const context = useContext(SidebarContext);
  if (!context) {
    throw new Error('useSidebar must be used within a SidebarProvider');
  }
  return context;
}