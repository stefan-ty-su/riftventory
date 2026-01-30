import React, { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { useRouter } from 'expo-router';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TextInput,
  Pressable,
  Animated,
  ActivityIndicator,
  Platform,
  SafeAreaView,
  StatusBar,
  RefreshControl,
  useWindowDimensions,
} from 'react-native';
import CardItem, { Card } from '../../components/CardItem';
import {
  Colors,
  Spacing,
  BorderRadius,
  Typography,
  Shadows,
  DomainColors,
} from '../../constants/theme';

// Filter options
type Rarity = 'Common' | 'Uncommon' | 'Rare' | 'Epic' | 'Showcase';
type Domain = 'Fury' | 'Calm' | 'Chaos' | 'Order' | 'Body' | 'Mind';
type SortOption = 'card_id' | 'name' | 'rarity' | 'number' | 'set';

// Pagination constants
const PAGE_SIZE = 24;

interface FilterChipProps {
  label: string;
  isActive: boolean;
  onPress: () => void;
  color?: string;
}

const FilterChip: React.FC<FilterChipProps> = ({ label, isActive, onPress, color }) => {
  const scaleAnim = useRef(new Animated.Value(1)).current;

  const handlePressIn = () => {
    Animated.spring(scaleAnim, {
      toValue: 0.95,
      friction: 8,
      useNativeDriver: true,
    }).start();
  };

  const handlePressOut = () => {
    Animated.spring(scaleAnim, {
      toValue: 1,
      friction: 8,
      useNativeDriver: true,
    }).start();
  };

  return (
    <Animated.View style={{ transform: [{ scale: scaleAnim }] }}>
      <Pressable
        onPress={onPress}
        onPressIn={handlePressIn}
        onPressOut={handlePressOut}
        style={[
          styles.filterChip,
          isActive && styles.filterChipActive,
          isActive && color && { backgroundColor: color + '30', borderColor: color },
        ]}
      >
        <Text
          style={[
            styles.filterChipText,
            isActive && styles.filterChipTextActive,
            isActive && color && { color },
          ]}
        >
          {label}
        </Text>
      </Pressable>
    </Animated.View>
  );
};

const CardGallery: React.FC = () => {
  const router = useRouter();

  // Card data state
  const [allCards, setAllCards] = useState<Card[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Filter state
  const [inputValue, setInputValue] = useState('');    // Immediate input state
  const [searchQuery, setSearchQuery] = useState('');  // Debounced state for API
  const [rarityFilter, setRarityFilter] = useState<Set<Rarity>>(new Set());
  const [domainFilter, setDomainFilter] = useState<Set<Domain>>(new Set());
  const [sortBy, setSortBy] = useState<SortOption>('card_id');
  const [showFilters, setShowFilters] = useState(false);

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [totalCards, setTotalCards] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [loadMoreError, setLoadMoreError] = useState<string | null>(null);

  const { width: screenWidth } = useWindowDimensions();

  const filterAnim = useRef(new Animated.Value(0)).current;
  const listRef = useRef<FlatList>(null);
  const searchDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isInitialMount = useRef(true);

  // Toggle handlers for multi-select filters
  const toggleRarityFilter = useCallback((rarity: Rarity | 'all') => {
    if (rarity === 'all') {
      setRarityFilter(new Set());
    } else {
      setRarityFilter(prev => {
        const newSet = new Set(prev);
        if (newSet.has(rarity)) {
          newSet.delete(rarity);
        } else {
          newSet.add(rarity);
        }
        return newSet;
      });
    }
  }, []);

  const toggleDomainFilter = useCallback((domain: Domain | 'all') => {
    if (domain === 'all') {
      setDomainFilter(new Set());
    } else {
      setDomainFilter(prev => {
        const newSet = new Set(prev);
        if (newSet.has(domain)) {
          newSet.delete(domain);
        } else {
          newSet.add(domain);
        }
        return newSet;
      });
    }
  }, []);

  // Cleanup debounce on unmount
  useEffect(() => {
    return () => {
      if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current);
    };
  }, []);

  // Filter panel animation
  useEffect(() => {
    Animated.spring(filterAnim, {
      toValue: showFilters ? 1 : 0,
      friction: 10,
      tension: 60,
      useNativeDriver: false,
    }).start();
  }, [showFilters]);

  // Build API URL with query parameters
  const buildApiUrl = useCallback((page: number) => {
    const params = new URLSearchParams();
    params.append('page', String(page));
    params.append('page_size', String(PAGE_SIZE));

    if (rarityFilter.size > 0) {
      params.append('rarity', Array.from(rarityFilter).join(','));
    }
    if (domainFilter.size > 0) {
      params.append('domain', Array.from(domainFilter).join(','));
    }
    if (searchQuery.trim()) params.append('search', searchQuery.trim());

    // Map frontend sort options to backend field names
    const sortFieldMap: Record<SortOption, string> = {
      card_id: 'card_id',
      name: 'card_name',
      rarity: 'card_rarity',
      number: 'card_number',
      set: 'set_id',
    };
    params.append('sort_by', sortFieldMap[sortBy]);
    if (sortBy === 'rarity') params.append('sort_desc', 'true');

    const url = `http://localhost:8000/cards?${params.toString()}`;
    console.log('Fetching URL:', url);
    return url;
  }, [rarityFilter, domainFilter, searchQuery, sortBy]);

  // Fetch cards from API (initial load or refresh)
  const fetchCards = useCallback(async (isRefresh = false) => {
    try {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setLoadMoreError(null);

      const url = buildApiUrl(1);
      const response = await fetch(url);
      if (!response.ok) throw new Error('Failed to fetch cards');

      const data = await response.json();

      setAllCards(data.cards);
      setTotalCards(data.total);
      setCurrentPage(1);
      setHasMore(data.cards.length >= PAGE_SIZE && data.cards.length < data.total);
    } catch (error) {
      console.error('Error fetching cards:', error);
      // Use mock data for development
      // setAllCards(MOCK_CARDS);
      // setTotalCards(MOCK_CARDS.length);
      setHasMore(false);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [buildApiUrl]);

  // Load more cards (pagination)
  const loadMoreCards = useCallback(async () => {
    if (isLoadingMore || !hasMore || loading) return;

    try {
      setIsLoadingMore(true);
      setLoadMoreError(null);

      const nextPage = currentPage + 1;
      const url = buildApiUrl(nextPage);
      const response = await fetch(url);
      if (!response.ok) throw new Error('Failed to load more cards');

      const data = await response.json();

      setAllCards(prev => [...prev, ...data.cards]);
      setCurrentPage(nextPage);
      setHasMore(data.cards.length >= PAGE_SIZE);
    } catch (error) {
      console.error('Error loading more cards:', error);
      setLoadMoreError('Failed to load more cards. Tap to retry.');
    } finally {
      setIsLoadingMore(false);
    }
  }, [currentPage, hasMore, isLoadingMore, loading, buildApiUrl]);

  // Initial fetch on mount
  useEffect(() => {
    fetchCards();
  }, []);

  // Convert Sets to strings for stable useEffect comparison
  const rarityKey = Array.from(rarityFilter).sort().join(',');
  const domainKey = Array.from(domainFilter).sort().join(',');

  // Refetch when filters change (not search - that's debounced separately)
  useEffect(() => {
    if (isInitialMount.current) {
      isInitialMount.current = false;
      return;
    }
    fetchCards();
  }, [rarityKey, domainKey, sortBy]);

  // Debounce inputValue -> searchQuery
  useEffect(() => {
    if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current);

    searchDebounceRef.current = setTimeout(() => {
      setSearchQuery(inputValue);
    }, 300);

    return () => {
      if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current);
    };
  }, [inputValue]);

  // Fetch when searchQuery changes (after debounce)
  useEffect(() => {
    if (isInitialMount.current) return;
    fetchCards();
  }, [searchQuery]);

  const handleCardPress = (card: Card) => {
    router.push(`/cards/${card.card_id}`);
  };

  const onRefresh = useCallback(() => {
    fetchCards(true);
  }, [fetchCards]);

  const rarityFilters: { key: Rarity | 'all'; label: string; color?: string }[] = [
    { key: 'all', label: 'All' },
    { key: 'Common', label: 'Common', color: Colors.rarityCommon },
    { key: 'Uncommon', label: 'Uncommon', color: Colors.rarityUncommon },
    { key: 'Rare', label: 'Rare', color: Colors.rarityRare },
    { key: 'Epic', label: 'Epic', color: Colors.rarityEpic },
    { key: 'Showcase', label: 'Showcase', color: Colors.rarityShowcase },
  ];

  const domainFilters: { key: Domain | 'all'; label: string; color?: string }[] = [
    { key: 'all', label: 'All' },
    { key: 'Fury', label: 'Fury', color: DomainColors.Fury.primary },
    { key: 'Calm', label: 'Calm', color: DomainColors.Calm.primary },
    { key: 'Chaos', label: 'Chaos', color: DomainColors.Chaos.primary },
    { key: 'Order', label: 'Order', color: DomainColors.Order.primary },
    { key: 'Body', label: 'Body', color: DomainColors.Body.primary },
    { key: 'Mind', label: 'Mind', color: DomainColors.Mind.primary },
  ];

  const sortOptions: { key: SortOption; label: string }[] = [
    { key: 'card_id', label: 'ID' },
    { key: 'name', label: 'Name' },
    { key: 'rarity', label: 'Rarity' },
    { key: 'number', label: '#' },
    { key: 'set', label: 'Set' },
  ];

  const filterHeight = filterAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [0, 220],
  });

  const numColumns = getNumColumns(screenWidth);

  const renderCard = useCallback(
    ({ item, index }: { item: Card; index: number }) => (
      <Animated.View
        style={{
          opacity: 1,
          transform: [{ translateY: 0 }],
        }}
      >
        <CardItem
          card={item}
          onPress={handleCardPress}
          size="small"
          showGlow={true}
        />
      </Animated.View>
    ),
    []
  );

  const headerElement = useMemo(() => (
    <View style={styles.header}>
      {/* Title Section */}
      <View style={styles.titleSection}>
        <Text style={styles.title}>Card Gallery</Text>
        <Text style={styles.subtitle}>
          {loading
            ? 'Loading...'
            : `${allCards.length}${totalCards > allCards.length ? ` of ${totalCards}` : ''} cards`
          }
        </Text>
      </View>

      {/* Search Bar */}
      <View style={styles.searchContainer}>
        <View style={styles.searchInputWrapper}>
          <View style={styles.searchIcon}>
            <Text style={styles.searchIconText}>⌕</Text>
          </View>
          <TextInput
            style={styles.searchInput}
            placeholder="Search cards..."
            placeholderTextColor={Colors.textMuted}
            value={inputValue}
            onChangeText={setInputValue}
            autoCapitalize="none"
            autoCorrect={false}
          />
          {inputValue.length > 0 && (
            <Pressable
              onPress={() => setInputValue('')}
              style={styles.clearButton}
            >
              <Text style={styles.clearButtonText}>✕</Text>
            </Pressable>
          )}
        </View>

        {/* Filter Toggle */}
        <Pressable
          onPress={() => setShowFilters(!showFilters)}
          style={[
            styles.filterToggle,
            showFilters && styles.filterToggleActive,
          ]}
        >
          <Text style={styles.filterToggleText}>☰</Text>
        </Pressable>
      </View>

      {/* Expandable Filters */}
      <Animated.View style={[styles.filtersContainer, { height: filterHeight }]}>
        <View style={styles.filterSection}>
          <Text style={styles.filterLabel}>Domain</Text>
          <View style={styles.filterChipsRow}>
            {domainFilters.map((filter) => (
              <FilterChip
                key={filter.key}
                label={filter.label}
                isActive={filter.key === 'all' ? domainFilter.size === 0 : domainFilter.has(filter.key)}
                onPress={() => toggleDomainFilter(filter.key)}
                color={filter.color}
              />
            ))}
          </View>
        </View>

        <View style={styles.filterSection}>
          <Text style={styles.filterLabel}>Rarity</Text>
          <View style={styles.filterChipsRow}>
            {rarityFilters.map((filter) => (
              <FilterChip
                key={filter.key}
                label={filter.label}
                isActive={filter.key === 'all' ? rarityFilter.size === 0 : rarityFilter.has(filter.key)}
                onPress={() => toggleRarityFilter(filter.key)}
                color={filter.color}
              />
            ))}
          </View>
        </View>

        <View style={styles.filterSection}>
          <Text style={styles.filterLabel}>Sort By</Text>
          <View style={styles.filterChipsRow}>
            {sortOptions.map((option) => (
              <FilterChip
                key={option.key}
                label={option.label}
                isActive={sortBy === option.key}
                onPress={() => setSortBy(option.key)}
              />
            ))}
          </View>
        </View>
      </Animated.View>
    </View>
  ), [loading, allCards.length, totalCards, inputValue, showFilters, filterHeight, domainFilter, rarityFilter, sortBy, toggleDomainFilter, toggleRarityFilter]);

  const renderEmpty = () => (
    <View style={styles.emptyContainer}>
      <View style={styles.emptyIcon}>
        <Text style={styles.emptyIconText}>∅</Text>
      </View>
      <Text style={styles.emptyTitle}>No Cards Found</Text>
      <Text style={styles.emptySubtitle}>
        {searchQuery
          ? 'Try adjusting your search or filters'
          : 'Cards will appear here once loaded'}
      </Text>
    </View>
  );

  const renderFooter = useCallback(() => {
    if (!hasMore && allCards.length > 0) {
      return (
        <View style={styles.footerContainer}>
          <Text style={styles.footerText}>
            Showing all {allCards.length} cards
          </Text>
        </View>
      );
    }

    if (loadMoreError) {
      return (
        <Pressable onPress={loadMoreCards} style={styles.footerContainer}>
          <Text style={styles.footerErrorText}>{loadMoreError}</Text>
          <Text style={styles.footerRetryText}>Tap to retry</Text>
        </Pressable>
      );
    }

    if (isLoadingMore) {
      return (
        <View style={styles.footerContainer}>
          <ActivityIndicator size="small" color={Colors.accent} />
          <Text style={styles.footerText}>Loading more cards...</Text>
        </View>
      );
    }

    return null;
  }, [hasMore, allCards.length, loadMoreError, isLoadingMore, loadMoreCards]);

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor={Colors.background} />

      {/* Static header - won't re-render when cards change */}
      {headerElement}

      {/* Cards grid - only this section reloads */}
      {loading ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={Colors.accent} />
          <Text style={styles.loadingText}>Loading cards...</Text>
        </View>
      ) : (
        <FlatList
          ref={listRef}
          data={allCards}
          renderItem={renderCard}
          keyExtractor={(item) => item.card_id}
          numColumns={numColumns}
          key={numColumns}
          ListEmptyComponent={renderEmpty}
          ListFooterComponent={renderFooter}
          contentContainerStyle={[
            styles.listContent,
            allCards.length === 0 && styles.listContentEmpty,
          ]}
          columnWrapperStyle={numColumns > 1 ? styles.row : undefined}
          showsVerticalScrollIndicator={false}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={onRefresh}
              tintColor={Colors.accent}
              colors={[Colors.accent]}
              progressBackgroundColor={Colors.surface}
            />
          }
          onEndReached={loadMoreCards}
          onEndReachedThreshold={0.5}
          initialNumToRender={12}
          maxToRenderPerBatch={12}
          windowSize={5}
          removeClippedSubviews={Platform.OS !== 'web'}
        />
      )}
    </SafeAreaView>
  );
};

// Responsive column calculation
const getNumColumns = (screenWidth: number) => {
  if (screenWidth >= 1024) return 5;
  if (screenWidth >= 768) return 4;
  if (screenWidth >= 480) return 3;
  return 3;
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: Spacing.lg,
  },
  loadingText: {
    color: Colors.textSecondary,
    fontSize: Typography.size.md,
  },
  header: {
    paddingHorizontal: Spacing.lg,
    paddingTop: Spacing.lg,
    paddingBottom: Spacing.md,
  },
  titleSection: {
    marginBottom: Spacing.lg,
  },
  title: {
    fontSize: Typography.size.xxxl,
    fontWeight: '700',
    color: Colors.textPrimary,
    letterSpacing: -0.5,
  },
  subtitle: {
    fontSize: Typography.size.md,
    color: Colors.textMuted,
    marginTop: Spacing.xs,
  },
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
  },
  searchInputWrapper: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.lg,
    borderWidth: 1,
    borderColor: Colors.border,
    paddingHorizontal: Spacing.md,
    height: 48,
  },
  searchIcon: {
    marginRight: Spacing.sm,
  },
  searchIconText: {
    fontSize: 20,
    color: Colors.textMuted,
  },
  searchInput: {
    flex: 1,
    color: Colors.textPrimary,
    fontSize: Typography.size.md,
    ...Platform.select({
      web: {
        outlineStyle: 'none' as any,
      },
    }),
  },
  clearButton: {
    padding: Spacing.xs,
    marginLeft: Spacing.xs,
  },
  clearButtonText: {
    color: Colors.textMuted,
    fontSize: 14,
  },
  filterToggle: {
    width: 48,
    height: 48,
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.lg,
    borderWidth: 1,
    borderColor: Colors.border,
    justifyContent: 'center',
    alignItems: 'center',
  },
  filterToggleActive: {
    backgroundColor: Colors.accentSubtle,
    borderColor: Colors.accent,
  },
  filterToggleText: {
    fontSize: 20,
    color: Colors.textSecondary,
  },
  filtersContainer: {
    overflow: 'hidden',
    marginTop: Spacing.md,
  },
  filterSection: {
    marginBottom: Spacing.md,
  },
  filterLabel: {
    fontSize: Typography.size.sm,
    color: Colors.textMuted,
    marginBottom: Spacing.sm,
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  filterChipsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.xs,
  },
  filterChip: {
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.xl,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  filterChipActive: {
    backgroundColor: Colors.accentSubtle,
    borderColor: Colors.accent,
  },
  filterChipText: {
    color: Colors.textSecondary,
    fontSize: Typography.size.sm,
    fontWeight: '500',
  },
  filterChipTextActive: {
    color: Colors.accent,
  },
  listContent: {
    paddingHorizontal: Spacing.lg - Spacing.sm,
    paddingBottom: Spacing.xxxl,
  },
  listContentEmpty: {
    flexGrow: 1,
  },
  row: {
    justifyContent: 'flex-start',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: Spacing.xxxl * 2,
  },
  emptyIcon: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: Colors.surface,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: Spacing.lg,
  },
  emptyIconText: {
    fontSize: 36,
    color: Colors.textMuted,
  },
  emptyTitle: {
    fontSize: Typography.size.xl,
    fontWeight: '600',
    color: Colors.textPrimary,
    marginBottom: Spacing.sm,
  },
  emptySubtitle: {
    fontSize: Typography.size.md,
    color: Colors.textMuted,
    textAlign: 'center',
    paddingHorizontal: Spacing.xxl,
  },
  // Footer styles for pagination
  footerContainer: {
    paddingVertical: Spacing.xl,
    paddingHorizontal: Spacing.lg,
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.sm,
  },
  footerText: {
    color: Colors.textMuted,
    fontSize: Typography.size.sm,
  },
  footerErrorText: {
    color: Colors.error,
    fontSize: Typography.size.sm,
    textAlign: 'center',
  },
  footerRetryText: {
    color: Colors.accent,
    fontSize: Typography.size.sm,
    fontWeight: '500',
  },
});

export default CardGallery;