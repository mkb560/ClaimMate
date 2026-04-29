import * as ImagePicker from 'expo-image-picker';
import { router, useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import {
  CasePolicyStatusResponse,
  getCasePolicyStatus,
  getCaseSnapshot,
  patchAccidentStageA,
  uploadIncidentPhoto,
} from '@/api/client';
import { useAuth } from '@/auth/AuthContext';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { CaseStepper } from '@/components/CaseStepper';
import { ErrorBanner } from '@/components/ErrorBanner';
import { Field } from '@/components/Field';
import { Loading } from '@/components/Loading';
import { Screen } from '@/components/Screen';
import { TriState, TriStateToggle } from '@/components/TriStateToggle';
import { colors, spacing } from '@/theme/theme';
import { EMPTY_STAGE_A, StageAData } from '@/types/forms';
import { dateTimeLocalToIso, textValue, toDateTimeLocal } from '@/utils/format';

type PhotoCategory = 'owner_damage' | 'overview' | 'other_damage' | 'other';
type PhotoSource = 'camera' | 'gallery';

const PHOTO_CHANNELS: { category: PhotoCategory; title: string; hint: string }[] = [
  {
    category: 'owner_damage',
    title: 'My Vehicle Damage',
    hint: 'Close-ups of your vehicle damage.',
  },
  {
    category: 'overview',
    title: 'Scene / Overview',
    hint: 'Road, lane, signal, and accident position.',
  },
  {
    category: 'other_damage',
    title: "Other Party's Vehicle",
    hint: 'Photos of the other vehicle and visible damage.',
  },
  {
    category: 'other',
    title: 'Other',
    hint: 'Receipts, extra angles, or anything else useful.',
  },
];

const EMPTY_PHOTO_COUNTS: Record<PhotoCategory, number> = {
  owner_damage: 0,
  overview: 0,
  other_damage: 0,
  other: 0,
};

function countPhotosByCategory(photos: unknown[]): Record<PhotoCategory, number> {
  return photos.reduce<Record<PhotoCategory, number>>((counts, item) => {
    const category = (item as { category?: unknown })?.category;
    if (category === 'owner_damage' || category === 'overview' || category === 'other_damage' || category === 'other') {
      counts[category] += 1;
    }
    return counts;
  }, { ...EMPTY_PHOTO_COUNTS });
}

function boolToTriState(value: unknown): TriState {
  if (value === true) return 'true';
  if (value === false) return 'false';
  return 'unknown';
}

function triStateToBool(value: TriState): boolean | null {
  if (value === 'true') return true;
  if (value === 'false') return false;
  return null;
}

function userDisplayName(user: ReturnType<typeof useAuth>['user']): string {
  if (!user) return '';
  return textValue(user.display_name) || user.email.split('@')[0] || '';
}

function firstPolicyholder(prefill?: CasePolicyStatusResponse['prefill']): string {
  const policyholders = prefill?.policyholders;
  if (!policyholders) return '';
  return policyholders.split(',')[0]?.trim() || '';
}

function buildInitial(
  stageA: unknown,
  prefill: CasePolicyStatusResponse['prefill'] | undefined,
  user: ReturnType<typeof useAuth>['user']
): StageAData {
  const a = (stageA as Record<string, unknown>) || {};
  const loc = (a.location as Record<string, unknown>) || {};
  const own = (a.owner_party as Record<string, unknown>) || {};
  const oth = (a.other_party as Record<string, unknown>) || {};
  const ownVehicle = (own.vehicle as Record<string, unknown>) || {};
  const othVehicle = (oth.vehicle as Record<string, unknown>) || {};
  return {
    occurred_at: toDateTimeLocal(a.occurred_at),
    address: textValue(loc.address),
    quick_summary: textValue(a.quick_summary),
    owner_name: textValue(own.name) || userDisplayName(user) || firstPolicyholder(prefill),
    owner_phone: textValue(own.phone),
    owner_insurer: textValue(own.insurer) || textValue(prefill?.insurer),
    owner_policy_number: textValue(own.policy_number) || textValue(prefill?.policy_number),
    owner_vin: textValue(ownVehicle.vin),
    owner_plate_number: textValue(ownVehicle.license_plate),
    other_name: textValue(oth.name),
    other_phone: textValue(oth.phone),
    other_insurer: textValue(oth.insurer),
    other_policy_number: textValue(oth.policy_number),
    other_vin: textValue(othVehicle.vin),
    other_plate_number: textValue(othVehicle.license_plate),
    injuries_reported: boolToTriState(a.injuries_reported),
    police_called: boolToTriState(a.police_called),
    drivable: boolToTriState(a.drivable),
    tow_requested: boolToTriState(a.tow_requested),
  };
}

export default function StageAScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const caseId = String(id);
  const { token, user } = useAuth();
  const [form, setForm] = useState<StageAData>(EMPTY_STAGE_A);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [photoBusyKey, setPhotoBusyKey] = useState<string | null>(null);
  const [photoCounts, setPhotoCounts] = useState<Record<PhotoCategory, number>>(EMPTY_PHOTO_COUNTS);
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
        const [snapshot, policyStatus] = await Promise.all([
          getCaseSnapshot(caseId),
          getCasePolicyStatus(caseId).catch(() => null),
        ]);
        if (active) {
          setForm(buildInitial(snapshot.stage_a, policyStatus?.prefill, user));
          const photos = (snapshot.stage_a?.photo_attachments as unknown[]) || [];
          setPhotoCounts(countPhotosByCategory(photos));
        }
      } catch {
        if (active) setForm(buildInitial(null, undefined, user));
      } finally {
        if (active) setLoading(false);
      }
    }
    load();
    return () => {
      active = false;
    };
  }, [caseId, token, user]);

  function set<K extends keyof StageAData>(key: K, value: StageAData[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function saveAndContinue() {
    setSaving(true);
    setError('');
    try {
      await patchAccidentStageA(caseId, {
        occurred_at: dateTimeLocalToIso(form.occurred_at),
        location: { address: form.address || null },
        quick_summary: form.quick_summary,
        owner_party: {
          role: 'owner',
          name: form.owner_name,
          phone: form.owner_phone || null,
          insurer: form.owner_insurer || null,
          policy_number: form.owner_policy_number || null,
          vehicle: {
            vin: form.owner_vin || null,
            license_plate: form.owner_plate_number || null,
          },
        },
        other_party: {
          role: 'other_driver',
          name: form.other_name,
          phone: form.other_phone || null,
          insurer: form.other_insurer || null,
          policy_number: form.other_policy_number || null,
          vehicle: {
            vin: form.other_vin || null,
            license_plate: form.other_plate_number || null,
          },
        },
        injuries_reported: triStateToBool(form.injuries_reported),
        police_called: triStateToBool(form.police_called),
        drivable: triStateToBool(form.drivable),
        tow_requested: triStateToBool(form.tow_requested),
        stage_completed_at: new Date().toISOString(),
      });
      router.push(`/cases/${caseId}/stage-b`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  }

  async function uploadPhoto(source: PhotoSource, category: PhotoCategory) {
    const busyKey = `${category}:${source}`;
    setPhotoBusyKey(busyKey);
    setError('');
    try {
      if (source === 'camera') {
        const permission = await ImagePicker.requestCameraPermissionsAsync();
        if (!permission.granted) throw new Error('Camera permission is required');
      } else {
        const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
        if (!permission.granted) throw new Error('Photo library permission is required');
      }
      const result = source === 'camera'
        ? await ImagePicker.launchCameraAsync({ quality: 0.75 })
        : await ImagePicker.launchImageLibraryAsync({ mediaTypes: ImagePicker.MediaTypeOptions.Images, quality: 0.75 });
      if (result.canceled || !result.assets[0]) return;
      const asset = result.assets[0];
      await uploadIncidentPhoto(caseId, {
        uri: asset.uri,
        name: asset.fileName || `incident-${Date.now()}.jpg`,
        type: asset.mimeType || 'image/jpeg',
      }, category);
      setPhotoCounts((counts) => ({ ...counts, [category]: counts[category] + 1 }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Photo upload failed');
    } finally {
      setPhotoBusyKey(null);
    }
  }

  if (loading) return <Loading />;

  return (
    <Screen>
      <CaseStepper caseId={caseId} current={0} />
      <Button title="Back to Cases" variant="ghost" onPress={() => router.push('/cases')} />
      <Text style={styles.title}>Step 1: Accident Basics</Text>
      <Text style={styles.subtitle}>Fill in what you have now. You can update anytime.</Text>
      <Card style={styles.card}>
        <Text style={styles.section}>Accident Details</Text>
        <Field label="Date & Time" value={form.occurred_at} onChangeText={(value) => set('occurred_at', value)} placeholder="2026-04-28T14:30" />
        <Field label="Location" value={form.address} onChangeText={(value) => set('address', value)} placeholder="123 Main St, Los Angeles, CA" />
        <Field label="Quick Summary" value={form.quick_summary} onChangeText={(value) => set('quick_summary', value)} placeholder="Rear-end collision at a red light..." multilineField />
      </Card>

      <Card style={styles.card}>
        <Text style={styles.section}>Your Information</Text>
        <Field label="Name" value={form.owner_name} onChangeText={(value) => set('owner_name', value)} />
        <Field label="Phone" value={form.owner_phone} onChangeText={(value) => set('owner_phone', value)} keyboardType="phone-pad" />
        <Field label="Insurer" value={form.owner_insurer} onChangeText={(value) => set('owner_insurer', value)} />
        <Field label="Policy #" value={form.owner_policy_number} onChangeText={(value) => set('owner_policy_number', value)} />
        <Field label="VIN" value={form.owner_vin} onChangeText={(value) => set('owner_vin', value)} autoCapitalize="characters" />
        <Field label="Plate number" value={form.owner_plate_number} onChangeText={(value) => set('owner_plate_number', value)} autoCapitalize="characters" />
      </Card>

      <Card style={styles.card}>
        <Text style={styles.section}>Other Party</Text>
        <Field label="Name" value={form.other_name} onChangeText={(value) => set('other_name', value)} />
        <Field label="Phone" value={form.other_phone} onChangeText={(value) => set('other_phone', value)} keyboardType="phone-pad" />
        <Field label="Insurer" value={form.other_insurer} onChangeText={(value) => set('other_insurer', value)} />
        <Field label="Policy #" value={form.other_policy_number} onChangeText={(value) => set('other_policy_number', value)} />
        <Field label="VIN" value={form.other_vin} onChangeText={(value) => set('other_vin', value)} autoCapitalize="characters" />
        <Field label="Plate number" value={form.other_plate_number} onChangeText={(value) => set('other_plate_number', value)} autoCapitalize="characters" />
      </Card>

      <Card style={styles.card}>
        <Text style={styles.section}>Quick Facts</Text>
        <TriStateToggle label="Injuries reported?" value={form.injuries_reported} onChange={(value) => set('injuries_reported', value)} />
        <TriStateToggle label="Police called?" value={form.police_called} onChange={(value) => set('police_called', value)} />
        <TriStateToggle label="Vehicle drivable?" value={form.drivable} onChange={(value) => set('drivable', value)} />
        <TriStateToggle label="Tow requested?" value={form.tow_requested} onChange={(value) => set('tow_requested', value)} />
      </Card>

      <Card style={styles.card}>
        <Text style={styles.section}>Incident Photos</Text>
        <Text style={styles.muted}>
          Add photos by category so the report can separate vehicle damage from scene context.
        </Text>
        <View style={styles.photoGrid}>
          {PHOTO_CHANNELS.map((channel) => (
            <View key={channel.category} style={styles.photoChannel}>
              <View style={styles.photoChannelHeader}>
                <Text style={styles.photoTitle}>{channel.title}</Text>
                <Text style={styles.photoCount}>{photoCounts[channel.category]}</Text>
              </View>
              <Text style={styles.photoHint}>{channel.hint}</Text>
              <View style={styles.photoActions}>
                <Button
                  title="Camera"
                  loading={photoBusyKey === `${channel.category}:camera`}
                  disabled={photoBusyKey !== null}
                  onPress={() => uploadPhoto('camera', channel.category)}
                  style={styles.photoButton}
                />
                <Button
                  title="Gallery"
                  variant="secondary"
                  loading={photoBusyKey === `${channel.category}:gallery`}
                  disabled={photoBusyKey !== null}
                  onPress={() => uploadPhoto('gallery', channel.category)}
                  style={styles.photoButton}
                />
              </View>
            </View>
          ))}
        </View>
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
  muted: {
    color: colors.muted,
  },
  photoGrid: {
    gap: spacing.md,
  },
  photoChannel: {
    backgroundColor: colors.surfaceSoft,
    borderColor: colors.border,
    borderRadius: 18,
    borderWidth: 1,
    gap: spacing.sm,
    padding: spacing.md,
  },
  photoChannelHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  photoTitle: {
    color: colors.text,
    flex: 1,
    fontSize: 16,
    fontWeight: '900',
  },
  photoCount: {
    backgroundColor: '#dbeafe',
    borderRadius: 999,
    color: colors.blueDark,
    fontWeight: '900',
    minWidth: 30,
    overflow: 'hidden',
    paddingHorizontal: 10,
    paddingVertical: 4,
    textAlign: 'center',
  },
  photoHint: {
    color: colors.muted,
    lineHeight: 20,
  },
  photoActions: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
  photoButton: {
    flex: 1,
  },
});
