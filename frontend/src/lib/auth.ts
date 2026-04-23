const TOKEN_KEY = 'claimmate_token'

export function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  if (typeof window === 'undefined') return
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

function caseNameKey(caseId: string): string {
  return `claimmate_case_name_${caseId}`
}

export function getCaseName(caseId: string): string {
  if (typeof window === 'undefined') return caseId
  return localStorage.getItem(caseNameKey(caseId)) || caseId
}

export function setCaseName(caseId: string, name: string): void {
  if (typeof window === 'undefined') return
  localStorage.setItem(caseNameKey(caseId), name)
}

export function removeCaseName(caseId: string): void {
  if (typeof window === 'undefined') return
  localStorage.removeItem(caseNameKey(caseId))
}
