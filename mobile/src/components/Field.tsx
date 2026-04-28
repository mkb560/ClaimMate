import { StyleSheet, Text, TextInput, TextInputProps, View } from 'react-native';
import { colors, radius, spacing } from '@/theme/theme';

type FieldProps = TextInputProps & {
  label: string;
  multilineField?: boolean;
};

export function Field({ label, multilineField = false, style, ...props }: FieldProps) {
  return (
    <View style={styles.wrap}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        placeholderTextColor="#94a3b8"
        style={[styles.input, multilineField && styles.multiline, style]}
        multiline={multilineField}
        textAlignVertical={multilineField ? 'top' : 'center'}
        {...props}
      />
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
  input: {
    minHeight: 48,
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    color: colors.text,
    fontSize: 16,
    paddingHorizontal: spacing.md,
    backgroundColor: '#fff',
  },
  multiline: {
    minHeight: 100,
    paddingTop: spacing.sm,
  },
});
