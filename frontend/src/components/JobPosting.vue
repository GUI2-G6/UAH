<template>
    <div>
        <Card>
            <template #header>
                <div class="job-header-row">
                    <h3 class="job-title">{{ job.title }}</h3>
                    <span v-if="formattedPublicationDate" class="meta-pill posted">Posted {{ formattedPublicationDate }}</span>
                </div>
            </template>
            <template #subtitle>
                <p class="job-company">{{ job.company || "Unknown company" }}</p>
            </template>

            <div class="job-meta-row">
                <span
                    v-for="pill in visibleMetaPills"
                    :key="pill"
                    class="meta-pill"
                    :class="{ accent: pill === workSetupLabel, compatible: pill === 'Location overlap' }"
                >
                    {{ pill }}
                </span>
            </div>

            <p class="job-teaser">{{ teaserText }}</p>

            <div class="job-actions">
                <button type="button" class="secondary" @click="openDetails">Details</button>
                <button type="button" class="primary" @click="apply">Apply Now</button>
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
                    <span>{{ job.location || "Unknown location" }}</span>
                    <span v-if="job.type">Type: {{ job.type }}</span>
                    <span v-if="job.levels && job.levels.length">Levels: {{ job.levels.join(", ") }}</span>
                    <span v-if="job.categories && job.categories.length">Categories: {{ job.categories.join(", ") }}</span>
                    <span v-if="job.tags && job.tags.length">Tags: {{ job.tags.join(", ") }}</span>
                    <span v-if="job.publication_date">Posted: {{ formattedPublicationDate }}</span>
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
                    <p>{{ detailsText }}</p>
                </div>

                <div class="job-modal-actions">
                    <a v-if="job.link" :href="job.link" target="_blank" rel="noopener noreferrer">
                        <button type="button" class="primary">Apply on The Muse</button>
                    </a>
                    <button type="button" class="secondary" @click="closeDetails">Close</button>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import Card from "./Card.vue";
export default {
    name: "JobPosting",
    components: {
        Card
    },
    props: {
        job: Object,
        showDebugMeta: {
            type: Boolean,
            default: false,
        }
    },
    data() {
        return {
            detailsOpen: false
        }
    },
    computed: {
        plainContents() {
            const raw = (this.job?.contents || "").toString()
            if (!raw) return ""
            return raw
                .replace(/<style[\s\S]*?<\/style>/gi, " ")
                .replace(/<script[\s\S]*?<\/script>/gi, " ")
                .replace(/<[^>]+>/g, " ")
                .replace(/&nbsp;/g, " ")
                .replace(/&amp;/g, "&")
                .replace(/&quot;/g, '"')
                .replace(/&#39;/g, "'")
                .replace(/\s+/g, " ")
                .trim()
        },
        teaserText() {
            if (this.plainContents) {
                return `${this.plainContents.slice(0, 180)}${this.plainContents.length > 180 ? "..." : ""}`
            }
            return "Open details to review responsibilities, qualifications, and company context."
        },
        detailsText() {
            if (this.plainContents) return this.plainContents
            return "This listing does not include a full description from the source. Use the apply link for complete role details."
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
        visibleMetaPills() {
            const pills = [
                this.job?.location || "Unknown location",
                this.workSetupLabel,
            ]

            if (this.showDebugMeta && this.job?.is_local_compatible_remote) {
                pills.push("Location overlap")
            }

            return pills
        }
    },
    methods: {
        openDetails() {
            this.detailsOpen = true
        },
        closeDetails() {
            this.detailsOpen = false
        },
        apply() {
            if (this.job?.link) {
                window.open(this.job.link, "_blank", "noopener")
                return
            }
            this.openDetails()
        }
    }
}
</script>

<style scoped>
.job-title {
    margin: 0;
    color: #0f172a;
    font-size: 1.05rem;
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

.meta-pill {
    border: 1px solid #d4d9e1;
    background: #f8fafc;
    color: #1f2937;
    border-radius: 999px;
    padding: 4px 10px;
    font-size: 0.82rem;
}

.meta-pill.accent {
    border-color: #0f766e;
    color: #0f766e;
    background: rgba(15, 118, 110, 0.08);
}

.meta-pill.posted {
    border-color: #cbd5e1;
    color: #334155;
    background: #f8fafc;
    white-space: nowrap;
}

.meta-pill.compatible {
    border-color: #0c4a6e;
    color: #0c4a6e;
    background: rgba(14, 116, 144, 0.12);
}

.meta-pill.info {
    border-color: #4b5563;
    color: #374151;
    background: #f1f5f9;
}

.meta-pill.trust {
    border-color: #334155;
    color: #334155;
    background: #f1f5f9;
}

.job-teaser {
    margin: 0;
    color: #334155;
    line-height: 1.45;
    font-size: 0.93rem;
}

.job-actions {
    display: flex;
    gap: 8px;
    margin-top: 12px;
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
    background: #0f766e;
    border-color: #0f766e;
    color: #ffffff;
}

.job-actions .secondary,
.job-modal-actions .secondary {
    background: #ffffff;
    color: #1f2937;
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
    margin: 0;
    color: #1f2937;
    line-height: 1.5;
    white-space: pre-wrap;
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

    .job-modal-dialog {
        width: 100%;
        max-height: 88vh;
    }
}
</style>
