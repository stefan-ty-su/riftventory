import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { DomainColors, getDomainColor, Spacing, BorderRadius, Typography } from '../constants/theme';

interface DomainBadgeProps {
  domain: string | string[] | undefined | null;
  size?: 'small' | 'medium' | 'large';
  showLabel?: boolean;
}

/**
 * DomainBadge Component
 * Displays a colored badge for card domains (Fury, Calm, Chaos, Order, Body, Mind)
 */
export const DomainBadge: React.FC<DomainBadgeProps> = ({
  domain,
  size = 'medium',
  showLabel = true,
}) => {
  const domains = Array.isArray(domain) ? domain : domain ? [domain] : [];

  const sizeStyles = {
    small: { badge: styles.badgeSmall, text: styles.textSmall, dot: styles.dotSmall },
    medium: { badge: styles.badgeMedium, text: styles.textMedium, dot: styles.dotMedium },
    large: { badge: styles.badgeLarge, text: styles.textLarge, dot: styles.dotLarge },
  };

  const currentSize = sizeStyles[size];

  if (domains.length === 0) {
    return null;
  }

  // Inline mode for dual-domain cards: render two badges side-by-side
  return (
    <View style={styles.inlineContainer}>
      {domains.map((d, index) => {
        const colors = getDomainColor(d);
        return (
          <View
            key={`${d}-${index}`}
            style={[
              styles.badge,
              styles.inlineBadge,
              currentSize.badge,
              {
                backgroundColor: `${colors.primary}15`,
                borderColor: `${colors.primary}40`,
              },
            ]}
          >
            <View
              style={[
                styles.dot,
                currentSize.dot,
                {
                  backgroundColor: colors.primary,
                  shadowColor: colors.primary,
                },
              ]}
            />
            {showLabel && (
              <Text style={[styles.text, currentSize.text, { color: colors.text }]}>
                {d}
              </Text>
            )}
          </View>
        );
      })}
    </View>
  );
};

/**
 * MultiDomainBadge Component
 * Displays multiple domain badges for cards with multiple domains
 */
export const MultiDomainBadge: React.FC<{
  domains: string[] | undefined | null;
  size?: 'small' | 'medium' | 'large';
}> = ({ domains, size = 'small' }) => {
  if (!domains || domains.length === 0) return null;

  return (
    <View style={styles.multiContainer}>
      {domains.map((domain, index) => (
        <DomainBadge
          key={`${domain}-${index}`}
          domain={domain}
          size={size}
          showLabel={domains.length === 1}
        />
      ))}
    </View>
  );
};

const styles = StyleSheet.create({
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: BorderRadius.xl,
    borderWidth: 1,
  },
  badgeSmall: {
    paddingHorizontal: Spacing.sm,
    paddingVertical: Spacing.xs,
    gap: Spacing.xs,
  },
  badgeMedium: {
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm - 2,
    gap: Spacing.sm - 2,
  },
  badgeLarge: {
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.sm,
    gap: Spacing.sm,
  },
  dot: {
    borderRadius: 50,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.8,
    shadowRadius: 4,
    elevation: 4,
  },
  dotSmall: {
    width: 6,
    height: 6,
  },
  dotMedium: {
    width: 8,
    height: 8,
  },
  dotLarge: {
    width: 10,
    height: 10,
  },
  text: {
    fontWeight: '600',
    letterSpacing: 0.5,
  },
  textSmall: {
    fontSize: Typography.size.xs,
  },
  textMedium: {
    fontSize: Typography.size.sm,
  },
  textLarge: {
    fontSize: Typography.size.md,
  },
  multiContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.sm - 2,
  },
  inlineContainer: {
    flexDirection: 'row',
    gap: Spacing.xs,
  },
  inlineBadge: {
    flex: 1,
    justifyContent: 'center',
  },
});

export default DomainBadge;
