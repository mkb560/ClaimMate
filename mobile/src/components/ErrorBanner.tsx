import { StyleSheet, Text } from 'react-native';

export function ErrorBanner({ message }: { message: string }) {
  if (!message) return null;
  return <Text style={styles.error}>{message}</Text>;
}

const styles = StyleSheet.create({
  error: {
    backgroundColor: '#fef2f2',
    borderRadius: 12,
    color: '#dc2626',
    fontSize: 14,
    fontWeight: '600',
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
});
