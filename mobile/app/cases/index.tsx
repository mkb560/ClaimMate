import { router, useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { Alert, StyleSheet, Text, View } from 'react-native';
import { useAuth } from '@/auth/AuthContext';
import { createCase, deleteCase, getUserCases, UserCaseEntry } from '@/api/client';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { ErrorBanner } from '@/components/ErrorBanner';
import { Loading } from '@/components/Loading';
import { Screen } from '@/components/Screen';
import { colors, radius, spacing } from '@/theme/theme';
import { isPolicyWorkspaceCaseId } from '@/utils/policyWorkspace';

function caseTitle(caseId: string): string {
  const suffix = caseId.replace(/^case-/, '').slice(0, 8).toUpperCase();
  return `Accident case ${suffix}`;
}

export default function CasesScreen() {
  const { token, user, logout } = useAuth();
  const [cases, setCases] = useState<UserCaseEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');

  const loadCases = useCallback(async () => {
    if (!token) {
      router.replace('/auth/login');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const entries = await getUserCases();
      setCases(entries.filter((entry) => !isPolicyWorkspaceCaseId(entry.case_id)));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load cases');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useFocusEffect(useCallback(() => {
    loadCases();
  }, [loadCases]));

  async function startCase() {
    setCreating(true);
    setError('');
    try {
      const created = await createCase();
      router.push(`/cases/${created.case_id}/stage-a`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Create case failed');
    } finally {
      setCreating(false);
    }
  }

  async function confirmDelete(caseId: string) {
    Alert.alert('Delete case?', 'This removes the demo case and related messages.', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: async () => {
          await deleteCase(caseId).catch(() => undefined);
          setCases((prev) => prev.filter((item) => item.case_id !== caseId));
        },
      },
    ]);
  }

  if (loading) return <Loading />;

  return (
    <Screen>
      <View style={styles.hero}>
        <Text style={styles.kicker}>ClaimMate workspace</Text>
        <Text style={styles.title}>Your Cases</Text>
        <Text style={styles.subtitle}>
          Start accident intake immediately, then add policy materials, generate a report, and collaborate in chat.
        </Text>
        <View style={styles.heroActions}>
          <Button title="+ Start New Case" onPress={startCase} loading={creating} style={styles.primaryCta} />
          <Button title="Policy Q&A" variant="secondary" onPress={() => router.push('/policy')} />
        </View>
      </View>

      <View style={styles.topRow}>
        <Text style={styles.signedIn}>Signed in as {user?.display_name || user?.email}</Text>
        <Button title="Sign out" variant="ghost" onPress={() => logout().then(() => router.replace('/auth/login'))} />
      </View>

      <ErrorBanner message={error} />
      {cases.length === 0 ? (
        <Card style={styles.empty}>
          <Text style={styles.emptyTitle}>No cases yet.</Text>
          <Text style={styles.emptyText}>Create one and ClaimMate will open Accident Basics right away.</Text>
          <Button title="Start your first case" onPress={startCase} loading={creating} />
        </Card>
      ) : (
        cases.map((entry) => (
          <Card key={entry.case_id} style={styles.caseCard}>
            <View style={{ flex: 1 }}>
              <Text style={styles.caseTitle}>{caseTitle(entry.case_id)}</Text>
              <Text style={styles.caseId}>{entry.case_id}</Text>
              <Text style={styles.role}>Role: {entry.role}</Text>
            </View>
            <View style={styles.caseActions}>
              <Button title="Open" onPress={() => router.push(`/cases/${entry.case_id}/stage-a`)} />
              <Button title="Delete" variant="danger" onPress={() => confirmDelete(entry.case_id)} />
            </View>
          </Card>
        ))
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  hero: {
    backgroundColor: colors.blueDark,
    borderRadius: radius.lg,
    gap: spacing.sm,
    padding: spacing.lg,
  },
  kicker: {
    color: '#a5f3fc',
    fontSize: 12,
    fontWeight: '900',
    letterSpacing: 2,
    textTransform: 'uppercase',
  },
  title: {
    color: '#fff',
    fontSize: 34,
    fontWeight: '900',
  },
  subtitle: {
    color: '#dbeafe',
    fontSize: 15,
    lineHeight: 22,
  },
  heroActions: {
    gap: spacing.sm,
    marginTop: spacing.sm,
  },
  primaryCta: {
    minHeight: 58,
  },
  topRow: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  signedIn: {
    color: colors.muted,
    flex: 1,
    fontSize: 13,
  },
  empty: {
    alignItems: 'center',
    gap: spacing.sm,
    paddingVertical: 42,
  },
  emptyTitle: {
    color: colors.text,
    fontSize: 20,
    fontWeight: '900',
  },
  emptyText: {
    color: colors.muted,
    textAlign: 'center',
  },
  caseCard: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.md,
  },
  caseTitle: {
    color: colors.text,
    fontSize: 18,
    fontWeight: '900',
  },
  caseId: {
    color: '#94a3b8',
    marginTop: 3,
  },
  role: {
    color: colors.muted,
    fontSize: 12,
    marginTop: 4,
  },
  caseActions: {
    gap: spacing.xs,
  },
});
