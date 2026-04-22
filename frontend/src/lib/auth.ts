const TOKEN_KEY = 'claimmate_token'
const CASES_KEY = 'claimmate_cases'

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

export function getCaseIds(): string[] {
  if (typeof window === 'undefined') return []
  try {
    return JSON.parse(localStorage.getItem(CASES_KEY) || '[]') as string[]
  } catch {
    return []
  }
}

export function addCaseId(caseId: string): void {
  if (typeof window === 'undefined') return
  const ids = getCaseIds()
  if (!ids.includes(caseId)) {
    localStorage.setItem(CASES_KEY, JSON.stringify([caseId, ...ids]))
  }
}

export function removeCaseId(caseId: string): void {
  if (typeof window === 'undefined') return
  const ids = getCaseIds().filter((id) => id !== caseId)
  localStorage.setItem(CASES_KEY, JSON.stringify(ids))
}
