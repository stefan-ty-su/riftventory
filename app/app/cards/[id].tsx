import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Image,
  Pressable,
  ActivityIndicator,
  SafeAreaView,
  StatusBar,
  useWindowDimensions,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import {
  Colors,
  Spacing,
  BorderRadius,
  Typography,
  Shadows,
} from '../../constants/theme';
import { DomainBadge } from '../../components/DomainBadge';

interface CardDetail {
  card_id: string;
  set_id: string;
  card_number: number;
  public_code: string;
  card_name: string;
  attr_energy: number | null;
  attr_power: number | null;
  attr_might: number | null;
  card_type: string | null;
  card_supertype: string | null;
  card_rarity: string | null;
  card_domain: string[];
  card_image_url: string | null;
  card_artist: string | null;
  card_tags: string[];
  alternate_art: boolean;
  overnumbered: boolean;
  signature: boolean;
  text_rich: string | null;
  text_plain: string | null;
}

const getRarityColor = (rarity: string | null): string => {
  switch (rarity) {
    case 'Common':
      return Colors.rarityCommon;
    case 'Uncommon':
      return Colors.rarityUncommon;
    case 'Rare':
      return Colors.rarityRare;
    case 'Epic':
      return Colors.rarityEpic;
    case 'Showcase':
      return Colors.rarityShowcase;
    default:
      return Colors.textMuted;
  }
};

export default function CardDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { width: screenWidth } = useWindowDimensions();

  const [card, setCard] = useState<CardDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Use 2-column layout on wider screens (tablet/desktop)
  const useTwoColumnLayout = screenWidth >= 768;

  useEffect(() => {
    const fetchCard = async () => {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch(`http://localhost:8000/cards/${id}`);

        if (!response.ok) {
          if (response.status === 404) {
            throw new Error('Card not found');
          }
          throw new Error('Failed to fetch card');
        }

        const data = await response.json();
        setCard(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred');
      } finally {
        setLoading(false);
      }
    };

    if (id) {
      fetchCard();
    }
  }, [id]);

  const handleBack = () => {
    router.back();
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <StatusBar barStyle="light-content" backgroundColor={Colors.background} />
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={Colors.accent} />
          <Text style={styles.loadingText}>Loading card...</Text>
        </View>
      </SafeAreaView>
    );
  }

  if (error || !card) {
    return (
      <SafeAreaView style={styles.container}>
        <StatusBar barStyle="light-content" backgroundColor={Colors.background} />
        <View style={styles.header}>
          <Pressable onPress={handleBack} style={styles.backButton}>
            <Text style={styles.backButtonText}>← Back</Text>
          </Pressable>
        </View>
        <View style={styles.errorContainer}>
          <Text style={styles.errorIcon}>!</Text>
          <Text style={styles.errorTitle}>Error</Text>
          <Text style={styles.errorText}>{error || 'Card not found'}</Text>
          <Pressable onPress={handleBack} style={styles.errorButton}>
            <Text style={styles.errorButtonText}>Go Back</Text>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor={Colors.background} />

      {/* Header with back button */}
      <View style={styles.header}>
        <Pressable onPress={handleBack} style={styles.backButton}>
          <Text style={styles.backButtonText}>← Back</Text>
        </Pressable>
      </View>

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={[
          styles.scrollContent,
          useTwoColumnLayout && styles.scrollContentTwoColumn,
        ]}
        showsVerticalScrollIndicator={false}
      >
        {/* Two Column Layout Container */}
        <View style={[
          styles.mainContent,
          useTwoColumnLayout && styles.mainContentTwoColumn,
        ]}>
          {/* Left Column - Card Image */}
          <View style={[
            styles.imageColumn,
            useTwoColumnLayout && styles.imageColumnTwoColumn,
          ]}>
            <View style={styles.imageContainer}>
              {card.card_image_url ? (
                <Image
                  source={{ uri: card.card_image_url }}
                  style={[
                    styles.cardImage,
                    useTwoColumnLayout && styles.cardImageTwoColumn,
                  ]}
                  resizeMode="contain"
                />
              ) : (
                <View style={[
                  styles.imagePlaceholder,
                  useTwoColumnLayout && styles.imagePlaceholderTwoColumn,
                ]}>
                  <Text style={styles.imagePlaceholderText}>No Image</Text>
                </View>
              )}
            </View>

            {/* Artist - shown below image in 2-column layout */}
            {useTwoColumnLayout && card.card_artist && (
              <View style={styles.artistContainerTwoColumn}>
                <Text style={styles.artistLabel}>Illustrated by</Text>
                <Text style={styles.artistName}>{card.card_artist}</Text>
              </View>
            )}
          </View>

          {/* Right Column - Card Info */}
          <View style={[
            styles.infoColumn,
            useTwoColumnLayout && styles.infoColumnTwoColumn,
          ]}>
            {/* Card Name */}
            <Text style={[
              styles.cardName,
              useTwoColumnLayout && styles.cardNameTwoColumn,
            ]}>
              {card.card_name}
            </Text>

            {/* Set and Number */}
            <Text style={[
              styles.setInfo,
              useTwoColumnLayout && styles.setInfoTwoColumn,
            ]}>
              {card.set_id} · #{card.card_number} · {card.public_code}
            </Text>

            {/* Domains */}
            {card.card_domain && card.card_domain.length > 0 && (
              <View style={[
                styles.domainContainer,
                useTwoColumnLayout && styles.domainContainerTwoColumn,
              ]}>
                <DomainBadge domain={card.card_domain} size="large" />
              </View>
            )}

            {/* Type and Rarity Row */}
            <View style={[
              styles.typeRarityRow,
              useTwoColumnLayout && styles.typeRarityRowTwoColumn,
            ]}>
              {card.card_supertype && (
                <View style={styles.typeBadge}>
                  <Text style={styles.typeBadgeText}>{card.card_supertype}</Text>
                </View>
              )}
              {card.card_type && (
                <View style={styles.typeBadge}>
                  <Text style={styles.typeBadgeText}>{card.card_type}</Text>
                </View>
              )}
              {card.card_rarity && (
                <View style={[styles.rarityBadge, { backgroundColor: `${getRarityColor(card.card_rarity)}20` }]}>
                  <Text style={[styles.rarityBadgeText, { color: getRarityColor(card.card_rarity) }]}>
                    {card.card_rarity}
                  </Text>
                </View>
              )}
            </View>

            {/* Stats Section */}
            {(card.attr_energy !== null || card.attr_power !== null || card.attr_might !== null) && (
              <View style={styles.statsContainer}>
                <Text style={styles.sectionTitle}>Stats</Text>
                <View style={styles.statsRow}>
                  {card.attr_energy !== null && (
                    <View style={styles.statItem}>
                      <Text style={styles.statLabel}>Energy</Text>
                      <Text style={styles.statValue}>{card.attr_energy}</Text>
                    </View>
                  )}
                  {card.attr_power !== null && (
                    <View style={styles.statItem}>
                      <Text style={styles.statLabel}>Power</Text>
                      <Text style={styles.statValue}>{card.attr_power}</Text>
                    </View>
                  )}
                  {card.attr_might !== null && (
                    <View style={styles.statItem}>
                      <Text style={styles.statLabel}>Might</Text>
                      <Text style={styles.statValue}>{card.attr_might}</Text>
                    </View>
                  )}
                </View>
              </View>
            )}

            {/* Card Text */}
            {card.text_plain && (
              <View style={styles.textContainer}>
                <Text style={styles.sectionTitle}>Card Text</Text>
                <Text style={styles.cardText}>{card.text_plain}</Text>
              </View>
            )}

            {/* Tags */}
            {card.card_tags && card.card_tags.length > 0 && (
              <View style={styles.tagsContainer}>
                <Text style={styles.sectionTitle}>Tags</Text>
                <View style={styles.tagsRow}>
                  {card.card_tags.map((tag, index) => (
                    <View key={index} style={styles.tagBadge}>
                      <Text style={styles.tagText}>{tag}</Text>
                    </View>
                  ))}
                </View>
              </View>
            )}

            {/* Special Indicators */}
            {(card.alternate_art || card.overnumbered || card.signature) && (
              <View style={styles.specialContainer}>
                <Text style={styles.sectionTitle}>Special</Text>
                <View style={styles.specialRow}>
                  {card.alternate_art && (
                    <View style={styles.specialBadge}>
                      <Text style={styles.specialText}>Alternate Art</Text>
                    </View>
                  )}
                  {card.overnumbered && (
                    <View style={styles.specialBadge}>
                      <Text style={styles.specialText}>Overnumbered</Text>
                    </View>
                  )}
                  {card.signature && (
                    <View style={styles.specialBadge}>
                      <Text style={styles.specialText}>Signature</Text>
                    </View>
                  )}
                </View>
              </View>
            )}

            {/* Artist - shown at bottom in single column layout */}
            {!useTwoColumnLayout && card.card_artist && (
              <View style={styles.artistContainer}>
                <Text style={styles.artistLabel}>Illustrated by</Text>
                <Text style={styles.artistName}>{card.card_artist}</Text>
              </View>
            )}
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

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
    paddingVertical: Spacing.md,
  },
  backButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: Spacing.sm,
    paddingHorizontal: Spacing.md,
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.md,
    alignSelf: 'flex-start',
  },
  backButtonText: {
    color: Colors.textPrimary,
    fontSize: Typography.size.md,
    fontWeight: '500',
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    paddingBottom: Spacing.xxxl,
  },
  scrollContentTwoColumn: {
    paddingHorizontal: Spacing.xl,
  },
  // Main content container
  mainContent: {},
  mainContentTwoColumn: {
    flexDirection: 'row',
    gap: Spacing.xxl,
  },
  // Left column (image)
  imageColumn: {},
  imageColumnTwoColumn: {
    flex: 2,
    alignItems: 'center',
  },
  imageContainer: {
    alignItems: 'center',
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.lg,
    width: '100%',
  },
  cardImage: {
    width: '100%',
    maxWidth: 400,
    aspectRatio: 280 / 400,
    borderRadius: BorderRadius.lg,
    ...Shadows.card,
  },
  cardImageTwoColumn: {
    maxWidth: 500,
  },
  imagePlaceholder: {
    width: '100%',
    maxWidth: 400,
    aspectRatio: 280 / 400,
    borderRadius: BorderRadius.lg,
    backgroundColor: Colors.surface,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: Colors.border,
  },
  imagePlaceholderTwoColumn: {
    maxWidth: 500,
  },
  imagePlaceholderText: {
    color: Colors.textMuted,
    fontSize: Typography.size.lg,
  },
  artistContainerTwoColumn: {
    alignItems: 'center',
    marginTop: Spacing.lg,
  },
  // Right column (info)
  infoColumn: {
    paddingHorizontal: Spacing.lg,
  },
  infoColumnTwoColumn: {
    flex: 3,
    paddingHorizontal: 0,
    paddingTop: Spacing.lg,
  },
  cardName: {
    fontSize: Typography.size.xxl,
    fontWeight: '700',
    color: Colors.textPrimary,
    textAlign: 'center',
    marginBottom: Spacing.xs,
  },
  cardNameTwoColumn: {
    textAlign: 'left',
    fontSize: Typography.size.xxxl,
  },
  setInfo: {
    fontSize: Typography.size.md,
    color: Colors.textMuted,
    textAlign: 'center',
    marginBottom: Spacing.lg,
  },
  setInfoTwoColumn: {
    textAlign: 'left',
  },
  domainContainer: {
    alignItems: 'center',
    marginBottom: Spacing.lg,
  },
  domainContainerTwoColumn: {
    alignItems: 'flex-start',
  },
  typeRarityRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: Spacing.sm,
    marginBottom: Spacing.xl,
  },
  typeRarityRowTwoColumn: {
    justifyContent: 'flex-start',
  },
  typeBadge: {
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.md,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  typeBadgeText: {
    color: Colors.textSecondary,
    fontSize: Typography.size.sm,
    fontWeight: '500',
  },
  rarityBadge: {
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    borderRadius: BorderRadius.md,
  },
  rarityBadgeText: {
    fontSize: Typography.size.sm,
    fontWeight: '600',
  },
  sectionTitle: {
    fontSize: Typography.size.sm,
    color: Colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginBottom: Spacing.sm,
  },
  statsContainer: {
    marginBottom: Spacing.xl,
  },
  statsRow: {
    flexDirection: 'row',
    gap: Spacing.lg,
  },
  statItem: {
    flex: 1,
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.md,
    padding: Spacing.md,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: Colors.border,
  },
  statLabel: {
    fontSize: Typography.size.sm,
    color: Colors.textMuted,
    marginBottom: Spacing.xs,
  },
  statValue: {
    fontSize: Typography.size.xl,
    fontWeight: '700',
    color: Colors.accent,
  },
  textContainer: {
    marginBottom: Spacing.xl,
  },
  cardText: {
    fontSize: Typography.size.md,
    color: Colors.textPrimary,
    lineHeight: Typography.size.md * Typography.lineHeight.relaxed,
    backgroundColor: Colors.surface,
    padding: Spacing.md,
    borderRadius: BorderRadius.md,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  tagsContainer: {
    marginBottom: Spacing.xl,
  },
  tagsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.sm,
  },
  tagBadge: {
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.xs,
    backgroundColor: Colors.accentSubtle,
    borderRadius: BorderRadius.xl,
  },
  tagText: {
    color: Colors.accent,
    fontSize: Typography.size.sm,
    fontWeight: '500',
  },
  specialContainer: {
    marginBottom: Spacing.xl,
  },
  specialRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.sm,
  },
  specialBadge: {
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.xs,
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.xl,
    borderWidth: 1,
    borderColor: Colors.accent,
  },
  specialText: {
    color: Colors.accent,
    fontSize: Typography.size.sm,
    fontWeight: '500',
  },
  artistContainer: {
    alignItems: 'center',
    paddingTop: Spacing.lg,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
  },
  artistLabel: {
    fontSize: Typography.size.sm,
    color: Colors.textMuted,
    marginBottom: Spacing.xs,
  },
  artistName: {
    fontSize: Typography.size.md,
    color: Colors.textSecondary,
    fontWeight: '500',
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: Spacing.xl,
  },
  errorIcon: {
    fontSize: 48,
    color: Colors.error,
    marginBottom: Spacing.lg,
  },
  errorTitle: {
    fontSize: Typography.size.xl,
    fontWeight: '600',
    color: Colors.textPrimary,
    marginBottom: Spacing.sm,
  },
  errorText: {
    fontSize: Typography.size.md,
    color: Colors.textSecondary,
    textAlign: 'center',
    marginBottom: Spacing.xl,
  },
  errorButton: {
    paddingHorizontal: Spacing.xl,
    paddingVertical: Spacing.md,
    backgroundColor: Colors.accent,
    borderRadius: BorderRadius.md,
  },
  errorButtonText: {
    color: Colors.background,
    fontSize: Typography.size.md,
    fontWeight: '600',
  },
});