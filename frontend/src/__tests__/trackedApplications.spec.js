import { describe, expect, it } from "vitest"
import { filterGmailTrackedRows } from "@/lib/trackedApplications.js"

describe("filterGmailTrackedRows", () => {
  it("keeps gmail rows only", () => {
    const rows = [
      { id: 1, source_type: "gmail", source_ref: "a" },
      { id: 2, source_type: "saved_job", source_ref: "b" },
      { id: 3, source_type: "GMAIL", source_ref: "c" },
    ]
    expect(filterGmailTrackedRows(rows)).toEqual([
      { id: 1, source_type: "gmail", source_ref: "a" },
      { id: 3, source_type: "GMAIL", source_ref: "c" },
    ])
  })

  it("handles non-arrays", () => {
    expect(filterGmailTrackedRows(null)).toEqual([])
    expect(filterGmailTrackedRows(undefined)).toEqual([])
  })
})
