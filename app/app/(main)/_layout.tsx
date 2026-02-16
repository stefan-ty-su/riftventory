import React from 'react';
import { View, StyleSheet } from 'react-native';
import Animated, {
  useAnimatedStyle,
  withTiming,
  Easing,
  useSharedValue,
  runOnJS,
} from 'react-native-reanimated';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import { Slot } from 'expo-router';
import * as Haptics from 'expo-haptics';
import { SidebarProvider, Sidebar, MobileHeader, useSidebar } from '@/components/navigation';
import { useResponsive } from '@/hooks/useResponsive';
import { Colors, Sidebar as SidebarTheme } from '@/constants/theme';

export default function MainLayout() {
  return (
    <SidebarProvider>
      <MainLayoutContent />
    </SidebarProvider>
  );
}

// Edge swipe threshold - how far from the left edge the swipe must start
const EDGE_WIDTH = 20;
// Minimum swipe distance to trigger sidebar open
const SWIPE_THRESHOLD = 50;

function MainLayoutContent() {
  const { isMobile } = useResponsive();
  const { isExpanded, setVisible, isVisible } = useSidebar();

  // Track swipe progress for potential future use (drag-to-reveal)
  const swipeProgress = useSharedValue(0);

  // Trigger haptic feedback (must be called from JS thread)
  const triggerHaptic = () => {
    if (process.env.EXPO_OS === 'ios') {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    }
  };

  // Open sidebar (must be called from JS thread)
  const openSidebar = () => {
    setVisible(true);
  };

  // Edge swipe gesture for mobile - swipe from left edge to open sidebar
  const edgeSwipeGesture = Gesture.Pan()
    .enabled(isMobile && !isVisible)
    .activeOffsetX(10) // Only activate on horizontal swipes
    .failOffsetY([-20, 20]) // Fail if vertical movement is too large
    .onStart((event) => {
      // Only respond to swipes starting from the left edge
      if (event.x > EDGE_WIDTH) {
        return;
      }
      swipeProgress.value = 0;
    })
    .onUpdate((event) => {
      // Only track swipes that started from the edge
      if (event.x - event.translationX > EDGE_WIDTH) {
        return;
      }
      swipeProgress.value = Math.max(0, event.translationX);
    })
    .onEnd((event) => {
      // Only respond to swipes that started from the edge
      if (event.x - event.translationX > EDGE_WIDTH) {
        swipeProgress.value = 0;
        return;
      }

      // Open sidebar if swipe exceeded threshold
      if (event.translationX > SWIPE_THRESHOLD && event.velocityX > 0) {
        runOnJS(triggerHaptic)();
        runOnJS(openSidebar)();
      }

      swipeProgress.value = 0;
    });

  // Animated margin for smooth sidebar collapse transition
  const contentStyle = useAnimatedStyle(() => {
    if (isMobile) {
      return { marginLeft: 0 };
    }

    const width = isExpanded ? SidebarTheme.expandedWidth : SidebarTheme.collapsedWidth;
    return {
      marginLeft: withTiming(width, {
        duration: 200,
        easing: Easing.bezier(0.25, 0.1, 0.25, 1),
      }),
    };
  }, [isMobile, isExpanded]);

  return (
    <View style={styles.container}>
      {/* Sidebar (renders as overlay on mobile) */}
      <Sidebar />

      {/* Main content area with edge swipe gesture */}
      <GestureDetector gesture={edgeSwipeGesture}>
        <Animated.View style={[styles.content, contentStyle]}>
          {/* Mobile header with hamburger */}
          {isMobile && <MobileHeader />}

          {/* Page content */}
          <View style={styles.pageContainer}>
            <Slot />
          </View>
        </Animated.View>
      </GestureDetector>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    flexDirection: 'row',
    backgroundColor: Colors.background,
  },
  content: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  pageContainer: {
    flex: 1,
  },
});