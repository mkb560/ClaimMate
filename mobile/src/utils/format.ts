export function formatDateTime(value: string | null | undefined): string {
  if (!value) return 'Not provided';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export function formatBool(value: boolean | null | undefined): string {
  if (value === true) return 'Yes';
  if (value === false) return 'No';
  return 'Unknown';
}

export function textValue(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

function pad(value: number): string {
  return String(value).padStart(2, '0');
}

export function dateToDateTimeLocal(date: Date): string {
  return [
    date.getFullYear(),
    pad(date.getMonth() + 1),
    pad(date.getDate()),
  ].join('-') + `T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function dateTimeLocalToDate(value: string): Date | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/.exec(value);
  if (match) {
    const [, year, month, day, hour, minute] = match;
    const date = new Date(
      Number(year),
      Number(month) - 1,
      Number(day),
      Number(hour),
      Number(minute)
    );
    return Number.isNaN(date.getTime()) ? null : date;
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatDateTimeLocal(value: string): string {
  const date = dateTimeLocalToDate(value);
  if (!date) return '';
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

export function toDateTimeLocal(value: unknown): string {
  if (!value || typeof value !== 'string') return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return dateToDateTimeLocal(date);
}

export function dateTimeLocalToIso(value: string): string | null {
  if (!value) return null;
  const date = dateTimeLocalToDate(value);
  if (!date) return null;
  return date.toISOString();
}
