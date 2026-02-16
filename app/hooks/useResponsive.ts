import { useWindowDimensions } from 'react-native';

// Breakpoints matching the sidebar navigation plan
const BREAKPOINTS = {
  mobile: 768,
  tablet: 1024,
} as const;

// Sidebar dimensions
const SIDEBAR_WIDTH = {
  expanded: 240,
  collapsed: 72,
} as const;

export type SidebarMode = 'expanded' | 'collapsed' | 'hidden';

export interface ResponsiveState {
  // Screen size flags
  isMobile: boolean;
  isTablet: boolean;
  isDesktop: boolean;

  // Sidebar specific
  sidebarWidth: number;
  sidebarMode: SidebarMode;

  // Raw dimensions
  screenWidth: number;
  screenHeight: number;
}

/**
 * Hook for responsive breakpoints and sidebar behavior.
 *
 * Breakpoints:
 * - Desktop (≥1024px): Sidebar expanded (240px), always visible
 * - Tablet (768-1024px): Sidebar collapsed (72px, icons only), always visible
 * - Mobile (<768px): Sidebar hidden, overlay with hamburger menu
 */
export function useResponsive(): ResponsiveState {
  const { width: screenWidth, height: screenHeight } = useWindowDimensions();

  const isMobile = screenWidth < BREAKPOINTS.mobile;
  const isTablet = screenWidth >= BREAKPOINTS.mobile && screenWidth < BREAKPOINTS.tablet;
  const isDesktop = screenWidth >= BREAKPOINTS.tablet;

  // Determine sidebar mode based on screen size
  let sidebarMode: SidebarMode;
  let sidebarWidth: number;

  if (isDesktop) {
    sidebarMode = 'expanded';
    sidebarWidth = SIDEBAR_WIDTH.expanded;
  } else if (isTablet) {
    sidebarMode = 'collapsed';
    sidebarWidth = SIDEBAR_WIDTH.collapsed;
  } else {
    sidebarMode = 'hidden';
    sidebarWidth = 0;
  }

  return {
    isMobile,
    isTablet,
    isDesktop,
    sidebarWidth,
    sidebarMode,
    screenWidth,
    screenHeight,
  };
}

// Export constants for use elsewhere
export { BREAKPOINTS, SIDEBAR_WIDTH };