import * as DocumentPicker from 'expo-document-picker';
import { useCallback, useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import {
  askPolicyQuestion,
  CasePolicyStatusResponse,
  DemoPolicy,
  getCasePolicyStatus,
  getDemoPolicies,
  seedDemoPolicy,
  uploadPolicy,
} from '@/api/client';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { ErrorBanner } from '@/components/ErrorBanner';
import { Field } from '@/components/Field';
import { Loading } from '@/components/Loading';
import { colors, spacing } from '@/theme/theme';

export function PolicyWorkspace({
  caseId,
  showAsk = true,
  canEdit = true,
}: {
  caseId: string;
  showAsk?: boolean;
  canEdit?: boolean;
}) {
  const [status, setStatus] = useState<CasePolicyStatusResponse | null>(null);
  const [policies, setPolicies] = useState<DemoPolicy[]>([]);
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [citations, setCitations] = useState(0);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const refresh = useCallback(async () => {
    setError('');
    const [policyStatus, catalog] = await Promise.all([
      getCasePolicyStatus(caseId),
      getDemoPolicies(),
    ]);
    setStatus(policyStatus);
    setPolicies(catalog.policies);
  }, [caseId]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    refresh()
      .catch((err) => active && setError(err instanceof Error ? err.message : 'Failed to load policy workspace'))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [caseId, refresh]);

  async function chooseExisting(policy: DemoPolicy) {
    setBusy(true);
    setError('');
    try {
      await seedDemoPolicy(caseId, policy.policy_key);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load existing policy');
    } finally {
      setBusy(false);
    }
  }

  async function pickPolicyPdf() {
    const picked = await DocumentPicker.getDocumentAsync({
      type: 'application/pdf',
      copyToCacheDirectory: true,
    });
    if (picked.canceled || !picked.assets[0]) return;
    const asset = picked.assets[0];
    setBusy(true);
    setError('');
    try {
      await uploadPolicy(caseId, {
        uri: asset.uri,
        name: asset.name || 'policy.pdf',
        type: asset.mimeType || 'application/pdf',
      });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setBusy(false);
    }
  }

  async function ask() {
    setBusy(true);
    setError('');
    setAnswer('');
    try {
      const result = await askPolicyQuestion(caseId, question.trim());
      setAnswer(result.answer);
      setCitations(result.citations.length);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ask request failed');
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <Loading />;

  return (
    <View style={styles.wrap}>
      <Card style={styles.card}>
        <View style={styles.statusRow}>
          <Text style={styles.sectionTitle}>Your Policy</Text>
          {status?.has_policy && <Text style={styles.loaded}>Loaded</Text>}
        </View>
        {status?.has_policy ? (
          <Text style={styles.policyText}>
            {status.filename || status.source_label} is indexed ({status.chunk_count} chunks)
          </Text>
        ) : (
          <Text style={styles.muted}>Choose an existing policy or upload your own PDF.</Text>
        )}
        <ErrorBanner message={error} />
      </Card>

      {canEdit && (
        <Card style={styles.card}>
          <Text style={styles.sectionTitle}>Existing Policy</Text>
          <Text style={styles.muted}>Pick one of the sample policies to get started instantly.</Text>
          <View style={styles.list}>
            {policies.map((policy) => (
              <Button
                key={policy.policy_key}
                title={policy.label}
                variant="secondary"
                loading={busy}
                onPress={() => chooseExisting(policy)}
              />
            ))}
          </View>
          <Button title="Upload Policy PDF" onPress={pickPolicyPdf} loading={busy} />
        </Card>
      )}

      {showAsk && status?.has_policy && (
        <Card style={styles.card}>
          <Text style={styles.sectionTitle}>Ask About Your Policy</Text>
          <Field
            label="Question"
            value={question}
            onChangeText={setQuestion}
            placeholder="What is my liability coverage limit?"
            multilineField
          />
          <Button title="Ask AI" onPress={ask} loading={busy} disabled={!question.trim()} />
          {answer ? (
            <View style={styles.answerBox}>
              <Text style={styles.answer}>{answer}</Text>
              <Text style={styles.sourceText}>Sources: {citations}</Text>
            </View>
          ) : null}
        </Card>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    gap: spacing.md,
  },
  card: {
    gap: spacing.md,
  },
  statusRow: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  sectionTitle: {
    color: colors.text,
    fontSize: 18,
    fontWeight: '900',
  },
  loaded: {
    backgroundColor: '#dcfce7',
    borderRadius: 999,
    color: '#15803d',
    fontWeight: '900',
    paddingHorizontal: 12,
    paddingVertical: 5,
  },
  muted: {
    color: colors.muted,
    lineHeight: 20,
  },
  policyText: {
    backgroundColor: '#ecfdf5',
    borderRadius: 14,
    color: '#047857',
    fontWeight: '700',
    padding: 12,
  },
  list: {
    gap: spacing.sm,
  },
  answerBox: {
    backgroundColor: colors.surfaceSoft,
    borderRadius: 14,
    gap: spacing.sm,
    padding: spacing.md,
  },
  answer: {
    color: colors.text,
    fontSize: 15,
    lineHeight: 22,
  },
  sourceText: {
    color: colors.blueDark,
    fontWeight: '700',
  },
});
