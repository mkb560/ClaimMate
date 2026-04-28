import { router } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { colors, radius, spacing } from '@/theme/theme';

const STEPS = [
  { label: 'Basics', path: 'stage-a' },
  { label: 'Details', path: 'stage-b' },
  { label: 'Report', path: 'report' },
  { label: 'Chat', path: 'chat' },
];

export function CaseStepper({ caseId, current }: { caseId: string; current: number }) {
  return (
    <View style={styles.wrap}>
      {STEPS.map((step, index) => {
        const active = index === current;
        const done = index < current;
        return (
          <Pressable
            key={step.path}
            onPress={() => router.push(`/cases/${caseId}/${step.path}`)}
            style={styles.step}
          >
            <View style={[styles.badge, done && styles.doneBadge, active && styles.activeBadge]}>
              <Text style={[styles.badgeText, (done || active) && styles.badgeTextActive]}>
                {done ? 'OK' : index + 1}
              </Text>
            </View>
            <Text style={[styles.label, active && styles.activeLabel]}>{step.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    backgroundColor: 'rgba(255,255,255,0.9)',
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing.xs,
    justifyContent: 'space-between',
    padding: spacing.sm,
  },
  step: {
    alignItems: 'center',
    flex: 1,
    gap: 4,
  },
  badge: {
    alignItems: 'center',
    backgroundColor: '#f1f5f9',
    borderRadius: radius.pill,
    height: 32,
    justifyContent: 'center',
    width: 32,
  },
  activeBadge: {
    backgroundColor: colors.blue,
  },
  doneBadge: {
    backgroundColor: colors.green,
  },
  badgeText: {
    color: colors.muted,
    fontSize: 11,
    fontWeight: '900',
  },
  badgeTextActive: {
    color: '#fff',
  },
  label: {
    color: colors.muted,
    fontSize: 12,
    fontWeight: '800',
  },
  activeLabel: {
    color: colors.text,
  },
});
