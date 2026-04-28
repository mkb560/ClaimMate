import { Pressable, StyleSheet, Text, View } from 'react-native';
import { colors, radius, spacing } from '@/theme/theme';

export type TriState = 'unknown' | 'true' | 'false';

const OPTIONS: { value: TriState; label: string }[] = [
  { value: 'unknown', label: '?' },
  { value: 'true', label: 'Yes' },
  { value: 'false', label: 'No' },
];

export function TriStateToggle({
  label,
  value,
  onChange,
}: {
  label: string;
  value: TriState;
  onChange: (value: TriState) => void;
}) {
  return (
    <View style={styles.wrap}>
      <Text style={styles.label}>{label}</Text>
      <View style={styles.row}>
        {OPTIONS.map((option) => {
          const selected = option.value === value;
          return (
            <Pressable
              key={option.value}
              onPress={() => onChange(option.value)}
              style={[styles.option, selected && styles.selected]}
            >
              <Text style={[styles.optionText, selected && styles.selectedText]}>
                {option.label}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    gap: spacing.xs,
  },
  label: {
    color: colors.text,
    fontSize: 14,
    fontWeight: '700',
  },
  row: {
    flexDirection: 'row',
    gap: spacing.xs,
  },
  option: {
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    minWidth: 62,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.sm,
  },
  selected: {
    backgroundColor: '#eff6ff',
    borderColor: colors.blue,
  },
  optionText: {
    color: colors.muted,
    fontWeight: '700',
    textAlign: 'center',
  },
  selectedText: {
    color: colors.blueDark,
  },
});
