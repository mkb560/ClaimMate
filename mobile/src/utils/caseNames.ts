import * as SecureStore from 'expo-secure-store';

function caseNameKey(caseId: string): string {
  return `claimmate_mobile_case_name_${caseId}`;
}

export function defaultCaseName(caseId: string): string {
  const suffix = caseId.replace(/^case-/, '').slice(0, 8).toUpperCase();
  return `Accident case ${suffix}`;
}

export async function getCaseName(caseId: string): Promise<string | null> {
  return SecureStore.getItemAsync(caseNameKey(caseId));
}

export async function setCaseName(caseId: string, name: string): Promise<void> {
  await SecureStore.setItemAsync(caseNameKey(caseId), name.trim());
}

export async function removeCaseName(caseId: string): Promise<void> {
  await SecureStore.deleteItemAsync(caseNameKey(caseId));
}
