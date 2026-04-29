import { DateTimePickerAndroid } from '@react-native-community/datetimepicker';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { colors, radius, spacing } from '@/theme/theme';
import {
  dateTimeLocalToDate,
  dateToDateTimeLocal,
  formatDateTimeLocal,
} from '@/utils/format';

type DateTimeFieldProps = {
  label: string;
  value: string;
  onChange: (value: string) => void;
};

export function DateTimeField({ label, value, onChange }: DateTimeFieldProps) {
  const selectedDate = dateTimeLocalToDate(value);
  const displayValue = value ? formatDateTimeLocal(value) : '';

  function openTimePicker(baseDate: Date) {
    DateTimePickerAndroid.open({
      value: baseDate,
      mode: 'time',
      is24Hour: false,
      onChange: (event, pickedTime) => {
        if (event.type !== 'set' || !pickedTime) return;
        const next = new Date(baseDate);
        next.setHours(pickedTime.getHours(), pickedTime.getMinutes(), 0, 0);
        onChange(dateToDateTimeLocal(next));
      },
    });
  }

  function openDatePicker() {
    const baseDate = selectedDate || new Date();
    DateTimePickerAndroid.open({
      value: baseDate,
      mode: 'date',
      onChange: (event, pickedDate) => {
        if (event.type !== 'set' || !pickedDate) return;
        const next = new Date(pickedDate);
        next.setHours(baseDate.getHours(), baseDate.getMinutes(), 0, 0);
        onChange(dateToDateTimeLocal(next));
        setTimeout(() => openTimePicker(next), 0);
      },
    });
  }

  function useNow() {
    onChange(dateToDateTimeLocal(new Date()));
  }

  return (
    <View style={styles.wrap}>
      <Text style={styles.label}>{label}</Text>
      <View style={styles.row}>
        <Pressable
          accessibilityRole="button"
          onPress={openDatePicker}
          style={({ pressed }) => [styles.input, pressed && styles.pressed]}
        >
          <Text style={[styles.value, !displayValue && styles.placeholder]}>
            {displayValue || 'Tap to choose date & time'}
          </Text>
          <Text style={styles.icon}>Calendar</Text>
        </Pressable>
        <Pressable
          accessibilityRole="button"
          onPress={useNow}
          style={({ pressed }) => [styles.nowButton, pressed && styles.pressed]}
        >
          <Text style={styles.nowText}>Now</Text>
        </Pressable>
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
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.sm,
  },
  input: {
    alignItems: 'center',
    backgroundColor: '#fff',
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    flex: 1,
    flexDirection: 'row',
    gap: spacing.sm,
    minHeight: 52,
    paddingHorizontal: spacing.md,
  },
  value: {
    color: colors.text,
    flex: 1,
    fontSize: 16,
    fontWeight: '700',
  },
  placeholder: {
    color: '#94a3b8',
    fontWeight: '500',
  },
  icon: {
    color: colors.blueDark,
    fontSize: 12,
    fontWeight: '900',
  },
  nowButton: {
    alignItems: 'center',
    backgroundColor: colors.blue,
    borderRadius: radius.md,
    justifyContent: 'center',
    minHeight: 52,
    paddingHorizontal: spacing.md,
  },
  nowText: {
    color: '#fff',
    fontSize: 15,
    fontWeight: '900',
  },
  pressed: {
    opacity: 0.75,
  },
});
