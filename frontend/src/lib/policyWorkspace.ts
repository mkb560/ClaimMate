export const POLICY_WORKSPACE_PREFIX = 'policy-qa-'

export function getPolicyWorkspaceCaseId(userId: string): string {
  const safeUserId = userId.replace(/[^A-Za-z0-9_-]/g, '-')
  return `${POLICY_WORKSPACE_PREFIX}${safeUserId}`.slice(0, 64)
}

export function isPolicyWorkspaceCaseId(caseId: string): boolean {
  return caseId.startsWith(POLICY_WORKSPACE_PREFIX)
}
