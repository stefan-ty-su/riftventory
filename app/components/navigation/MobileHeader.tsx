import React from 'react';
import { View, Text, StyleSheet, Pressable } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { usePathname } from 'expo-router';
import * as Haptics from 'expo-haptics';
import { IconSymbol } from '@/components/ui/icon-symbol';
import { Colors, Spacing, Typography } from '@/constants/theme';
import { useSidebar } from './SidebarContext';

// Map routes to page titles
const ROUTE_TITLES: Record<string, string> = {
  '/': 'Home',
  '/cards': 'Card Gallery',
  '/inventories': 'Inventories',
  '/trades': 'Trades',
  '/users': 'User Search',
  '/profile': 'Profile',
  '/settings': 'Settings',
};

export function MobileHeader() {
  const insets = useSafeAreaInsets();
  const pathname = usePathname();
  const { toggleVisible } = useSidebar();

  // Get page title from pathname
  const title = ROUTE_TITLES[pathname] || 'Riftventory';

  const handleMenuPress = () => {
    if (process.env.EXPO_OS === 'ios') {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    }
    toggleVisible();
  };

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      <View style={styles.content}>
        {/* Hamburger Menu Button */}
        <Pressable
          onPress={handleMenuPress}
          style={({ pressed }) => [
            styles.menuButton,
            pressed && styles.menuButtonPressed,
          ]}
        >
          <IconSymbol
            name="line.3.horizontal"
            size={24}
            color={Colors.textPrimary}
          />
        </Pressable>

        {/* Page Title */}
        <Text style={styles.title} numberOfLines={1}>
          {title}
        </Text>

        {/* Spacer for balance */}
        <View style={styles.spacer} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: Colors.sidebarBackground,
    borderBottomWidth: 1,
    borderBottomColor: Colors.sidebarBorder,
  },
  content: {
    flexDirection: 'row',
    alignItems: 'center',
    height: 56,
    paddingHorizontal: Spacing.md,
  },
  menuButton: {
    width: 44,
    height: 44,
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: 8,
  },
  menuButtonPressed: {
    backgroundColor: Colors.sidebarItemHover,
  },
  title: {
    flex: 1,
    fontSize: Typography.size.lg,
    fontWeight: '600',
    color: Colors.textPrimary,
    textAlign: 'center',
    marginHorizontal: Spacing.md,
  },
  spacer: {
    width: 44,
  },
});