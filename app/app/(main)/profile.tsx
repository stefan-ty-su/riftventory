import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Colors, Typography, Spacing } from '@/constants/theme';
import { IconSymbol } from '@/components/ui/icon-symbol';
import { useAuth } from '@/context/AuthContext';

export default function ProfileScreen() {
  const { session } = useAuth();

  return (
    <View style={styles.container}>
      <View style={styles.iconContainer}>
        <IconSymbol name="person.circle.fill" size={64} color={Colors.accent} />
      </View>
      <Text style={styles.title}>Profile</Text>
      <Text style={styles.email}>{session?.user?.email || 'Not signed in'}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: Colors.background,
    padding: Spacing.xl,
  },
  iconContainer: {
    marginBottom: Spacing.lg,
  },
  title: {
    fontSize: Typography.size.xxl,
    fontWeight: '700',
    color: Colors.textPrimary,
    marginBottom: Spacing.sm,
  },
  email: {
    fontSize: Typography.size.md,
    color: Colors.textSecondary,
  },
});