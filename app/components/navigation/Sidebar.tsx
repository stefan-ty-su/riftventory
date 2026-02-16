import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  Pressable,
  Platform,
} from 'react-native';
import Animated, {
  useAnimatedStyle,
  withTiming,
  useSharedValue,
  runOnJS,
  Easing,
} from 'react-native-reanimated';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import * as Haptics from 'expo-haptics';
import { IconSymbol } from '@/components/ui/icon-symbol';
import { Colors, Sidebar as SidebarTheme, Typography, BorderRadius } from '@/constants/theme';
import { useResponsive } from '@/hooks/useResponsive';
import { useSidebar } from './SidebarContext';
import { SidebarItem } from './SidebarItem';

// Navigation items configuration
const NAV_ITEMS = [
  { icon: 'rectangle.grid.2x2.fill' as const, label: 'Card Gallery', href: '/cards' },
  { icon: 'archivebox.fill' as const, label: 'Inventories', href: '/inventories' },
  { icon: 'arrow.left.arrow.right' as const, label: 'Trades', href: '/trades' },
  { icon: 'magnifyingglass' as const, label: 'User Search', href: '/users' },
];

const BOTTOM_ITEMS = [
  { icon: 'person.circle.fill' as const, label: 'Profile', href: '/profile' },
  { icon: 'gearshape.fill' as const, label: 'Settings', href: '/settings' },
];

// Minimum swipe distance to close sidebar
const CLOSE_SWIPE_THRESHOLD = 50;

export function Sidebar() {
  const insets = useSafeAreaInsets();
  const { isMobile } = useResponsive();
  const { isExpanded, isVisible, setVisible, toggleExpanded } = useSidebar();

  // Track swipe progress
  const swipeProgress = useSharedValue(0);

  // Trigger haptic feedback (must be called from JS thread)
  const triggerHaptic = () => {
    if (process.env.EXPO_OS === 'ios') {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    }
  };

  // Close sidebar (must be called from JS thread)
  const closeSidebar = () => {
    setVisible(false);
  };

  // Swipe gesture to close sidebar - swipe left to close
  const swipeToCloseGesture = Gesture.Pan()
    .activeOffsetX(-10) // Only activate on leftward swipes
    .failOffsetY([-20, 20]) // Fail if vertical movement is too large
    .onUpdate((event) => {
      swipeProgress.value = Math.min(0, event.translationX);
    })
    .onEnd((event) => {
      // Close sidebar if swipe exceeded threshold
      if (event.translationX < -CLOSE_SWIPE_THRESHOLD && event.velocityX < 0) {
        runOnJS(triggerHaptic)();
        runOnJS(closeSidebar)();
      }
      swipeProgress.value = 0;
    });

  // Animated width for desktop/tablet
  const animatedStyle = useAnimatedStyle(() => {
    const width = isExpanded ? SidebarTheme.expandedWidth : SidebarTheme.collapsedWidth;
    return {
      width: withTiming(width, {
        duration: 200,
        easing: Easing.bezier(0.25, 0.1, 0.25, 1),
      }),
    };
  }, [isExpanded]);

  // Mobile overlay animation
  const overlayStyle = useAnimatedStyle(() => {
    return {
      opacity: withTiming(isVisible ? 1 : 0, { duration: 200 }),
      pointerEvents: isVisible ? 'auto' : 'none',
    };
  }, [isVisible]);

  const mobileSlideStyle = useAnimatedStyle(() => {
    return {
      transform: [
        {
          translateX: withTiming(isVisible ? 0 : -SidebarTheme.expandedWidth, {
            duration: 250,
            easing: Easing.bezier(0.25, 0.1, 0.25, 1),
          }),
        },
      ],
    };
  }, [isVisible]);

  const handleBackdropPress = () => {
    setVisible(false);
  };

  // Mobile: Render as overlay
  if (isMobile) {
    return (
      <>
        {/* Backdrop */}
        <Animated.View style={[styles.backdrop, overlayStyle]}>
          <Pressable style={StyleSheet.absoluteFill} onPress={handleBackdropPress} />
        </Animated.View>

        {/* Sidebar with swipe-to-close gesture */}
        <GestureDetector gesture={swipeToCloseGesture}>
          <Animated.View
            style={[
              styles.container,
              styles.mobileContainer,
              mobileSlideStyle,
              { paddingTop: insets.top, paddingBottom: insets.bottom },
            ]}
          >
            <SidebarContent isExpanded={true} />
          </Animated.View>
        </GestureDetector>
      </>
    );
  }

  // Desktop/Tablet: Render inline
  return (
    <Animated.View
      style={[
        styles.container,
        animatedStyle,
        { paddingTop: insets.top, paddingBottom: insets.bottom },
      ]}
    >
      <SidebarContent
        isExpanded={isExpanded}
        showCollapseToggle={true}
        onToggleCollapse={toggleExpanded}
      />
    </Animated.View>
  );
}

interface SidebarContentProps {
  isExpanded: boolean;
  showCollapseToggle?: boolean;
  onToggleCollapse?: () => void;
}

function SidebarContent({ isExpanded, showCollapseToggle, onToggleCollapse }: SidebarContentProps) {
  const handleCollapsePress = () => {
    if (process.env.EXPO_OS === 'ios') {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    }
    onToggleCollapse?.();
  };

  return (
    <View style={styles.content}>
      {/* Header / Brand */}
      <View style={styles.header}>
        {isExpanded ? (
          <Text style={styles.brandText}>Riftventory</Text>
        ) : (
          <Text style={styles.brandIcon}>R</Text>
        )}
      </View>

      {/* Main Navigation */}
      <View style={styles.navSection}>
        {NAV_ITEMS.map((item) => (
          <SidebarItem
            key={item.href}
            icon={item.icon}
            label={item.label}
            href={item.href}
          />
        ))}
      </View>

      {/* Spacer */}
      <View style={styles.spacer} />

      {/* Bottom Section */}
      <View style={styles.bottomSection}>
        <View style={styles.divider} />
        {BOTTOM_ITEMS.map((item) => (
          <SidebarItem
            key={item.href}
            icon={item.icon}
            label={item.label}
            href={item.href}
          />
        ))}

        {/* Collapse Toggle (desktop/tablet only) */}
        {showCollapseToggle && (
          <>
            <View style={styles.collapseDivider} />
            <Pressable
              onPress={handleCollapsePress}
              style={({ pressed, hovered }) => [
                styles.collapseButton,
                isExpanded ? styles.collapseButtonExpanded : styles.collapseButtonCollapsed,
                (pressed || hovered) && styles.collapseButtonHover,
              ]}
            >
              <View style={styles.collapseIconContainer}>
                <IconSymbol
                  name={isExpanded ? 'chevron.left' : 'chevron.right'}
                  size={18}
                  color={Colors.textSecondary}
                />
              </View>
              {isExpanded && (
                <Text style={styles.collapseLabel}>Collapse</Text>
              )}
            </Pressable>
          </>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: Colors.sidebarBackground,
    borderRightWidth: 1,
    borderRightColor: Colors.sidebarBorder,
    height: '100%',
    ...Platform.select({
      web: {
        position: 'fixed' as any,
        left: 0,
        top: 0,
        bottom: 0,
        zIndex: 100,
      },
    }),
  },
  mobileContainer: {
    position: 'absolute',
    left: 0,
    top: 0,
    bottom: 0,
    width: SidebarTheme.expandedWidth,
    zIndex: 1001,
  },
  backdrop: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    zIndex: 1000,
  },
  content: {
    flex: 1,
  },
  header: {
    height: SidebarTheme.headerHeight,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: SidebarTheme.itemPadding,
  },
  brandText: {
    fontSize: Typography.size.xl,
    fontWeight: '700',
    color: Colors.accent,
    letterSpacing: -0.5,
  },
  brandIcon: {
    fontSize: Typography.size.xxl,
    fontWeight: '700',
    color: Colors.accent,
  },
  navSection: {
    paddingTop: SidebarTheme.sectionGap / 2,
  },
  spacer: {
    flex: 1,
  },
  bottomSection: {
    paddingBottom: SidebarTheme.itemPadding,
  },
  divider: {
    height: 1,
    backgroundColor: Colors.sidebarBorder,
    marginHorizontal: SidebarTheme.itemPadding,
    marginBottom: SidebarTheme.sectionGap / 2,
  },
  collapseDivider: {
    height: 1,
    backgroundColor: Colors.sidebarBorder,
    marginHorizontal: SidebarTheme.itemPadding,
    marginTop: SidebarTheme.sectionGap / 2,
    marginBottom: SidebarTheme.itemGap,
  },
  collapseButton: {
    flexDirection: 'row',
    alignItems: 'center',
    height: 40,
    borderRadius: BorderRadius.md,
    marginHorizontal: SidebarTheme.itemPadding,
  },
  collapseButtonExpanded: {
    paddingHorizontal: SidebarTheme.itemPadding,
  },
  collapseButtonCollapsed: {
    justifyContent: 'center',
  },
  collapseButtonHover: {
    backgroundColor: Colors.sidebarItemHover,
  },
  collapseIconContainer: {
    width: SidebarTheme.iconSize + 16,
    height: SidebarTheme.iconSize,
    justifyContent: 'center',
    alignItems: 'center',
  },
  collapseLabel: {
    fontSize: Typography.size.sm,
    color: Colors.textMuted,
    marginLeft: 4,
  },
});