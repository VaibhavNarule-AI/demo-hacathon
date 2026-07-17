// FastAPI's 422 validation-error body shape is {detail: [{type, loc, msg, input}, ...]},
// not a plain string like every other error path (401/403/404/409/400 all return
// {detail: "some string"}). Rendering `detail` directly as a JSX child works for the
// string case but crashes the whole tree the moment a 422 shows up (React refuses to
// render a plain object/array of objects as a child, and there's no error boundary
// here to contain it) -- this normalizes both shapes to a safe display string.
export function errorMessage(err, fallback) {
  const detail = err?.response?.data?.detail;
  if (!detail) return fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => (typeof d === "string" ? d : d.msg || JSON.stringify(d))).join("; ");
  }
  return fallback;
}
