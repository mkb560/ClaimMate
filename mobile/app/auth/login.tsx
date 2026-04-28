import { Link, router } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useAuth } from '@/auth/AuthContext';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { ErrorBanner } from '@/components/ErrorBanner';
import { Field } from '@/components/Field';
import { Screen } from '@/components/Screen';
import { colors, spacing } from '@/theme/theme';

export default function LoginScreen() {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleLogin() {
    setLoading(true);
    setError('');
    try {
      await login(email.trim(), password);
      router.replace('/cases');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <Screen contentStyle={styles.content}>
      <View style={styles.hero}>
        <Text style={styles.logo}>ClaimMate</Text>
        <Text style={styles.title}>Your claims copilot, now on Android.</Text>
        <Text style={styles.subtitle}>Sign in to continue your accident intake, policy Q&A, and case chat.</Text>
      </View>
      <Card style={styles.card}>
        <Field label="Email" value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" />
        <Field label="Password" value={password} onChangeText={setPassword} secureTextEntry />
        <ErrorBanner message={error} />
        <Button title="Sign in" loading={loading} onPress={handleLogin} disabled={!email || !password} />
        <Text style={styles.footerText}>
          New to ClaimMate? <Link href="/auth/register" style={styles.link}>Create an account</Link>
        </Text>
      </Card>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: {
    justifyContent: 'center',
    minHeight: '100%',
  },
  hero: {
    gap: spacing.sm,
  },
  logo: {
    color: colors.blue,
    fontSize: 34,
    fontWeight: '900',
  },
  title: {
    color: colors.text,
    fontSize: 26,
    fontWeight: '900',
    lineHeight: 32,
  },
  subtitle: {
    color: colors.muted,
    fontSize: 15,
    lineHeight: 22,
  },
  card: {
    gap: spacing.md,
  },
  footerText: {
    color: colors.muted,
    textAlign: 'center',
  },
  link: {
    color: colors.blue,
    fontWeight: '800',
  },
});
