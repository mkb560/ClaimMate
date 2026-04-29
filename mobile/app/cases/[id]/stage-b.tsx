import { router, useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { StyleSheet, Text } from 'react-native';
import { getCaseSnapshot, patchAccidentStageB } from '@/api/client';
import { useAuth } from '@/auth/AuthContext';
import { AppHeader } from '@/components/AppHeader';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { CaseStepper } from '@/components/CaseStepper';
import { ErrorBanner } from '@/components/ErrorBanner';
import { Field } from '@/components/Field';
import { Loading } from '@/components/Loading';
import { PolicyWorkspace } from '@/components/PolicyWorkspace';
import { Screen } from '@/components/Screen';
import { colors, spacing } from '@/theme/theme';
import { EMPTY_STAGE_B, StageBData } from '@/types/forms';
import { textValue } from '@/utils/format';

function buildInitial(stageB: Record<string, unknown> | null): StageBData {
  const b = stageB || {};
  return {
    detailed_narrative: textValue(b.detailed_narrative),
    damage_summary: textValue(b.damage_summary),
    weather_conditions: textValue(b.weather_conditions),
    road_conditions: textValue(b.road_conditions),
    police_report_number: textValue(b.police_report_number),
    adjuster_name: textValue(b.adjuster_name),
    repair_shop_name: textValue(b.repair_shop_name),
    follow_up_notes: textValue(b.follow_up_notes),
  };
}

export default function StageBScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const caseId = String(id);
  const { token } = useAuth();
  const [form, setForm] = useState<StageBData>(EMPTY_STAGE_B);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!token) {
      router.replace('/auth/login');
      return;
    }
    let active = true;
    async function load() {
      setLoading(true);
      try {
        const snapshot = await getCaseSnapshot(caseId);
        if (active) setForm(buildInitial(snapshot.stage_b));
      } catch {
        if (active) setForm(EMPTY_STAGE_B);
      } finally {
        if (active) setLoading(false);
      }
    }
    load();
    return () => {
      active = false;
    };
  }, [caseId, token]);

  function set<K extends keyof StageBData>(key: K, value: StageBData[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function saveAndContinue() {
    setSaving(true);
    setError('');
    try {
      await patchAccidentStageB(caseId, {
        detailed_narrative: form.detailed_narrative || null,
        damage_summary: form.damage_summary || null,
        weather_conditions: form.weather_conditions || null,
        road_conditions: form.road_conditions || null,
        police_report_number: form.police_report_number || null,
        adjuster_name: form.adjuster_name || null,
        repair_shop_name: form.repair_shop_name || null,
        follow_up_notes: form.follow_up_notes || null,
        stage_completed_at: new Date().toISOString(),
      });
      router.push(`/cases/${caseId}/report`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <Loading />;

  return (
    <Screen>
      <AppHeader />
      <CaseStepper caseId={caseId} current={1} />
      <Button title="Back" variant="ghost" onPress={() => router.push(`/cases/${caseId}/stage-a`)} />
      <Text style={styles.title}>Step 2: Accident Details</Text>
      <Text style={styles.subtitle}>Add policy materials and the full accident narrative.</Text>
      <PolicyWorkspace caseId={caseId} showAsk={false} />

      <Card style={styles.card}>
        <Text style={styles.section}>Narrative</Text>
        <Field label="Detailed Account" value={form.detailed_narrative} onChangeText={(value) => set('detailed_narrative', value)} multilineField />
        <Field label="Damage Summary" value={form.damage_summary} onChangeText={(value) => set('damage_summary', value)} multilineField />
      </Card>

      <Card style={styles.card}>
        <Text style={styles.section}>Conditions</Text>
        <Field label="Weather" value={form.weather_conditions} onChangeText={(value) => set('weather_conditions', value)} />
        <Field label="Road Conditions" value={form.road_conditions} onChangeText={(value) => set('road_conditions', value)} />
      </Card>

      <Card style={styles.card}>
        <Text style={styles.section}>Contacts & Records</Text>
        <Field label="Police Report #" value={form.police_report_number} onChangeText={(value) => set('police_report_number', value)} />
        <Field label="Adjuster Name" value={form.adjuster_name} onChangeText={(value) => set('adjuster_name', value)} />
        <Field label="Repair Shop" value={form.repair_shop_name} onChangeText={(value) => set('repair_shop_name', value)} />
        <Field label="Follow-up Notes" value={form.follow_up_notes} onChangeText={(value) => set('follow_up_notes', value)} multilineField />
      </Card>

      <ErrorBanner message={error} />
      <Button title="Save & Continue" loading={saving} onPress={saveAndContinue} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: {
    color: colors.text,
    fontSize: 26,
    fontWeight: '900',
  },
  subtitle: {
    color: colors.muted,
    fontSize: 15,
  },
  card: {
    gap: spacing.md,
  },
  section: {
    color: colors.text,
    fontSize: 18,
    fontWeight: '900',
  },
});
