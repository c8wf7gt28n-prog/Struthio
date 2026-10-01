// STRUTHIO HANDHELD · the arcade's canonical JSON (arcade/src/core/canonical.mjs),
// exposed as a string so a mismatching tick can be diffed line against line.
function canonicalOf(value) {
  if (value === null) return 'null';
  if (value === true) return 'true';
  if (value === false) return 'false';
  if (typeof value === 'number') return String(value);
  if (typeof value === 'string') return JSON.stringify(value);
  if (Array.isArray(value)) return '[' + value.map(canonicalOf).join(',') + ']';
  const keys = Object.keys(value).sort();
  return '{' + keys.map((k) => JSON.stringify(k) + ':' + canonicalOf(value[k])).join(',') + '}';
}
export { canonicalOf };
