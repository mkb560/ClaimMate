import { router, useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { StyleSheet, Text } from 'react-native';
import { acceptInvite, lookupInvite } from '@/api/client';
import { useAuth } from '@/auth/AuthContext';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { ErrorBanner } from '@/components/ErrorBanner';
import { Loading } from '@/components/Loading';
import { Screen } from '@/components/Screen';
import { colors, spacing } from '@/theme/theme';

export default function InviteAcceptScreen() {
  const { token } = useAuth();
  const params = useLocalSearchParams<{ token?: string }>();
  const inviteToken = String(params.token || '');
  const [caseId, setCaseId] = useState('');
  const [role, setRole] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!token) {
      router.replace('/auth/login');
      return;
    }
    if (!inviteToken) {
      setError('Missing invite token');
      setLoading(false);
      return;
    }
    let active = true;
    lookupInvite(inviteToken)
      .then((invite) => {
        if (!active) return;
        setCaseId(invite.case_id);
        setRole(invite.role);
      })
      .catch((err) => active && setError(err instanceof Error ? err.message : 'Invite not found'))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [inviteToken, token]);

  async function accept() {
    setBusy(true);
    setError('');
    try {
      const result = await acceptInvite(inviteToken);
      router.replace(`/cases/${result.case_id}/chat`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Accept invite failed');
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <Loading />;

  return (
    <Screen contentStyle={styles.content}>
      <Card style={styles.card}>
        <Text style={styles.title}>Join ClaimMate Case</Text>
        <Text style={styles.body}>You were invited to join case {caseId || 'unknown'} as {role || 'member'}.</Text>
        <ErrorBanner message={error} />
        <Button title="Accept Invite" onPress={accept} loading={busy} disabled={!inviteToken || !caseId} />
        <Button title="Back to Cases" variant="ghost" onPress={() => router.replace('/cases')} />
      </Card>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: {
    justifyContent: 'center',
    minHeight: '100%',
  },
  card: {
    gap: spacing.md,
  },
  title: {
    color: colors.text,
    fontSize: 26,
    fontWeight: '900',
  },
  body: {
    color: colors.muted,
    fontSize: 15,
    lineHeight: 22,
  },
});
