import { ActivityIndicator, StyleSheet, View } from 'react-native';
import { colors } from '@/theme/theme';

export function Loading() {
  return (
    <View style={styles.wrap}>
      <ActivityIndicator color={colors.blue} size="large" />
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    alignItems: 'center',
    flex: 1,
    justifyContent: 'center',
    padding: 40,
  },
});
