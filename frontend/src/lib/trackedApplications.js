/**
 * Tracked-application rows from /api/applications/tracked can include multiple
 * source_type values. The Applications inbox UI is Gmail-only for now; job-board
 * saved jobs use source_type "saved_job" and belong on the Job Board.
 */
export function filterGmailTrackedRows(rows) {
  if (!Array.isArray(rows)) return []
  return rows.filter((row) => String(row?.source_type || "").toLowerCase() === "gmail")
}
