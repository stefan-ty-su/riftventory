# Spotify-Style Sidebar Navigation Implementation Plan

## Overview

Convert the bottom tab navigation to a Spotify-style sidebar that works on both web and mobile. The sidebar will have navigation items at the top (Card Gallery, Inventories, Trades, User Search) and user items at the bottom (Profile, Settings).

**Approach:** Custom sidebar component using expo-router's `Slot` for content rendering. This gives full control over the Spotify-like design (top/bottom split, responsive collapse behavior).

## Responsive Behavior

| Screen Size | Sidebar Behavior |
|-------------|------------------|
| Desktop (≥1024px) | Expanded (240px), always visible |
| Tablet (768-1024px) | Collapsed (72px, icons only), always visible |
| Mobile (<768px) | Hidden, overlay with hamburger menu trigger |

## File Changes

### New Files

| File | Purpose |
|------|---------|
| `app/components/navigation/SidebarContext.tsx` | Sidebar state management (expanded/collapsed/visible) |
| `app/components/navigation/Sidebar.tsx` | Main sidebar component |
| `app/components/navigation/SidebarItem.tsx` | Individual nav item with icon + label |
| `app/components/navigation/MobileHeader.tsx` | Mobile header with hamburger menu |
| `app/hooks/useResponsive.ts` | Responsive breakpoint hook |
| `app/app/(main)/_layout.tsx` | New layout with sidebar + Slot |
| `app/app/(main)/index.tsx` | Home screen |
| `app/app/(main)/cards.tsx` | Card Gallery (move from tabs) |
| `app/app/(main)/inventories.tsx` | Inventories screen (new) |
| `app/app/(main)/trades.tsx` | Trades screen (new) |
| `app/app/(main)/users.tsx` | User Search screen (new) |
| `app/app/(main)/profile.tsx` | Profile screen (new) |
| `app/app/(main)/settings.tsx` | Settings screen (new) |

### Modified Files

| File | Changes |
|------|---------|
| `app/app/_layout.tsx` | Route to `(main)` instead of `(tabs)` when authenticated |
| `app/constants/theme.ts` | Add sidebar-specific colors and spacing |
| `app/components/ui/icon-symbol.tsx` | Add icon mappings for sidebar items |

### Files to Remove

| File | Reason |
|------|--------|
| `app/app/(tabs)/_layout.tsx` | Replaced by (main) layout |
| `app/app/(tabs)/index.tsx` | Moved to (main) |
| `app/app/(tabs)/explore.tsx` | Remove or merge content elsewhere |
| `app/app/(tabs)/cards.tsx` | Moved to (main) |

## Navigation Items

| Label | Route | SF Symbol | Material Icon |
|-------|-------|-----------|---------------|
| Card Gallery | `/cards` | `rectangle.grid.2x2.fill` | `grid-view` |
| Inventories | `/inventories` | `archivebox.fill` | `inventory-2` |
| Trades | `/trades` | `arrow.left.arrow.right` | `swap-horiz` |
| User Search | `/users` | `magnifyingglass` | `search` |
| Profile | `/profile` | `person.circle.fill` | `account-circle` |
| Settings | `/settings` | `gearshape.fill` | `settings` |

## Implementation Steps

### Phase 1: Foundation

1. **Create `app/hooks/useResponsive.ts`**
   - Hook returning `isMobile`, `isTablet`, `isDesktop`, `sidebarWidth`, `sidebarMode`

2. **Create `app/components/navigation/SidebarContext.tsx`**
   - Context with `isExpanded`, `isVisible`, toggle functions
   - Auto-expand on desktop, auto-collapse on tablet

3. **Update `app/constants/theme.ts`**
   - Add sidebar colors: `sidebarBackground`, `sidebarItemHover`, `sidebarItemActive`
   - Add spacing: `sidebarExpanded: 240`, `sidebarCollapsed: 72`, `sidebarItemHeight: 48`

4. **Update `app/components/ui/icon-symbol.tsx`**
   - Add mappings for all sidebar icons

### Phase 2: Sidebar Components

5. **Create `app/components/navigation/SidebarItem.tsx`**
   - Props: `icon`, `label`, `href`, `isActive`, `isExpanded`
   - Use `usePathname()` for active state
   - Use `router.push()` for navigation
   - Animated scale on press

6. **Create `app/components/navigation/Sidebar.tsx`**
   - Top section: Logo/brand + main nav items
   - Bottom section: Profile + Settings
   - Animated width transition
   - Fixed position on left

7. **Create `app/components/navigation/MobileHeader.tsx`**
   - Hamburger button that toggles sidebar visibility
   - Current page title

### Phase 3: Layout Integration

8. **Create `app/app/(main)/_layout.tsx`**
   - Wrap with `SidebarProvider`
   - Row layout: Sidebar + Content (using `Slot`)
   - Mobile: Overlay sidebar with backdrop
   - Use `SafeAreaView` for proper insets

9. **Create screen files in `app/app/(main)/`**
   - Move `cards.tsx` from (tabs)
   - Create placeholder screens for: `index.tsx`, `inventories.tsx`, `trades.tsx`, `users.tsx`, `profile.tsx`, `settings.tsx`

10. **Update `app/app/_layout.tsx`**
    - Change route from `/(tabs)` to `/(main)`
    - Update Stack.Screen name

11. **Remove `app/app/(tabs)/` directory**

### Phase 4: Polish

12. **Add animations with Reanimated**
    - Sidebar width transition (200ms)
    - Mobile slide-in (250ms)
    - Label fade on expand/collapse

13. **Add gesture support for mobile**
    - Swipe from left edge to open
    - Tap backdrop to close

14. **Add haptic feedback**
    - Use existing HapticTab pattern for sidebar items

## Verification

1. **Desktop (≥1024px):** Sidebar expanded, all labels visible, clicking items navigates correctly
2. **Tablet (768-1024px):** Sidebar collapsed (icons only), hover shows tooltips or labels
3. **Mobile (<768px):** No sidebar visible initially, hamburger menu opens overlay sidebar
4. **Navigation:** Each nav item routes to correct screen, active state highlights correctly
5. **Authentication:** Sidebar only appears when authenticated, not on login/signup screens
6. **Web:** Hover states work, no mobile-specific behaviors
7. **iOS/Android:** Gestures work, haptic feedback on item press