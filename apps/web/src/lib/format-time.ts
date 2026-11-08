const dateFormatter = new Intl.DateTimeFormat("en-GB", {
  day: "2-digit",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: false,
  timeZone: "UTC",
  timeZoneName: "short",
});

export function formatUtcTimestamp(value: string): string {
  return dateFormatter.format(new Date(value));
}

const windowFormatter = new Intl.DateTimeFormat("en-GB", {
  dateStyle: "medium",
  timeStyle: "short",
  hourCycle: "h23",
  timeZone: "UTC",
});

export function formatUtcWindow(start: string, end: string): string {
  return `${windowFormatter.formatRange(new Date(start), new Date(end))} UTC`;
}
