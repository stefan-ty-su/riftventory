/**
 * Below are the colors that are used in the app. The colors are defined in the light and dark mode.
 * There are many other ways to style your app. For example, [Nativewind](https://www.nativewind.dev/), [Tamagui](https://tamagui.dev/), [unistyles](https://reactnativeunistyles.vercel.app), etc.
 */

import { Platform } from 'react-native';

const tintColorLight = '#0a7ea4';
const tintColorDark = '#fff';

export const Colors = {
  light: {
    text: '#11181C',
    background: '#fff',
    tint: tintColorLight,
    icon: '#687076',
    tabIconDefault: '#687076',
    tabIconSelected: tintColorLight,
  },
  dark: {
    text: '#ECEDEE',
    background: '#151718',
    tint: tintColorDark,
    icon: '#9BA1A6',
    tabIconDefault: '#9BA1A6',
    tabIconSelected: tintColorDark,
  },
  // Core backgrounds
  background: '#0A0A0B',
  backgroundElevated: '#141416',
  backgroundCard: '#1A1A1E',
  backgroundCardHover: '#222226',
  
  // Surface colors
  surface: '#1E1E22',
  surfaceLight: '#2A2A2E',
  
  // Text colors
  textPrimary: '#F5F5F7',
  textSecondary: '#A1A1A6',
  textMuted: '#6E6E73',
  textAccent: '#F5A623',
  
  // Accent colors (amber/gold for that rare card feel)
  accent: '#F5A623',
  accentLight: '#FFD074',
  accentDark: '#C4841D',
  accentSubtle: 'rgba(245, 166, 35, 0.15)',
  
  // Rarity colors
  rarityCommon: '#8E8E93',
  rarityUncommon: '#5AC8FA',
  rarityRare: '#E056A0',
  rarityEpic: '#F5A623',
  rarityShowcase: '#FFF200',
  
  // Domain colors (matched to rune card art)
  domainFury: '#D62839',    // Red
  domainCalm: '#2D8F4E',    // Green
  domainChaos: '#7B2D8E',   // Purple
  domainOrder: '#D4A017',   // Gold
  domainBody: '#E07020',    // Orange
  domainMind: '#2574A9',    // Blue
  
  // UI elements
  border: '#2C2C2E',
  borderLight: '#3A3A3C',
  divider: '#1C1C1E',
  
  // Status
  success: '#34C759',
  error: '#FF453A',
  warning: '#FFD60A',
  
  // Gradients
  gradientStart: '#1A1A1E',
  gradientEnd: '#0A0A0B',
};

export const Fonts = Platform.select({
  ios: {
    /** iOS `UIFontDescriptorSystemDesignDefault` */
    sans: 'system-ui',
    /** iOS `UIFontDescriptorSystemDesignSerif` */
    serif: 'ui-serif',
    /** iOS `UIFontDescriptorSystemDesignRounded` */
    rounded: 'ui-rounded',
    /** iOS `UIFontDescriptorSystemDesignMonospaced` */
    mono: 'ui-monospace',
  },
  default: {
    sans: 'normal',
    serif: 'serif',
    rounded: 'normal',
    mono: 'monospace',
  },
  web: {
    sans: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
    serif: "Georgia, 'Times New Roman', serif",
    rounded: "'SF Pro Rounded', 'Hiragino Maru Gothic ProN', Meiryo, 'MS PGothic', sans-serif",
    mono: "SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
  },
});

export const Spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
  xxxl: 48,
};

export const BorderRadius = {
  sm: 6,
  md: 10,
  lg: 14,
  xl: 20,
  card: 12,
};

export const Typography = {
  // Font families (using system fonts with fallbacks)
  fontFamily: {
    regular: 'System',
    medium: 'System',
    bold: 'System',
  },
  // Font sizes
  size: {
    xs: 11,
    sm: 13,
    md: 15,
    lg: 17,
    xl: 20,
    xxl: 28,
    xxxl: 34,
    display: 48,
  },
  // Line heights
  lineHeight: {
    tight: 1.2,
    normal: 1.4,
    relaxed: 1.6,
  },
};

export const Shadows = {
  card: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  cardHover: {
    shadowColor: '#F5A623',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.25,
    shadowRadius: 16,
    elevation: 12,
  },
  subtle: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 4,
  },
};

// Domain color utilities (matched to rune card art)
export const DomainColors: Record<string, { primary: string; glow: string; text: string }> = {
  Fury: {
    primary: Colors.domainFury,
    glow: 'rgba(214, 40, 57, 0.4)',
    text: '#F25C69',
  },
  Calm: {
    primary: Colors.domainCalm,
    glow: 'rgba(45, 143, 78, 0.4)',
    text: '#5DBF7A',
  },
  Chaos: {
    primary: Colors.domainChaos,
    glow: 'rgba(123, 45, 142, 0.4)',
    text: '#A85DC2',
  },
  Order: {
    primary: Colors.domainOrder,
    glow: 'rgba(212, 160, 23, 0.4)',
    text: '#F0C040',
  },
  Body: {
    primary: Colors.domainBody,
    glow: 'rgba(224, 112, 32, 0.4)',
    text: '#F09050',
  },
  Mind: {
    primary: Colors.domainMind,
    glow: 'rgba(37, 116, 169, 0.4)',
    text: '#4A9FD4',
  },
};

export const getDomainColor = (domain: string | string[] | undefined | null) => {
  if (!domain) return DomainColors.Order; // Default fallback
  const domainKey = Array.isArray(domain) ? domain[0] : domain;
  return DomainColors[domainKey] || DomainColors.Order;
};

// Get colors for all domains in an array
export const getDomainColors = (domains: string[] | undefined | null) => {
  if (!domains || domains.length === 0) return [DomainColors.Order];
  return domains.map(d => DomainColors[d] || DomainColors.Order);
};

// Check if card has exactly two domains
export const isDualDomain = (domains: string[] | undefined | null): boolean => {
  return Array.isArray(domains) && domains.length === 2;
};