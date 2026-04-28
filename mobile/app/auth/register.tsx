import { Link, router } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, Text } from 'react-native';
import { useAuth } from '@/auth/AuthContext';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { ErrorBanner } from '@/components/ErrorBanner';
import { Field } from '@/components/Field';
import { Screen } from '@/components/Screen';
import { colors, spacing } from '@/theme/theme';

export default function RegisterScreen() {
  const { register } = useAuth();
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleRegister() {
    setLoading(true);
    setError('');
    try {
      await register(email.trim(), password, displayName.trim() || undefined);
      router.replace('/cases');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <Screen contentStyle={styles.content}>
      <Text style={styles.logo}>ClaimMate</Text>
      <Text style={styles.title}>Create your account</Text>
      <Card style={styles.card}>
        <Field label="Display name" value={displayName} onChangeText={setDisplayName} placeholder="Mingtao Ding" />
        <Field label="Email" value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" />
        <Field label="Password" value={password} onChangeText={setPassword} secureTextEntry />
        <ErrorBanner message={error} />
        <Button title="Create account" loading={loading} onPress={handleRegister} disabled={!email || !password} />
        <Text style={styles.footerText}>
          Already have an account? <Link href="/auth/login" style={styles.link}>Sign in</Link>
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
  logo: {
    color: colors.blue,
    fontSize: 34,
    fontWeight: '900',
  },
  title: {
    color: colors.text,
    fontSize: 26,
    fontWeight: '900',
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
