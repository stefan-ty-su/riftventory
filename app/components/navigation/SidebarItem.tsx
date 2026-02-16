import React, { useEffect } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import Animated, {
  useAnimatedStyle,
  withTiming,
  withSpring,
  useSharedValue,
  Easing,
  interpolate,
} from 'react-native-reanimated';
import { useRouter, usePathname } from 'expo-router';
import * as Haptics from 'expo-haptics';
import { IconSymbol } from '@/components/ui/icon-symbol';
import { Colors, Sidebar as SidebarTheme, Typography, BorderRadius } from '@/constants/theme';
import { useSidebar } from './SidebarContext';

type SFSymbolName =
  | 'house.fill'
  | 'rectangle.grid.2x2.fill'
  | 'archivebox.fill'
  | 'arrow.left.arrow.right'
  | 'magnifyingglass'
  | 'person.circle.fill'
  | 'gearshape.fill';

interface SidebarItemProps {
  icon: SFSymbolName;
  label: string;
  href: string;
}

export function SidebarItem({ icon, label, href }: SidebarItemProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { isExpanded, closeMobileSidebar } = useSidebar();

  // Shared values for animations
  const scale = useSharedValue(1);
  const expandProgress = useSharedValue(isExpanded ? 1 : 0);

  // Check if this item is active (handle both /route and /route/subroute)
  const isActive = pathname === href || pathname.startsWith(`${href}/`);

  // Sync expand progress with isExpanded state
  useEffect(() => {
    expandProgress.value = withTiming(isExpanded ? 1 : 0, {
      duration: 200,
      easing: Easing.bezier(0.25, 0.1, 0.25, 1),
    });
  }, [isExpanded, expandProgress]);

  // Animated styles for scale on press
  const scaleStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }));

  // Animated styles for label fade
  const labelStyle = useAnimatedStyle(() => ({
    opacity: interpolate(expandProgress.value, [0, 0.5, 1], [0, 0, 1]),
    transform: [
      { translateX: interpolate(expandProgress.value, [0, 1], [-10, 0]) },
    ],
  }));

  const handlePressIn = () => {
    scale.value = withSpring(0.95, { damping: 15, stiffness: 300 });
  };

  const handlePressOut = () => {
    scale.value = withSpring(1, { damping: 15, stiffness: 300 });
  };

  const handlePress = () => {
    // Haptic feedback on iOS
    if (process.env.EXPO_OS === 'ios') {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    }

    // Close mobile sidebar before navigating
    closeMobileSidebar();

    // Navigate
    router.push(href as any);
  };

  return (
    <Animated.View style={scaleStyle}>
      <Pressable
        onPress={handlePress}
        onPressIn={handlePressIn}
        onPressOut={handlePressOut}
        style={({ pressed, hovered }) => [
          styles.container,
          isExpanded ? styles.containerExpanded : styles.containerCollapsed,
          isActive && styles.containerActive,
          (pressed || hovered) && !isActive && styles.containerHover,
        ]}
      >
        <View style={styles.iconContainer}>
          <IconSymbol
            name={icon}
            size={SidebarTheme.iconSize}
            color={isActive ? Colors.accent : Colors.textSecondary}
          />
        </View>

        {/* Label with fade animation - always rendered but animated */}
        <Animated.Text
          style={[
            styles.label,
            isActive && styles.labelActive,
            labelStyle,
            !isExpanded && styles.labelHidden,
          ]}
          numberOfLines={1}
        >
          {label}
        </Animated.Text>

        {/* Active indicator bar */}
        {isActive && <View style={styles.activeIndicator} />}
      </Pressable>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    height: SidebarTheme.itemHeight,
    borderRadius: BorderRadius.md,
    marginHorizontal: SidebarTheme.itemPadding,
    marginVertical: SidebarTheme.itemGap / 2,
    position: 'relative',
    overflow: 'hidden',
  },
  containerExpanded: {
    paddingHorizontal: SidebarTheme.itemPadding,
  },
  containerCollapsed: {
    justifyContent: 'center',
    paddingHorizontal: 0,
  },
  containerActive: {
    backgroundColor: Colors.sidebarItemActive,
  },
  containerHover: {
    backgroundColor: Colors.sidebarItemHover,
  },
  iconContainer: {
    width: SidebarTheme.iconSize + 16,
    height: SidebarTheme.iconSize,
    justifyContent: 'center',
    alignItems: 'center',
  },
  label: {
    flex: 1,
    fontSize: Typography.size.md,
    color: Colors.textSecondary,
    marginLeft: 4,
  },
  labelActive: {
    color: Colors.textPrimary,
    fontWeight: '600',
  },
  labelHidden: {
    position: 'absolute',
    width: 0,
    overflow: 'hidden',
  },
  activeIndicator: {
    position: 'absolute',
    left: 0,
    top: '20%',
    bottom: '20%',
    width: 3,
    backgroundColor: Colors.accent,
    borderRadius: 2,
  },
});