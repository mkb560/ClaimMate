import { router } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useAuth } from '@/auth/AuthContext';
import { colors, radius, spacing } from '@/theme/theme';

export function AppHeader() {
  const { logout } = useAuth();

  async function handleSignOut() {
    await logout();
    router.replace('/auth/login');
  }

  return (
    <View style={styles.header}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Go to cases home"
        onPress={() => router.replace('/cases')}
        style={({ pressed }) => [styles.brand, pressed && styles.pressed]}
      >
        <View style={styles.logo}>
          <Text style={styles.logoText}>C</Text>
        </View>
        <Text style={styles.brandText}>ClaimMate</Text>
      </Pressable>

      <View style={styles.actions}>
        <Pressable
          accessibilityRole="button"
          onPress={() => router.push('/policy')}
          style={({ pressed }) => [styles.actionButton, pressed && styles.pressed]}
        >
          <Text style={styles.actionText}>Policy Q&A</Text>
        </Pressable>
        <Pressable
          accessibilityRole="button"
          onPress={handleSignOut}
          style={({ pressed }) => [styles.actionButton, styles.signOutButton, pressed && styles.pressed]}
        >
          <Text style={[styles.actionText, styles.signOutText]}>Sign out</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  header: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing.sm,
    justifyContent: 'space-between',
    padding: spacing.sm,
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.08,
    shadowRadius: 18,
  },
  brand: {
    alignItems: 'center',
    flexDirection: 'row',
    flexShrink: 1,
    gap: spacing.sm,
    minWidth: 0,
  },
  logo: {
    alignItems: 'center',
    backgroundColor: colors.cyan,
    borderRadius: radius.pill,
    height: 42,
    justifyContent: 'center',
    width: 42,
  },
  logoText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '900',
  },
  brandText: {
    color: colors.text,
    flexShrink: 1,
    fontSize: 22,
    fontWeight: '900',
  },
  actions: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.xs,
  },
  actionButton: {
    borderRadius: radius.pill,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.sm,
  },
  signOutButton: {
    backgroundColor: '#f8fafc',
  },
  actionText: {
    color: colors.blueDark,
    fontSize: 13,
    fontWeight: '900',
  },
  signOutText: {
    color: colors.muted,
  },
  pressed: {
    opacity: 0.72,
  },
});
