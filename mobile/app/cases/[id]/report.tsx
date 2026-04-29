import { router, useLocalSearchParams } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { generateAccidentReport, GenerateReportResponse, getAccidentReport } from '@/api/client';
import { useAuth } from '@/auth/AuthContext';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { CaseStepper } from '@/components/CaseStepper';
import { ErrorBanner } from '@/components/ErrorBanner';
import { Loading } from '@/components/Loading';
import { Screen } from '@/components/Screen';
import { colors, spacing } from '@/theme/theme';
import { formatBool, formatDateTime } from '@/utils/format';

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.fact}>
      <Text style={styles.factLabel}>{label}</Text>
      <Text style={styles.factValue}>{value}</Text>
    </View>
  );
}

export default function ReportScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const caseId = String(id);
  const { token } = useAuth();
  const [report, setReport] = useState<GenerateReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const loadReport = useCallback(async () => {
    try {
      const loaded = await getAccidentReport(caseId);
      setReport(loaded);
    } catch {
      setReport(null);
    }
  }, [caseId]);

  useEffect(() => {
    if (!token) {
      router.replace('/auth/login');
      return;
    }
    setLoading(true);
    loadReport().finally(() => setLoading(false));
  }, [caseId, loadReport, token]);

  async function generate() {
    setBusy(true);
    setError('');
    try {
      const generated = await generateAccidentReport(caseId);
      setReport(generated);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Generate report failed');
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <Loading />;

  const r = report?.report_payload;
  const visibleMissingItems = (r?.missing_items || []).filter(
    (item) => !/witness|injury follow-up/i.test(item)
  );

  return (
    <Screen>
      <CaseStepper caseId={caseId} current={2} />
      <Button title="Back" variant="ghost" onPress={() => router.push(`/cases/${caseId}/stage-b`)} />
      <View style={styles.headerRow}>
        <View style={{ flex: 1 }}>
          <Text style={styles.title}>Step 3: Accident Report</Text>
          <Text style={styles.subtitle}>Generate a clean, claim-ready accident summary.</Text>
        </View>
        <Button title={r ? 'Regenerate' : 'Generate'} loading={busy} onPress={generate} />
      </View>
      <ErrorBanner message={error} />

      {!r ? (
        <Card style={styles.card}>
          <Text style={styles.section}>No report yet</Text>
          <Text style={styles.muted}>Save Accident Basics and Details, then generate the report.</Text>
          <Button title="Generate Report" loading={busy} onPress={generate} />
        </Card>
      ) : (
        <>
          <Card style={styles.card}>
            <Text style={styles.kicker}>Claim-ready accident summary</Text>
            <Text style={styles.reportTitle}>Accident Report</Text>
            <Text style={styles.summary}>{r.damage_summary || r.accident_summary}</Text>
            <View style={styles.factGrid}>
              <Fact label="Accident Time" value={formatDateTime(r.occurrence_time)} />
              <Fact label="Location" value={r.location_summary || 'Not provided'} />
              <Fact label="Police Called" value={formatBool(r.police_called)} />
              <Fact label="Injuries" value={formatBool(r.injuries_reported)} />
            </View>
          </Card>

          <Card style={styles.card}>
            <Text style={styles.section}>People & Insurance</Text>
            {(r.party_comparison_rows || []).filter((row) => !['Claim number', 'Vehicle'].includes(row.field_label)).map((row) => (
              <View key={row.field_label} style={styles.tableRow}>
                <Text style={styles.tableLabel}>{row.field_label}</Text>
                <Text style={styles.tableValue}>You: {row.owner_value}</Text>
                <Text style={styles.tableValue}>Other: {row.other_party_value}</Text>
              </View>
            ))}
            <View style={styles.tableRow}>
              <Text style={styles.tableLabel}>VIN</Text>
              <Text style={styles.tableValue}>You: {r.owner_party?.vehicle?.vin || 'Unknown'}</Text>
              <Text style={styles.tableValue}>Other: {r.other_party?.vehicle?.vin || 'Unknown'}</Text>
            </View>
            <View style={styles.tableRow}>
              <Text style={styles.tableLabel}>Plate number</Text>
              <Text style={styles.tableValue}>You: {r.owner_party?.vehicle?.license_plate || 'Unknown'}</Text>
              <Text style={styles.tableValue}>Other: {r.other_party?.vehicle?.license_plate || 'Unknown'}</Text>
            </View>
          </Card>

          {r.detailed_narrative ? (
            <Card style={styles.card}>
              <Text style={styles.section}>Narrative</Text>
              <Text style={styles.paragraph}>{r.detailed_narrative}</Text>
            </Card>
          ) : null}

          <Card style={styles.card}>
            <Text style={styles.section}>Supporting Details</Text>
            <Fact label="Photos Attached" value={`${r.photo_attachments?.length || 0}`} />
            <Fact label="Weather" value={r.weather_conditions || 'Not provided'} />
            <Fact label="Road Conditions" value={r.road_conditions || 'Not provided'} />
            <Fact label="Repair Shop" value={r.repair_shop_name || 'Not provided'} />
          </Card>

          {visibleMissingItems.length ? (
            <Card style={styles.card}>
              <Text style={styles.section}>Still Needed</Text>
              {visibleMissingItems.map((item) => (
                <Text key={item} style={styles.muted}>- {item}</Text>
              ))}
            </Card>
          ) : null}

          <Button title="Continue to Chat" onPress={() => router.push(`/cases/${caseId}/chat`)} />
        </>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  headerRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.md,
  },
  title: {
    color: colors.text,
    fontSize: 26,
    fontWeight: '900',
  },
  subtitle: {
    color: colors.muted,
  },
  card: {
    gap: spacing.md,
  },
  kicker: {
    color: colors.blue,
    fontSize: 12,
    fontWeight: '900',
    letterSpacing: 1.2,
    textTransform: 'uppercase',
  },
  reportTitle: {
    color: colors.text,
    fontSize: 24,
    fontWeight: '900',
  },
  summary: {
    color: colors.text,
    fontSize: 15,
    lineHeight: 23,
  },
  factGrid: {
    gap: spacing.sm,
  },
  fact: {
    backgroundColor: colors.surfaceSoft,
    borderRadius: 14,
    gap: 4,
    padding: spacing.md,
  },
  factLabel: {
    color: colors.muted,
    fontSize: 12,
    fontWeight: '900',
    textTransform: 'uppercase',
  },
  factValue: {
    color: colors.text,
    fontSize: 15,
    fontWeight: '800',
  },
  section: {
    color: colors.text,
    fontSize: 18,
    fontWeight: '900',
  },
  tableRow: {
    borderBottomColor: colors.border,
    borderBottomWidth: 1,
    gap: 4,
    paddingBottom: spacing.sm,
  },
  tableLabel: {
    color: colors.text,
    fontWeight: '900',
  },
  tableValue: {
    color: colors.muted,
  },
  paragraph: {
    color: colors.text,
    fontSize: 15,
    lineHeight: 23,
  },
  muted: {
    color: colors.muted,
  },
});
