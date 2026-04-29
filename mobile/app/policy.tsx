import { router } from 'expo-router';
import { useEffect, useMemo, useState } from 'react';
import { StyleSheet, Text } from 'react-native';
import { createCase } from '@/api/client';
import { useAuth } from '@/auth/AuthContext';
import { AppHeader } from '@/components/AppHeader';
import { Button } from '@/components/Button';
import { ErrorBanner } from '@/components/ErrorBanner';
import { Loading } from '@/components/Loading';
import { PolicyWorkspace } from '@/components/PolicyWorkspace';
import { Screen } from '@/components/Screen';
import { colors, spacing } from '@/theme/theme';
import { getPolicyWorkspaceCaseId } from '@/utils/policyWorkspace';

export default function PolicyScreen() {
  const { token, user } = useAuth();
  const [ready, setReady] = useState(false);
  const [error, setError] = useState('');
  const policyCaseId = useMemo(() => (user ? getPolicyWorkspaceCaseId(user.user_id) : ''), [user]);

  useEffect(() => {
    if (!token) {
      router.replace('/auth/login');
      return;
    }
    if (!policyCaseId) return;
    let active = true;
    async function ensurePolicyCase() {
      setReady(false);
      setError('');
      try {
        await createCase(policyCaseId);
      } catch (err) {
        const message = err instanceof Error ? err.message : '';
        if (!message.includes('already exists')) {
          if (active) setError(message || 'Failed to prepare policy workspace');
          return;
        }
      }
      if (active) setReady(true);
    }
    ensurePolicyCase();
    return () => {
      active = false;
    };
  }, [policyCaseId, token]);

  if (!ready && !error) return <Loading />;

  return (
    <Screen>
      <AppHeader />
      <Button title="Back to Cases" variant="ghost" onPress={() => router.push('/cases')} />
      <Text style={styles.kicker}>Policy Q&A</Text>
      <Text style={styles.title}>Ask questions about your insurance policy</Text>
      <Text style={styles.subtitle}>
        Upload a PDF or choose an existing policy, then ask coverage and policy fact questions.
      </Text>
      <ErrorBanner message={error} />
      {ready && <PolicyWorkspace caseId={policyCaseId} />}
    </Screen>
  );
}

const styles = StyleSheet.create({
  kicker: {
    color: colors.blue,
    fontSize: 13,
    fontWeight: '900',
    letterSpacing: 1.4,
    textTransform: 'uppercase',
  },
  title: {
    color: colors.text,
    fontSize: 28,
    fontWeight: '900',
    lineHeight: 34,
  },
  subtitle: {
    color: colors.muted,
    fontSize: 15,
    lineHeight: 22,
    marginBottom: spacing.sm,
  },
});
