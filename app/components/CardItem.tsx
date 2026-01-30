import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Image,
  Text,
  StyleSheet,
  Pressable,
  Animated,
  useWindowDimensions,
  Platform,
} from 'react-native';
import { Colors, BorderRadius, Shadows, Spacing, Typography, getDomainColor, getDomainColors, isDualDomain } from '../constants/theme';
import { LinearGradient } from 'expo-linear-gradient';
import { DomainBadge } from './DomainBadge';

// Card data interface matching the database schema
export interface Card {
  card_id: string;
  card_name: string;
  card_image_url: string | null;
  card_type?: string | null;
  card_supertype?: string | null;
  card_rarity?: string | null;
  card_domain?: string[] | null;
  set_id: string;
  card_number: number;
  attr_energy?: number | null;
  attr_power?: number | null;
  attr_might?: number | null;
}

interface CardItemProps {
  card: Card;
  onPress?: (card: Card) => void;
  size?: 'small' | 'medium' | 'large';
  showGlow?: boolean;
  showInfo?: boolean; // Show card name and domain below image
}

// Rarity to color mapping
const getRarityColor = (rarity?: string | null): string => {
  const rarityMap: Record<string, string> = {
    common: Colors.rarityCommon,
    uncommon: Colors.rarityUncommon,
    rare: Colors.rarityRare,
    epic: Colors.rarityEpic,
    showcase: Colors.rarityShowcase
  };
  return rarityMap[rarity?.toLowerCase() ?? ''] ?? Colors.rarityCommon;
};

// Get number of columns based on screen width (must match cards.tsx)
const getNumColumns = (screenWidth: number) => {
  if (screenWidth >= 1024) return 5;
  if (screenWidth >= 768) return 4;
  if (screenWidth >= 480) return 3;
  return 3;
};

// Size configurations for different card sizes
const getSizeConfig = (size: 'small' | 'medium' | 'large', screenWidth: number) => {
  const numColumns = getNumColumns(screenWidth);
  // Account for container padding (Spacing.lg - Spacing.xs on each side) and card margins (Spacing.md * 2 per card)
  const containerPadding = (Spacing.lg - Spacing.xs) * 2;
  const totalMargins = Spacing.md * 2 * numColumns;
  const availableWidth = screenWidth - containerPadding - totalMargins;

  const configs = {
    small: {
      width: availableWidth / numColumns,
      aspectRatio: 0.715, // Standard TCG card ratio
    },
    medium: {
      width: (screenWidth - Spacing.lg * 2 - Spacing.md) / 2,
      aspectRatio: 0.715,
    },
    large: {
      width: screenWidth - Spacing.lg * 2,
      aspectRatio: 0.715,
    },
  };
  return configs[size];
};

const CardItem: React.FC<CardItemProps> = ({
  card,
  onPress,
  size = 'small',
  showGlow = true,
  showInfo = true,
}) => {
  const [isPressed, setIsPressed] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const [imageLoaded, setImageLoaded] = useState(false);

  const { width: screenWidth } = useWindowDimensions();

  const scaleAnim = useRef(new Animated.Value(1)).current;
  const glowAnim = useRef(new Animated.Value(0)).current;
  const shimmerAnim = useRef(new Animated.Value(0)).current;

  const sizeConfig = getSizeConfig(size, screenWidth);
  const rarityColor = getRarityColor(card.card_rarity);
  const domainColors = getDomainColor(card.card_domain);
  const allDomainColors = getDomainColors(card.card_domain);
  const hasDualDomain = isDualDomain(card.card_domain);

  // Shimmer animation loop
  useEffect(() => {
    if (showGlow && imageLoaded) {
      const shimmerLoop = Animated.loop(
        Animated.sequence([
          Animated.timing(shimmerAnim, {
            toValue: 1,
            duration: 2000,
            useNativeDriver: true,
          }),
          Animated.timing(shimmerAnim, {
            toValue: 0,
            duration: 2000,
            useNativeDriver: true,
          }),
        ])
      );
      shimmerLoop.start();
      return () => shimmerLoop.stop();
    }
  }, [showGlow, imageLoaded, shimmerAnim]);

  const handlePressIn = () => {
    setIsPressed(true);
    Animated.parallel([
      Animated.spring(scaleAnim, {
        toValue: 0.96,
        friction: 8,
        tension: 100,
        useNativeDriver: true,
      }),
      Animated.timing(glowAnim, {
        toValue: 1,
        duration: 150,
        useNativeDriver: true,
      }),
    ]).start();
  };

  const handlePressOut = () => {
    setIsPressed(false);
    Animated.parallel([
      Animated.spring(scaleAnim, {
        toValue: isHovered ? 1.02 : 1,
        friction: 6,
        tension: 80,
        useNativeDriver: true,
      }),
      Animated.timing(glowAnim, {
        toValue: isHovered ? 0.5 : 0,
        duration: 200,
        useNativeDriver: true,
      }),
    ]).start();
  };

  const handleHoverIn = () => {
    if (Platform.OS === 'web') {
      setIsHovered(true);
      Animated.parallel([
        Animated.spring(scaleAnim, {
          toValue: 1.03,
          friction: 8,
          tension: 100,
          useNativeDriver: true,
        }),
        Animated.timing(glowAnim, {
          toValue: 0.6,
          duration: 200,
          useNativeDriver: true,
        }),
      ]).start();
    }
  };

  const handleHoverOut = () => {
    if (Platform.OS === 'web') {
      setIsHovered(false);
      if (!isPressed) {
        Animated.parallel([
          Animated.spring(scaleAnim, {
            toValue: 1,
            friction: 8,
            tension: 100,
            useNativeDriver: true,
          }),
          Animated.timing(glowAnim, {
            toValue: 0,
            duration: 300,
            useNativeDriver: true,
          }),
        ]).start();
      }
    }
  };

  const cardWidth = sizeConfig.width;
  const cardHeight = cardWidth / sizeConfig.aspectRatio;

  const glowOpacity = glowAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [0.3, 0.8],
  });

  const glowStyle = {
    shadowColor: rarityColor,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: glowOpacity,
    shadowRadius: 20,
  };

  const shimmerOpacity = shimmerAnim.interpolate({
    inputRange: [0, 0.5, 1],
    outputRange: [0, 0.15, 0],
  });

  return (
    <Animated.View
      style={[
        styles.cardWrapper,
        {
          width: cardWidth,
          transform: [{ scale: scaleAnim }],
        },
        showGlow && glowStyle,
      ]}
    >
      <Pressable
        onPress={() => onPress?.(card)}
        onPressIn={handlePressIn}
        onPressOut={handlePressOut}
        {...(Platform.OS === 'web' && {
          onHoverIn: handleHoverIn,
          onHoverOut: handleHoverOut,
        })}
        style={styles.pressable}
      >
        <View style={styles.gradientBorderWrapper}>
          {/* Gradient border layer for dual-domain cards on hover */}
          {hasDualDomain && (isHovered || isPressed) && (
            <LinearGradient
              colors={[allDomainColors[0].primary, allDomainColors[1].primary]}
              start={{ x: 0, y: 0.5 }}
              end={{ x: 1, y: 0.5 }}
              style={styles.gradientBorder}
            />
          )}
          <View
            style={[
              styles.cardContainer,
              hasDualDomain && (isHovered || isPressed)
                ? styles.cardContainerGradientBorder
                : { borderColor: isHovered || isPressed ? domainColors.primary : Colors.border },
            ]}
          >
          {/* Card Image */}
          <View style={[styles.imageWrapper, { height: cardHeight }]}>
            {card.card_image_url ? (
              <Image
                source={{ uri: card.card_image_url }}
                style={styles.cardImage}
                resizeMode="cover"
                onLoad={() => setImageLoaded(true)}
              />
            ) : (
              <View style={styles.placeholderContainer}>
                <View style={styles.placeholderInner}>
                  <View style={styles.placeholderIcon}>
                    <View style={styles.placeholderIconOuter}>
                      <View style={styles.placeholderIconInner} />
                    </View>
                  </View>
                </View>
              </View>
            )}

            {/* Shimmer overlay for legendary/mythic cards */}
            {showGlow &&
              imageLoaded &&
              (card.card_rarity?.toLowerCase() === 'legendary' ||
                card.card_rarity?.toLowerCase() === 'mythic') && (
                <Animated.View
                  style={[
                    styles.shimmerOverlay,
                    { opacity: shimmerOpacity },
                  ]}
                  pointerEvents="none"
                />
              )}

            {/* Rarity indicator bar */}
            <View style={[styles.rarityBar, { backgroundColor: rarityColor }]} />
          </View>

          {/* Card Info Section */}
          {showInfo && (
            <View style={styles.infoSection}>
              <Text style={styles.cardName} numberOfLines={2}>
                {card.card_name}
              </Text>
              
              {card.card_type && (
                <Text style={styles.cardType} numberOfLines={1}>
                  {card.card_type}
                  {card.card_supertype && ` · ${card.card_supertype}`}
                </Text>
              )}
              
              {card.card_domain && card.card_domain.length > 0 && (
                <View style={styles.domainContainer}>
                  <DomainBadge domain={card.card_domain} size="small"/>
                </View>
              )}
            </View>
          )}
        </View>
        </View>
      </Pressable>
    </Animated.View>
  );
};

const styles = StyleSheet.create({
  cardWrapper: {
    margin: Spacing.md,
  },
  pressable: {
    flex: 1,
  },
  gradientBorderWrapper: {
    flex: 1,
    borderRadius: BorderRadius.card,
    overflow: 'hidden',
  },
  gradientBorder: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    borderRadius: BorderRadius.card,
  },
  cardContainer: {
    flex: 1,
    backgroundColor: Colors.backgroundCard,
    borderRadius: BorderRadius.card,
    borderWidth: 3,
    borderColor: Colors.border,
    overflow: 'hidden',
    ...Shadows.card,
  },
  cardContainerGradientBorder: {
    margin: 3,
    borderWidth: 0,
  },
  imageWrapper: {
    position: 'relative',
    overflow: 'hidden',
  },
  cardImage: {
    width: '100%',
    height: '100%',
  },
  placeholderContainer: {
    flex: 1,
    backgroundColor: Colors.surface,
    justifyContent: 'center',
    alignItems: 'center',
  },
  placeholderInner: {
    width: '60%',
    aspectRatio: 1,
    justifyContent: 'center',
    alignItems: 'center',
    opacity: 0.3,
  },
  placeholderIcon: {
    width: '50%',
    aspectRatio: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  placeholderIconOuter: {
    width: '100%',
    height: '100%',
    borderRadius: 8,
    borderWidth: 2,
    borderColor: Colors.textMuted,
    justifyContent: 'center',
    alignItems: 'center',
  },
  placeholderIconInner: {
    width: '40%',
    height: '40%',
    borderRadius: 4,
    backgroundColor: Colors.textMuted,
  },
  shimmerOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: '#FFFFFF',
  },
  rarityBar: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    height: 3,
  },
  infoSection: {
    padding: Spacing.sm,
    backgroundColor: Colors.backgroundCard,
    gap: Spacing.xs,
  },
  cardName: {
    color: Colors.textPrimary,
    fontSize: Typography.size.sm,
    fontWeight: '600',
    lineHeight: Typography.size.sm * Typography.lineHeight.tight,
  },
  cardType: {
    color: Colors.textMuted,
    fontSize: Typography.size.xs,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  domainContainer: {
    marginTop: Spacing.xs,
  },
});

export default CardItem;
