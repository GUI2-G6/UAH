<template>
    <div>
        <Card variant="job" class="job-posting-card">
            <template #header>
                <div class="job-header-row">
                    <h3 class="job-title">{{ job.title }}</h3>
                </div>
            </template>
            <template #subtitle>
                <p class="job-company">{{ job.company || "Unknown company" }}</p>
            </template>

            <div class="job-card-body">
                <div class="job-meta-row">
                    <span
                        v-for="pill in visibleMetaPills"
                        :key="pill.key"
                        class="meta-pill"
                        :class="pill.classes"
                        :title="pill.title || null"
                    >
                        {{ pill.label }}
                    </span>
                </div>

                <div v-if="categoryPills.length" class="job-topic-row">
                    <span
                        v-for="pill in categoryPills"
                        :key="`category-${pill}`"
                        class="meta-pill subtle"
                    >
                        {{ pill }}
                    </span>
                </div>

                <p class="job-teaser">{{ teaserText }}</p>

                <div class="job-footer">
                    <div v-if="attributionText" class="job-attribution">
                        <a
                            v-if="attributionHref"
                            :href="attributionHref"
                            target="_blank"
                            rel="noopener noreferrer"
                            class="source-badge"
                            :class="{ required: attributionRequired }"
                        >
                            {{ attributionText }}
                        </a>
                        <span v-else class="source-badge" :class="{ required: attributionRequired }">
                            {{ attributionText }}
                        </span>
                    </div>

                    <div class="job-actions">
                        <button
                            type="button"
                            class="secondary save-action"
                            :class="{ active: isSaved }"
                            :disabled="savePending"
                            @click="toggleSave"
                        >
                            {{ saveButtonLabel }}
                        </button>
                        <button type="button" class="secondary" @click="markApplied">Mark applied</button>
                        <button type="button" class="secondary" @click="openDetails">Details</button>
                        <button type="button" class="primary" @click="apply">Apply Now</button>
                    </div>
                </div>
            </div>
        </Card>

        <div
            v-if="detailsOpen"
            class="job-modal-overlay"
            role="dialog"
            aria-modal="true"
            :aria-label="`Job details for ${job.title || 'role'}`"
            @click="closeDetails"
        >
            <div class="job-modal-dialog" v-draggable-modal="{ handle: '.job-modal-header' }" @click.stop>
                <div class="job-modal-header drag-handle">
                    <h2>{{ job.title }}</h2>
                    <button type="button" @click="closeDetails">Close</button>
                </div>

                <p class="job-modal-company">{{ job.company || "Unknown company" }}</p>

                <div class="job-modal-meta">
                    <span
                        v-for="item in detailMetaPills"
                        :key="item.key"
                        :class="item.classes"
                        :title="item.title || null"
                    >
                        {{ item.label }}
                    </span>
                    <span v-if="showDebugMeta && job.is_local_compatible_remote">Compatibility: {{ compatibilityLabel }}</span>
                    <span v-if="showDebugMeta && constraintExclusions.length">Exclusions: {{ constraintExclusions.join(", ") }}</span>
                    <span
                        v-if="showDebugMeta"
                        v-for="tz in constraintTimezones"
                        :key="`modal-tz-${tz}`"
                    >
                        Time zone: {{ tz }}
                    </span>
                </div>

                <div class="job-modal-body">
                    <p v-for="(paragraph, index) in detailParagraphs" :key="`paragraph-${index}`">{{ paragraph }}</p>
                </div>

                <div class="job-modal-actions">
                    <a v-if="applicationLink" :href="applicationLink" target="_blank" rel="noopener noreferrer">
                        <button type="button" class="primary">Open Application</button>
                    </a>
                    <button
                        type="button"
                        class="secondary save-action"
                        :class="{ active: isSaved }"
                        :disabled="savePending"
                        @click="toggleSave"
                    >
                        {{ detailSaveButtonLabel }}
                    </button>
                    <button type="button" class="secondary" @click="closeDetails">Close</button>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import Card from "./Card.vue";
import { formatJobLocationDisplay } from "../lib/jobLocationDisplay";
export default {
    name: "JobPosting",
    components: {
        Card
    },
    props: {
        job: Object,
        providerAttribution: {
            type: Object,
            default: null,
        },
        showDebugMeta: {
            type: Boolean,
            default: false,
        },
        boardMode: {
            type: String,
            default: "search",
        },
        isSaved: {
            type: Boolean,
            default: false,
        },
        savePending: {
            type: Boolean,
            default: false,
        },
    },
    emits: ["toggle-save", "mark-applied"],
    data() {
        return {
            detailsOpen: false
        }
    },
    computed: {
        normalizedDescriptionText() {
            const raw = (this.job?.contents || "").toString()
            if (!raw) return ""
            return this.formatDescriptionText(raw)
        },
        teaserText() {
            const shortDescription = (this.job?.short_description || "").toString().trim()
            if (shortDescription) {
                return this.truncateText(shortDescription, 185)
            }
            if (this.normalizedDescriptionText) {
                return this.truncateText(this.normalizedDescriptionText, 185)
            }
            return "Open details to review responsibilities, qualifications, and company context."
        },
        detailParagraphs() {
            if (!this.normalizedDescriptionText) {
                return ["This listing does not include a full description from the source. Use the apply link for complete role details."]
            }
            return this.normalizedDescriptionText
                .split(/\n{2,}/)
                .map((item) => item.trim())
                .filter(Boolean)
        },
        categoryPills() {
            const values = []
            const seen = new Set()
            for (const category of this.job?.categories || []) {
                const clean = (category || "").toString().trim()
                const key = clean.toLowerCase()
                if (!clean || seen.has(key)) continue
                seen.add(key)
                values.push(clean)
                if (values.length >= 2) break
            }
            return values
        },
        formattedPublicationDate() {
            const raw = this.job?.publication_date
            if (!raw) return ""
            const parsed = new Date(raw)
            if (Number.isNaN(parsed.getTime())) return ""
            return parsed.toLocaleDateString()
        },
        constraintTimezones() {
            const values = this.job?.location_constraints?.include_timezone_families || []
            return values.slice(0, 2)
        },
        constraintExclusions() {
            const values = this.job?.location_constraints?.exclude_location_terms || []
            return values.slice(0, 2)
        },
        compatibilityLabel() {
            if (!this.job?.is_local_compatible_remote) return "No local overlap"
            const reason = this.job?.local_compatibility_reason || "constraint-overlap"
            if (reason === "constraint-overlap") return "Constraint overlap"
            return reason
        },
        workSetupLabel() {
            if (this.job?.has_hybrid) return "Hybrid"
            if (this.job?.has_remote) return "Remote"
            return "On-site"
        },
        locationMetaPill() {
            const locationDisplay = formatJobLocationDisplay(this.job)
            return this.buildMetaPill("location", locationDisplay.label, {
                classes: ["location"],
                title: locationDisplay.title,
            })
        },
        visibleMetaPills() {
            const pills = [
                this.locationMetaPill,
                this.buildMetaPill("work-setup", this.workSetupLabel, { classes: ["accent"] }),
            ]

            if (this.formattedPublicationDate) {
                pills.push(this.buildMetaPill("posted", `Posted ${this.formattedPublicationDate}`, { classes: ["posted"] }))
            }

            const levelLabel = (this.job?.levels?.[0] || "").toString().trim()
            if (levelLabel) {
                pills.push(this.buildMetaPill("level", levelLabel))
            }

            if (this.showDebugMeta && this.job?.is_local_compatible_remote) {
                pills.push(this.buildMetaPill("location-overlap", "Location overlap", { classes: ["compatible"] }))
            }

            return pills
        },
        detailMetaPills() {
            const pills = [
                this.buildMetaPill("detail-location", this.locationMetaPill.label, {
                    classes: ["location"],
                    title: this.locationMetaPill.title,
                })
            ]
            if (this.job?.type) {
                pills.push(this.buildMetaPill("detail-type", `Type: ${this.job.type}`))
            }
            if (this.job?.levels?.length) {
                pills.push(this.buildMetaPill("detail-levels", `Level: ${this.job.levels.join(", ")}`))
            }
            if (this.job?.categories?.length) {
                pills.push(this.buildMetaPill("detail-categories", `Categories: ${this.job.categories.join(", ")}`))
            }
            if (this.job?.publication_date && this.formattedPublicationDate) {
                pills.push(this.buildMetaPill("detail-posted", `Posted: ${this.formattedPublicationDate}`))
            }
            if (this.attributionText) {
                pills.push(this.buildMetaPill("detail-source", `Source: ${this.attributionText}`))
            }
            return pills
        },
        applicationLink() {
            return this.job?.apply_link || this.job?.link || ""
        },
        attributionText() {
            const attribution = this.providerAttribution || {}
            const label = (attribution.label || "").toString().trim()
            if (label) return label
            const provider = (this.job?.provider || "").toString().trim()
            return provider ? `Source: ${provider}` : ""
        },
        attributionHref() {
            return (this.providerAttribution?.url || "").toString().trim()
        },
        attributionRequired() {
            return this.providerAttribution?.required === true
        },
        saveButtonLabel() {
            if (this.savePending) {
                return this.isSaved ? "Updating..." : "Saving..."
            }
            if (this.boardMode === "saved") {
                return "Remove saved"
            }
            return this.isSaved ? "Saved" : "Save job"
        },
        detailSaveButtonLabel() {
            if (this.boardMode === "saved") {
                return this.savePending ? "Removing..." : "Remove saved"
            }
            if (this.savePending) {
                return this.isSaved ? "Updating..." : "Saving..."
            }
            return this.isSaved ? "Saved" : "Save job"
        }
    },
    methods: {
        openDetails() {
            this.detailsOpen = true
        },
        closeDetails() {
            this.detailsOpen = false
        },
        buildMetaPill(key, label, options = {}) {
            return {
                key,
                label,
                title: options.title || "",
                classes: Array.isArray(options.classes) ? options.classes : [],
            }
        },
        truncateText(value, maxLength = 180) {
            const clean = (value || "").trim()
            if (!clean) return ""
            if (clean.length <= maxLength) return clean
            return `${clean.slice(0, maxLength - 1).trimEnd()}…`
        },
        formatDescriptionText(value) {
            const raw = (value || "").toString()
            if (!raw) return ""
            return raw
                .replace(/<style[\s\S]*?<\/style>/gi, " ")
                .replace(/<script[\s\S]*?<\/script>/gi, " ")
                .replace(/<li[^>]*>/gi, "\n• ")
                .replace(/<\/(li|ul|ol)>/gi, "\n")
                .replace(/<(br|br\/)\s*>/gi, "\n")
                .replace(/<\/(p|div|section|article|h[1-6])>/gi, "\n\n")
                .replace(/<[^>]+>/g, " ")
                .replace(/&nbsp;/g, " ")
                .replace(/&amp;/g, "&")
                .replace(/&quot;/g, '"')
                .replace(/&#39;/g, "'")
                .replace(/\r/g, "")
                .replace(/[ \t]+\n/g, "\n")
                .replace(/\n{3,}/g, "\n\n")
                .replace(/[ \t]{2,}/g, " ")
                .trim()
        },
        apply() {
            if (this.applicationLink) {
                window.open(this.applicationLink, "_blank", "noopener")
                return
            }
            this.openDetails()
        },
        toggleSave() {
            if (this.savePending) return
            this.$emit("toggle-save", this.job)
        },
        markApplied() {
            this.$emit("mark-applied", this.job)
        }
    }
}
</script>

<style scoped>
.job-posting-card {
    width: 100%;
    height: 100%;
}

:deep(.job-posting-card .ui-card__body) {
    display: flex;
    flex: 1;
}

.job-card-body {
    display: flex;
    flex-direction: column;
    flex: 1;
}

.job-title {
    margin: 0;
    color: #0f172a;
    font-size: 1.05rem;
    line-height: 1.35;
    flex: 1;
    min-width: 0;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

.job-header-row {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 10px;
}

.job-company {
    margin: 6px 0 2px;
    color: #334155;
}

.job-meta-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin: 10px 0 8px;
}

.job-topic-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin: 0 0 10px;
}

.meta-pill {
    border: 1px solid #d4d9e1;
    background: #f8fafc;
    color: #1f2937;
    border-radius: 999px;
    padding: 4px 10px;
    font-size: 0.82rem;
    display: inline-flex;
    align-items: center;
    max-width: 100%;
    min-width: 0;
}

.meta-pill.accent,
.job-modal-meta span.accent {
    border-color: var(--color-primary-600);
    color: var(--color-primary-600);
    background: color-mix(in srgb, var(--color-primary-600) 10%, white);
}

.meta-pill.posted {
    border-color: #cbd5e1;
    color: #334155;
    background: #f8fafc;
    white-space: nowrap;
}

.meta-pill.compatible,
.job-modal-meta span.compatible {
    border-color: #0c4a6e;
    color: #0c4a6e;
    background: rgba(14, 116, 144, 0.12);
}

.meta-pill.subtle {
    border-color: #d7e4df;
    color: #35534a;
    background: #f3fbf7;
}

.meta-pill.location {
    max-width: min(100%, 25rem);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.job-teaser {
    margin: 0;
    color: #334155;
    line-height: 1.45;
    font-size: 0.93rem;
    display: -webkit-box;
    -webkit-line-clamp: 4;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

.job-footer {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-top: auto;
    padding-top: 14px;
}

.job-attribution {
    font-size: 0.82rem;
}

.source-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    border-radius: 999px;
    border: 1px solid color-mix(in srgb, var(--color-primary-600) 24%, white);
    background: color-mix(in srgb, var(--color-primary-600) 10%, white);
    color: var(--color-primary-600);
    padding: 6px 11px;
    font-weight: 700;
    text-decoration: none;
}

.source-badge.required {
    background: rgba(13, 148, 136, 0.16);
    border-color: rgba(13, 148, 136, 0.26);
    color: #115e59;
}

.job-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}

.job-actions button,
.job-modal-header button,
.job-modal-actions button {
    border: 1px solid #c9cfda;
    border-radius: 8px;
    padding: 7px 12px;
    cursor: pointer;
    background: #f8fafc;
}

.job-actions .primary,
.job-modal-actions .primary {
    background: var(--color-primary-600);
    border-color: var(--color-primary-600);
    color: #ffffff;
}

.job-actions .secondary,
.job-modal-actions .secondary {
    background: #ffffff;
    color: #1f2937;
}

.job-actions .save-action.active,
.job-modal-actions .save-action.active {
    border-color: #0f766e;
    color: #0f766e;
    background: rgba(15, 118, 110, 0.08);
}

.job-modal-overlay {
    position: fixed;
    inset: 0;
    z-index: 1300;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(2, 6, 23, 0.45);
    padding: 14px;
}

.job-modal-dialog {
    width: min(760px, 96vw);
    max-height: min(84vh, 860px);
    background: #ffffff;
    border: 1px solid #dbe1e7;
    border-radius: 12px;
    box-shadow: 0 20px 38px rgba(15, 23, 42, 0.18);
    display: flex;
    flex-direction: column;
}

.job-modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding: 14px 16px 10px;
    border-bottom: 1px solid #e7eaee;
    cursor: grab;
}

.job-modal-header h2 {
    margin: 0;
    color: #0f172a;
    font-size: 1.08rem;
}

.job-modal-company {
    margin: 10px 16px 0;
    color: #334155;
    font-weight: 600;
}

.job-modal-meta {
    margin: 8px 16px 0;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}

.job-modal-meta span {
    border: 1px solid #d4d9e1;
    border-radius: 999px;
    padding: 4px 10px;
    font-size: 0.82rem;
    color: #334155;
    background: #f8fafc;
    display: inline-flex;
    align-items: center;
    min-width: 0;
    max-width: 100%;
}

.job-modal-meta span.location {
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.job-modal-body {
    margin: 12px 16px 0;
    padding: 12px;
    border: 1px solid #e7eaee;
    border-radius: 10px;
    background: #fafbfc;
    overflow-y: auto;
    max-height: 44vh;
}

.job-modal-body p {
    margin: 0 0 12px;
    color: #1f2937;
    line-height: 1.5;
    white-space: pre-wrap;
}

.job-modal-body p:last-child {
    margin-bottom: 0;
}

.job-modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    padding: 12px 16px 14px;
}

.job-modal-actions a {
    text-decoration: none;
}

@media (max-width: 700px) {
    .job-header-row {
        flex-direction: column;
        align-items: flex-start;
    }

    .job-actions {
        flex-direction: column;
    }

    .job-footer {
        gap: 10px;
    }

    .job-modal-dialog {
        width: 100%;
        max-height: 88vh;
    }
}

html[data-theme="dark"] .job-title {
    color: var(--color-text-primary);
}

html[data-theme="dark"] .job-company,
html[data-theme="dark"] .job-teaser {
    color: var(--color-text-secondary);
}

html[data-theme="dark"] .meta-pill,
html[data-theme="dark"] .job-modal-meta span {
    border-color: var(--border-color);
    background: var(--color-surface-muted);
    color: var(--color-text-primary);
}

html[data-theme="dark"] .meta-pill.posted {
    color: var(--color-text-secondary);
}

html[data-theme="dark"] .meta-pill.subtle {
    color: #c5f5e3;
    background: rgba(16, 185, 129, 0.14);
    border-color: rgba(16, 185, 129, 0.3);
}

html[data-theme="dark"] .meta-pill.accent,
html[data-theme="dark"] .job-modal-meta span.accent {
    background: rgba(59, 130, 246, 0.22);
    border-color: rgba(96, 165, 250, 0.58);
    color: #dbeafe;
}

html[data-theme="dark"] .meta-pill.compatible,
html[data-theme="dark"] .job-modal-meta span.compatible {
    background: rgba(14, 116, 144, 0.2);
    border-color: rgba(56, 189, 248, 0.52);
    color: #bae6fd;
}

html[data-theme="dark"] .job-actions button,
html[data-theme="dark"] .job-modal-header button,
html[data-theme="dark"] .job-modal-actions button {
    border-color: var(--border-color);
    background: var(--color-surface);
    color: var(--color-text-primary);
}

html[data-theme="dark"] .job-actions .secondary,
html[data-theme="dark"] .job-modal-actions .secondary {
    background: var(--color-surface);
    color: var(--color-text-primary);
}

html[data-theme="dark"] .job-modal-dialog {
    background: var(--color-surface);
    border-color: var(--border-color);
}

html[data-theme="dark"] .job-modal-header {
    border-bottom-color: var(--border-color);
}

html[data-theme="dark"] .job-modal-header h2,
html[data-theme="dark"] .job-modal-company {
    color: var(--color-text-primary);
}

html[data-theme="dark"] .job-modal-body {
    background: var(--color-surface-muted);
    border-color: var(--border-color);
}

html[data-theme="dark"] .job-modal-body p {
    color: var(--color-text-secondary);
}
</style>
