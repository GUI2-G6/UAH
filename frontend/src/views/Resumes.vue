<template>
    <div class="page">

        <!-- ── Greeting ──────────────────────────────────────── -->
        <div class="greeting">
            <div class="greeting-left">
                <h1>Resumes</h1>
                <p>Manage UAH resumes and application information</p>
            </div>
            <button v-if="activeTab === 'imported'" class="btn-primary" @click="openUploadModal">
                + Import New Resume
            </button>
            <button v-if="activeTab === 'applicant'" class="btn-primary" :disabled="working" @click="saveApplicantInfo">
                {{ working ? 'Saving…' : 'Save All' }}
            </button>
        </div>

        <!-- ── Tab nav ───────────────────────────────────────── -->
        <nav class="resume-nav">
            <button :class="{ active: activeTab === 'imported' }" @click="activeTab = 'imported'">
                Imported Resumes
            </button>
            <button :class="{ active: activeTab === 'applicant' }" @click="activeTab = 'applicant'">
                Applicant Information
            </button>
            <button :class="{ active: activeTab === 'jobinfo' }" @click="activeTab = 'jobinfo'">
                Job Application Info
            </button>
        </nav>

        <!-- ════════════════════════════════════════════════════
             TAB 1 — Imported Resumes
        ═════════════════════════════════════════════════════ -->
        <div v-if="activeTab === 'imported'" class="dashboard">

            <div ref="inlineImportSection" class="appinfo-card inline-import-card">
                <h3>Import Resume</h3>
                <p class="subtitle import-subtitle">Upload a UAH resume PDF and follow the staged flow: Select file, Confirm settings, Parse, then review readiness.</p>

                <div class="upload-stage-row" v-if="activeTab === 'imported'">
                    <span :class="['stage-pill', uploadStep === 'select' ? 'active' : '']">1. Select</span>
                    <span :class="['stage-pill', uploadStep === 'confirm' ? 'active' : '']">2. Confirm</span>
                    <span :class="['stage-pill', uploadStep === 'parsing' ? 'active' : '']">3. Parsing</span>
                    <span class="stage-pill">4. Review Readiness</span>
                </div>

                <div
                    v-if="uploadStep === 'select'"
                    class="drop-zone"
                    :class="{ 'drag-over': isDragOver }"
                    @click="triggerFileInput"
                    @dragover.prevent="isDragOver = true"
                    @dragleave="isDragOver = false"
                    @drop.prevent="onFileDrop"
                >
                    <div class="drop-icon" aria-hidden="true">PDF</div>
                    <p>Upload resume PDF</p>
                    <p class="drop-hint">Drag and drop a PDF file here, or click to browse</p>
                    <button class="btn-primary" @click.stop="triggerFileInput">Choose PDF File</button>
                    <p class="drop-hint">PDF files only, max 5MB</p>
                </div>
                <input
                    ref="fileInput"
                    type="file"
                    accept=".pdf,application/pdf"
                    style="display:none"
                    @change="onFileChange"
                />

                <template v-if="uploadStep === 'confirm'">
                    <div class="file-preview-row file-preview-top-gap">
                        <div class="pdf-icon">PDF</div>
                        <div class="file-info">
                            <p class="file-name">{{ pendingFile.name }}</p>
                            <p class="file-size">{{ formatBytes(pendingFile.size) }}</p>
                        </div>
                        <button class="clear-btn" @click="clearFile" title="Remove file">&#x2715;</button>
                    </div>

                    <div class="pipeline-guardrails import-options-spaced">
                        <h4>Pipeline Guarantees</h4>
                        <p class="pipeline-ordering-note">UAH parser order (highest reliability/accuracy to lowest): Local AI, Cloud AI, Rules-based.</p>
                        <div class="import-option-row">
                            <div class="check-circle" aria-hidden="true"></div>
                            <div class="option-text">
                                <strong>Local AI uses isolated local infrastructure</strong>
                                <span>Local OCR plus local LLM processing, with method-specific local queue metrics.</span>
                            </div>
                        </div>
                        <div class="import-option-row">
                            <div class="check-circle" aria-hidden="true"></div>
                            <div class="option-text">
                                <strong>Cloud AI uses web ZAI OCR and GLM-4.7-Flash</strong>
                                <span>Cloud throughput is concurrency-limited; provider-side waiting queue is not exposed.</span>
                            </div>
                        </div>
                        <div class="import-option-row">
                            <div class="check-circle" aria-hidden="true"></div>
                            <div class="option-text">
                                <strong>Rules-based parsing is deterministic and isolated</strong>
                                <span>Rules mode reads embedded PDF text only and does not use OCR/model queues.</span>
                            </div>
                        </div>
                    </div>

                    <div class="parse-method-group">
                        <div class="parse-method-header">
                            <label class="parse-method-label">Parse Pipeline</label>
                            <button class="btn-secondary btn-compact" type="button" @click="showPipelineDetails = true">View Details</button>
                        </div>
                        <div class="method-toggle method-toggle-3">
                            <button :class="{ active: parseMethod === 'local' }" @click="parseMethod = 'local'">Local AI</button>
                            <button :class="{ active: parseMethod === 'cloud' }" @click="parseMethod = 'cloud'">Cloud AI (ZAI)</button>
                            <button :class="{ active: parseMethod === 'rules' }" @click="parseMethod = 'rules'">Rules-based</button>
                        </div>
                        <p class="parse-method-summary">{{ selectedParseMethodDescription }}</p>
                    </div>

                    <div class="modal-actions inline-actions">
                        <button class="btn-secondary" @click="clearFile" :disabled="uploading">Choose Different File</button>
                        <button class="btn-primary" @click="doUpload" :disabled="uploading">
                            <span v-if="uploading">
                                <span class="spinner spinner-inline"></span>
                                Importing...
                            </span>
                            <span v-else>Import Resume</span>
                        </button>
                    </div>
                </template>

                <!-- Stage 3: Parsing progress -->
                <template v-if="uploadStep === 'parsing'">
                    <div class="parse-progress-card">
                        <div class="parse-progress-header">
                            <div class="spinner spinner-inline"></div>
                            <span class="parse-stage-label">{{ parseStageLabel || 'Starting…' }}</span>
                        </div>
                        <div class="parse-progress-bar-track">
                            <div
                                class="parse-progress-bar-fill"
                                :style="{ width: parseProgressPercent + '%' }"
                            ></div>
                        </div>
                        <p class="parse-progress-hint">{{ parseProgressHint }}</p>
                        <p class="parse-progress-hint" v-if="parseAttemptLabel || parseElapsedLabel">
                            <span v-if="parseAttemptLabel">{{ parseAttemptLabel }}</span>
                            <span v-if="parseAttemptLabel && parseElapsedLabel"> · </span>
                            <span v-if="parseElapsedLabel">{{ parseElapsedLabel }}</span>
                            <span v-if="parseQueuePosition && parseQueueTotal"> · Queue {{ parseQueuePosition }}/{{ parseQueueTotal }}</span>
                        </p>
                        <p class="parse-progress-hint" v-if="parseErrorCode">Code: {{ parseErrorCode }}</p>
                        <button class="btn-secondary" @click="cancelParse" :disabled="parseStatus === 'cancelled'">
                            Cancel
                        </button>
                    </div>
                </template>

                <div v-if="uploadError" class="upload-error">{{ uploadError }}</div>
            </div>

            <!-- Stats row -->
            <div class="stats-row">
                <div class="stat-card">
                    <div class="stat-label">Total Resumes</div>
                    <div class="stat-value">{{ resumes.length }}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Portal Ready</div>
                    <div class="stat-value">{{ portalReadyCount }}/{{ resumes.length }}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Latest Upload</div>
                    <div class="stat-value stat-value-small">{{ latestUploadDate }}</div>
                </div>
            </div>

            <div class="queue-panel-card">
                <div class="queue-panel-header">
                    <div>
                        <h4>Parse Queue</h4>
                        <p>Track UAH queue load, method-level activity, and current parse position in real time.</p>
                    </div>
                    <div class="queue-scope-toggle">
                        <button :class="{ active: queueScope === 'user' }" @click="setQueueScope('user')">My Queue</button>
                        <button
                            v-if="canViewGlobalQueue"
                            :class="{ active: queueScope === 'global' }"
                            @click="setQueueScope('global')"
                        >Global Queue</button>
                    </div>
                </div>

                <div v-if="queueLoading && !queueStatus" class="loading-row queue-loading-row">
                    <div class="spinner"></div> Loading queue status...
                </div>
                <div v-else-if="queueError" class="upload-error">{{ queueError }}</div>
                <template v-else-if="queueStatus">
                    <div class="queue-metrics-grid">
                        <div class="queue-metric-card">
                            <span class="queue-metric-label">Your Position</span>
                            <span class="queue-metric-value">
                                {{ queueStatus.current_user?.active_job_position ?? '—' }}
                                <small v-if="queueStatus.current_user?.active_job_total">/ {{ queueStatus.current_user.active_job_total }}</small>
                            </span>
                            <span class="queue-metric-sub">
                                {{ parseMethodTagLabel(queueStatus.current_user?.focus_method || parseMethod || 'local') }} pipeline
                            </span>
                        </div>
                        <div class="queue-metric-card">
                            <span class="queue-metric-label">System Load</span>
                            <span class="queue-metric-value">{{ queueStatus.global_metrics?.load_total ?? 0 }}</span>
                            <span class="queue-metric-sub">
                                Active {{ queueStatus.global_metrics?.active_total ?? 0 }} · Queued {{ queueStatus.queue_depth_total ?? queueStatus.queue_depth ?? 0 }}
                            </span>
                        </div>
                        <div class="queue-metric-card">
                            <span class="queue-metric-label">Queues By Method</span>
                            <span class="queue-metric-value">{{ queueStatus.queue_depth_total ?? queueStatus.queue_depth ?? 0 }}</span>
                            <span class="queue-metric-sub queue-method-inline">
                                <span>Local {{ queueStatus.queue_depth_by_method?.local ?? 0 }}</span>
                                <span>Cloud {{ queueStatus.queue_depth_by_method?.cloud ?? 0 }}</span>
                                <span>Rules {{ queueStatus.queue_depth_by_method?.rules ?? 0 }}</span>
                            </span>
                        </div>
                    </div>

                    <p class="queue-stage-text" v-if="queueStatus.current_user?.latest_active_job_status">
                        Active job: {{ parseMethodTagLabel(queueStatus.current_user?.latest_active_job_method) }} · {{ queueStatus.current_user?.latest_active_job_status }}
                    </p>

                    <details class="queue-details">
                        <summary>Queue details</summary>
                        <div class="queue-details-body">
                            <p class="queue-details-line">Worker mode: {{ queueStatus.worker_status?.mode || 'unknown' }}</p>
                            <p class="queue-details-line" v-if="queueStatus.local_queue_note">{{ queueStatus.local_queue_note }}</p>
                            <p class="queue-details-line" v-if="queueStatus.cloud_behavior?.description">{{ queueStatus.cloud_behavior.description }}</p>
                        </div>
                    </details>

                    <details v-if="queueScope === 'global' && queueStatus.global_queue" class="queue-details queue-details-global">
                        <summary>Global active queue ({{ queueStatus.global_queue.active_count }})</summary>
                        <div class="queue-global-list">
                            <div class="queue-global-entry" v-for="entry in queueStatus.global_queue.entries" :key="entry.job_id">
                                <span class="entry-position">#{{ entry.position }}</span>
                                <span class="entry-method">{{ parseMethodTagLabel(entry.method) }}</span>
                                <span class="entry-status">{{ entry.status }}</span>
                            </div>
                        </div>
                    </details>
                </template>
            </div>

            <!-- Loading -->
            <div v-if="resumesLoading" class="loading-row">
                <div class="spinner"></div> Loading resumes…
            </div>

            <!-- Error -->
            <div v-else-if="resumesError" class="upload-error">{{ resumesError }}</div>

            <!-- List -->
            <div v-else-if="resumes.length" class="resume-list-card">
                <div v-for="r in resumes" :key="r.id" class="resume-list-item">
                    <div class="pdf-icon">PDF</div>
                    <div class="resume-meta">
                        <p class="resume-name">{{ r.file_name }}</p>
                        <p class="resume-date">Uploaded {{ formatDate(r.created_at) }}</p>
                    </div>
                    <div class="resume-badges">
                        <span :class="['badge', badgeClass(r)]">{{ badgeText(r) }}</span>
                        <span v-if="r.parse_method" :class="['badge', 'parse-method-badge', parseMethodToneClass(r.parse_method)]">{{ parseMethodTagLabel(r.parse_method) }}</span>
                    </div>
                    <div class="resume-actions">
                        <button title="View parsed data" @click="viewResume(r.id)">View</button>
                        <button
                            title="Delete resume"
                            class="delete-btn"
                            :class="{ 'confirm-delete': deletingId === r.id }"
                            @click="handleDelete(r.id)"
                        >
                            {{ deletingId === r.id ? 'Confirm Delete' : 'Delete' }}
                        </button>
                    </div>
                </div>
            </div>

            <!-- Empty -->
            <div v-else class="resume-list-card">
                <div class="empty-state">
                    <p>No resumes yet. Import a PDF to get started.</p>
                </div>
            </div>

        </div><!-- /tab imported -->


        <!-- ════════════════════════════════════════════════════
             TAB 2 — Applicant Information
        ═════════════════════════════════════════════════════ -->
        <div v-if="activeTab === 'applicant'" class="dashboard">

            <!-- Profile switcher -->
            <div v-if="profiles.length > 0" class="profile-switcher">
                <div class="profile-switcher-row">
                    <label class="profile-switcher-label">Active Profile:</label>
                    <select class="profile-select" :value="activeProfileId" @change="switchProfile(Number($event.target.value))">
                        <option v-for="p in profiles" :key="p.id" :value="p.id">
                            {{ p.name }}{{ p.is_active ? ' (active)' : '' }}
                        </option>
                    </select>
                    <button class="btn-secondary btn-compact" @click="showNewProfileInput = !showNewProfileInput" title="New profile">+</button>
                    <button
                        v-if="profiles.length > 1 && !isDefaultProfile(activeProfileId)"
                        class="btn-secondary btn-compact delete-profile-btn"
                        @click="deleteProfile(activeProfileId)"
                        title="Delete current profile"
                    >Delete</button>
                </div>
                <div v-if="showNewProfileInput" class="new-profile-row">
                    <input
                        v-model="newProfileName"
                        type="text"
                        placeholder="New profile name…"
                        class="new-profile-input"
                        @keyup.enter="createNewProfile"
                    />
                    <button class="btn-primary btn-compact" @click="createNewProfile" :disabled="!newProfileName.trim()">Create</button>
                    <button class="btn-secondary btn-compact" @click="showNewProfileInput = false">Cancel</button>
                </div>
            </div>

            <!-- Save feedback -->
            <div v-if="saveStatus.message" :class="['save-feedback', saveStatus.type === 'success' ? 'is-success' : 'is-error']">
                {{ saveStatus.message }}
            </div>

            <!-- Personal Information -->
            <div class="appinfo-card">
                <h3>Personal Information</h3>
                <div class="appinfo-grid">
                    <div class="field-group">
                        <label>First Name</label>
                        <input type="text" v-model="firstName" placeholder="John">
                    </div>
                    <div class="field-group">
                        <label>Last Name</label>
                        <input type="text" v-model="lastName" placeholder="Doe">
                    </div>
                    <div class="field-group">
                        <label>Email</label>
                        <input type="email" v-model="appEmail" placeholder="john.doe@email.com">
                    </div>
                    <div class="field-group">
                        <label>Phone</label>
                        <input type="text" v-model="phone" placeholder="(555) 123-4567">
                    </div>
                    <div class="field-group">
                        <label>LinkedIn URL</label>
                        <input type="text" v-model="linkedin" placeholder="linkedin.com/in/johndoe">
                    </div>
                    <div class="field-group">
                        <label>Portfolio/Website</label>
                        <input type="text" v-model="portfolio" placeholder="johndoe.com">
                    </div>
                </div>
            </div>

            <!-- Address -->
            <div class="appinfo-card">
                <h3>Address</h3>
                <div class="field-group field-group-spaced">
                    <label>Street Address</label>
                    <input type="text" v-model="streetAddress" placeholder="123 Main Street">
                </div>
                <div class="appinfo-3col">
                    <div class="field-group">
                        <label>City</label>
                        <input type="text" v-model="city" placeholder="San Francisco">
                    </div>
                    <div class="field-group">
                        <label>State</label>
                        <input type="text" v-model="appState" placeholder="CA">
                    </div>
                    <div class="field-group">
                        <label>ZIP Code</label>
                        <input type="text" v-model="zip" placeholder="94105">
                    </div>
                </div>
            </div>

            <!-- Professional Summary -->
            <div class="appinfo-card">
                <h3>Professional Summary</h3>
                <div class="field-group">
                    <label>Summary</label>
                    <textarea v-model="summary" class="textarea-summary" placeholder="Brief professional summary highlighting your key skills and experience…"></textarea>
                </div>
            </div>

            <!-- Work Authorization -->
            <div class="appinfo-card">
                <h3>Work Authorization</h3>
                <div class="appinfo-grid">
                    <div class="field-group">
                        <label>Authorization Status</label>
                        <select v-model="workAuth">
                            <option value="">Select…</option>
                            <option>US Citizen</option>
                            <option>Green Card</option>
                            <option>H1-B</option>
                            <option>OPT/CPT</option>
                            <option>Other</option>
                            <option>Require Sponsorship</option>
                        </select>
                    </div>
                    <div class="field-group">
                        <label>Requires Sponsorship?</label>
                        <select v-model="requiresSponsorship">
                            <option value="">Select…</option>
                            <option>Yes</option>
                            <option>No</option>
                            <option>In the future</option>
                        </select>
                    </div>
                </div>
            </div>

            <!-- Education -->
            <div class="appinfo-card">
                <h3>Education</h3>
                <div class="appinfo-grid">
                    <div class="field-group">
                        <label>Degree</label>
                        <input type="text" v-model="degree" placeholder="Bachelor of Science">
                    </div>
                    <div class="field-group">
                        <label>Major / Field of Study</label>
                        <input type="text" v-model="major" placeholder="Computer Science">
                    </div>
                    <div class="field-group appinfo-full">
                        <label>University</label>
                        <input type="text" v-model="university" placeholder="University of Alabama in Huntsville">
                    </div>
                    <div class="field-group">
                        <label>Graduation Year</label>
                        <input type="text" v-model="gradYear" placeholder="2026">
                    </div>
                    <div class="field-group">
                        <label>GPA (optional)</label>
                        <input type="text" v-model="gpa" placeholder="3.8">
                    </div>
                </div>
            </div>

            <!-- Current Experience -->
            <div class="appinfo-card">
                <h3>Current Experience</h3>
                <div class="appinfo-grid">
                    <div class="field-group">
                        <label>Years of Experience</label>
                        <input type="text" v-model="yearsExperience" placeholder="2">
                    </div>
                    <div class="field-group">
                        <label>Current / Most Recent Job Title</label>
                        <input type="text" v-model="jobTitle" placeholder="Software Engineer Intern">
                    </div>
                </div>
            </div>

            <div class="appinfo-card">
                <h3>Skills and Certifications</h3>
                <div class="field-group field-group-spaced">
                    <label>Skills (comma-separated)</label>
                    <textarea v-model="skillsText" placeholder="Python, SQL, FastAPI, Vue.js, Docker"></textarea>
                </div>
                <div class="field-group field-group-spaced">
                    <label>Certifications and Licenses</label>
                    <textarea v-model="certificationsText" placeholder="AWS Certified Cloud Practitioner - Amazon - 2025"></textarea>
                </div>
                <div class="field-group">
                    <label>Professional Links</label>
                    <textarea v-model="professionalLinksText" placeholder="LinkedIn: https://...&#10;GitHub: https://...&#10;Portfolio: https://..."></textarea>
                </div>
            </div>

            <div class="appinfo-card">
                <h3>Education History (Additional Entries)</h3>
                <div class="field-group">
                    <label>Education History</label>
                    <textarea
                        class="textarea-tall"
                        v-model="educationHistoryText"
                        placeholder="School | Degree | Field | Start Date | End Date&#10;Example University | B.S. | Computer Science | August 2022 | May 2026"
                    ></textarea>
                </div>
            </div>

            <div class="appinfo-card">
                <h3>Employment History (Additional Entries)</h3>
                <div class="field-group">
                    <label>Employment History</label>
                    <textarea
                        class="textarea-tall"
                        v-model="employmentHistoryText"
                        placeholder="Company | Title | Location | Start Date | End Date&#10;Tech Corp | Software Engineer Intern | Boston, MA | June 2024 | August 2024"
                    ></textarea>
                </div>
            </div>

            <div class="appinfo-card">
                <h3>Demographics (Optional)</h3>
                <div class="appinfo-grid">
                    <div class="field-group">
                        <label>Gender Identity (Optional)</label>
                        <select v-model="demographicGender">
                            <option value="">Prefer not to answer</option>
                            <option>Female</option>
                            <option>Male</option>
                            <option>Non-binary</option>
                            <option>Another identity</option>
                        </select>
                    </div>
                    <div class="field-group">
                        <label>Ethnicity / Race (Optional)</label>
                        <select v-model="demographicEthnicity">
                            <option value="">Prefer not to answer</option>
                            <option>American Indian or Alaska Native</option>
                            <option>Asian</option>
                            <option>Black or African American</option>
                            <option>Hispanic or Latino</option>
                            <option>Native Hawaiian or Other Pacific Islander</option>
                            <option>White</option>
                            <option>Two or More Races</option>
                        </select>
                    </div>
                </div>
            </div>

        </div><!-- /tab applicant -->


        <!-- ════════════════════════════════════════════════════
             TAB 3 — Job Application Info (EEO)
        ═════════════════════════════════════════════════════ -->
        <div v-if="activeTab === 'jobinfo'" class="dashboard">

            <div class="eeo-banner">
                Required: Federal and state laws require employers to collect this information for equal employment
                opportunity reporting. Your responses are confidential and will not affect your application.
            </div>

            <!-- Veteran Status -->
            <div class="eeo-card">
                <div class="eeo-header-row">
                    <div>
                        <h3>Veteran Status <span class="required-mark">*</span></h3>
                        <p class="eeo-subtitle">Protected veteran status under VEVRAA</p>
                    </div>
                </div>
                <div
                    v-for="opt in veteranOptions"
                    :key="opt"
                    class="option-row"
                    :class="{ selected: veteranStatus === opt }"
                    @click="veteranStatus = opt"
                >
                    <div class="radio-dot"></div>
                    {{ opt }}
                </div>
                <p class="eeo-footnote">
                    Protected veterans include: Disabled veterans, recently separated veterans, active duty wartime
                    or campaign badge veterans, and Armed Forces service medal veterans.
                </p>
            </div>

            <!-- Disability Status -->
            <div class="eeo-card">
                <div class="eeo-header-row">
                    <div>
                        <h3>Disability Status <span class="required-mark">*</span></h3>
                        <p class="eeo-subtitle">Voluntary self-identification under Section 503</p>
                    </div>
                </div>
                <div
                    v-for="opt in disabilityOptions"
                    :key="opt"
                    class="option-row"
                    :class="{ selected: disabilityStatus === opt }"
                    @click="disabilityStatus = opt"
                >
                    <div class="radio-dot"></div>
                    {{ opt }}
                </div>
            </div>

            <!-- California Resident -->
            <div class="eeo-card">
                <div class="eeo-header-row">
                    <div>
                        <h3>California Resident <span class="required-mark">*</span></h3>
                        <p class="eeo-subtitle">Required for CCPA compliance</p>
                    </div>
                </div>
                <div
                    v-for="opt in californiaOptions"
                    :key="opt"
                    class="option-row"
                    :class="{ selected: californiaResident === opt }"
                    @click="californiaResident = opt"
                >
                    <div class="radio-dot"></div>
                    {{ opt }}
                </div>
            </div>

            <!-- Save -->
            <div class="jobinfo-save-row">
                <button class="btn-primary" @click="saveJobInfo">Save Information</button>
                <span v-if="jobInfoError" class="save-error">{{ jobInfoError }}</span>
                <span v-if="jobInfoSuccess" class="save-success">{{ jobInfoSuccess }}</span>
            </div>

        </div><!-- /tab jobinfo -->


        <!-- ════════════════════════════════════════════════════
             VIEW RESUME MODAL
        ═════════════════════════════════════════════════════ -->
        <div v-if="showViewModal" class="modal-overlay" @click.self="closeViewModal">
            <div class="modal-box view-modal-box" v-draggable-modal="{ handle: '.modal-drag-header' }">
                <div class="modal-drag-header drag-handle view-modal-header-row">
                    <h2>{{ viewingResume ? viewingResume.file_name : 'Resume' }}</h2>
                    <button class="btn-secondary btn-compact" @click="closeViewModal">Close</button>
                </div>

                <div v-if="viewLoading" class="loading-row">
                    <div class="spinner"></div> Loading…
                </div>

                <template v-else-if="viewingResume">
                    <!-- View sub-tabs: PDF | Parsed Data -->
                    <nav class="view-sub-nav" v-if="viewingResume.has_pdf || viewingResume.structured_data">
                        <button
                            v-if="viewingResume.has_pdf"
                            :class="{ active: viewSubTab === 'pdf' }"
                            @click="activateViewSubTab('pdf')"
                        >PDF Document</button>
                        <button
                            v-if="viewingResume.structured_data"
                            :class="{ active: viewSubTab === 'parsed' }"
                            @click="activateViewSubTab('parsed')"
                        >Parsed Data</button>
                    </nav>

                    <!-- PDF sub-tab -->
                    <div v-if="viewSubTab === 'pdf' && viewingResume.has_pdf" class="view-pdf-container">
                        <div v-if="pdfLoading" class="loading-row queue-loading-row">
                            <div class="spinner"></div> Loading PDF preview...
                        </div>
                        <div v-else-if="pdfLoadError" class="view-error-state">
                            <p class="view-error-text">{{ pdfLoadError }}</p>
                            <button class="btn-secondary" @click="loadPdfForView">Retry PDF</button>
                        </div>
                        <iframe
                            v-else-if="pdfViewUrl"
                            :src="pdfViewUrl"
                            class="pdf-iframe"
                            title="Resume PDF"
                        ></iframe>
                        <p v-else class="not-parsed-message">Preparing PDF preview...</p>
                    </div>

                    <!-- Parsed data sub-tab -->
                    <template v-if="viewSubTab === 'parsed' && viewingResume.structured_data">
                        <span :class="['badge', badgeClass(viewingResume), 'view-badge']">
                            {{ badgeText(viewingResume) }}
                        </span>

                        <!-- Portal readiness bar -->
                        <div class="view-section">
                            <h4>Portal Readiness</h4>
                            <div class="portal-bar-wrap">
                                <div class="portal-bar-track">
                                    <div
                                        class="portal-bar-fill"
                                        :class="{ partial: !viewingResume.portal_ready }"
                                        :style="{ width: portalPercent(viewingResume) + '%' }"
                                    ></div>
                                </div>
                                <span class="portal-fill-caption">{{ portalFilledCount(viewingResume) }}/15 required fields filled</span>
                            </div>

                            <div v-if="missingRequiredList(viewingResume).length" class="missing-fields-list">
                                <span
                                    v-for="field in missingRequiredList(viewingResume).slice(0, 6)"
                                    :key="field"
                                    class="missing-field-pill"
                                >
                                    {{ field }}
                                </span>
                            </div>
                            <button
                                v-if="missingRequiredList(viewingResume).length"
                                type="button"
                                class="btn-secondary portal-action-btn"
                                @click="goToApplicantInfo"
                            >
                                Review Missing Fields
                            </button>
                        </div>

                        <!-- Personal Info -->
                        <div v-if="viewingResume.structured_data.personal_info" class="view-section">
                            <h4>Personal Information</h4>
                            <div class="view-grid">
                                <div class="view-field">
                                    <label>Name</label>
                                    <p>{{ fullName(viewingResume.structured_data.personal_info) || '—' }}</p>
                                </div>
                                <div class="view-field">
                                    <label>Email</label>
                                    <p>{{ displayValue(viewingResume.structured_data.personal_info.email) }}</p>
                                </div>
                                <div class="view-field">
                                    <label>Phone</label>
                                    <p>{{ displayValue(viewingResume.structured_data.personal_info.phone) }}</p>
                                </div>
                                <div class="view-field">
                                    <label>Location</label>
                                    <p>{{ displayValue(locationStr(viewingResume.structured_data.personal_info)) }}</p>
                                </div>
                                <div v-if="!isPlaceholderValue(viewingResume.structured_data.personal_info.linkedin)" class="view-field">
                                    <label>LinkedIn</label>
                                    <p>{{ displayValue(viewingResume.structured_data.personal_info.linkedin) }}</p>
                                </div>
                                <div v-if="!isPlaceholderValue(viewingResume.structured_data.personal_info.website)" class="view-field">
                                    <label>Website</label>
                                    <p>{{ displayValue(viewingResume.structured_data.personal_info.website) }}</p>
                                </div>
                            </div>
                        </div>

                        <!-- Summary -->
                        <div v-if="!isPlaceholderValue(viewingResume.structured_data.summary)" class="view-section">
                            <h4>Summary</h4>
                            <p class="summary-text">
                                {{ displayValue(viewingResume.structured_data.summary) }}
                            </p>
                        </div>

                        <!-- Skills -->
                        <div v-if="hasSkills(viewingResume.structured_data.skills)" class="view-section">
                            <h4>Skills</h4>
                            <div v-if="viewingResume.structured_data.skills.technical && viewingResume.structured_data.skills.technical.length">
                                <p class="skill-group-label">Technical</p>
                                <div class="skill-pills">
                                    <span v-for="s in viewingResume.structured_data.skills.technical" :key="s" class="skill-pill">{{ s }}</span>
                                </div>
                            </div>
                            <div v-if="viewingResume.structured_data.skills.languages && viewingResume.structured_data.skills.languages.length">
                                <p class="skill-group-label">Languages</p>
                                <div class="skill-pills">
                                    <span v-for="s in viewingResume.structured_data.skills.languages" :key="s" class="skill-pill">{{ s }}</span>
                                </div>
                            </div>
                            <div v-if="viewingResume.structured_data.skills.tools && viewingResume.structured_data.skills.tools.length">
                                <p class="skill-group-label">Tools</p>
                                <div class="skill-pills">
                                    <span v-for="s in viewingResume.structured_data.skills.tools" :key="s" class="skill-pill">{{ s }}</span>
                                </div>
                            </div>
                            <div v-if="viewingResume.structured_data.skills.soft_skills && viewingResume.structured_data.skills.soft_skills.length">
                                <p class="skill-group-label">Soft Skills</p>
                                <div class="skill-pills">
                                    <span v-for="s in viewingResume.structured_data.skills.soft_skills" :key="s" class="skill-pill">{{ s }}</span>
                                </div>
                            </div>
                        </div>

                        <!-- Education -->
                        <div v-if="viewingResume.structured_data.education && viewingResume.structured_data.education.length" class="view-section">
                            <h4>Education</h4>
                            <div v-for="(edu, i) in viewingResume.structured_data.education" :key="i" class="exp-entry">
                                <p class="exp-title">{{ edu.institution || '—' }}</p>
                                <p class="exp-sub">
                                    {{ [edu.degree, edu.field_of_study].filter(Boolean).join(' — ') }}
                                    <span v-if="edu.end_date"> · {{ edu.end_date }}</span>
                                </p>
                                <p v-if="edu.gpa" class="gpa-text">GPA: {{ edu.gpa }}</p>
                            </div>
                        </div>

                        <!-- Work Experience -->
                        <div v-if="viewingResume.structured_data.work_experience && viewingResume.structured_data.work_experience.length" class="view-section">
                            <h4>Work Experience</h4>
                            <div v-for="(job, i) in viewingResume.structured_data.work_experience" :key="i" class="exp-entry">
                                <p class="exp-title">{{ job.title || '—' }}</p>
                                <p class="exp-sub">
                                    {{ job.company || '' }}
                                    <span v-if="job.start_date || job.end_date">
                                        · {{ job.start_date || '' }} – {{ job.end_date || 'Present' }}
                                    </span>
                                </p>
                                <ul v-if="job.bullets && job.bullets.length">
                                    <li v-for="(b, j) in job.bullets" :key="j">{{ b }}</li>
                                </ul>
                            </div>
                        </div>
                    </template>

                    <!-- No data at all -->
                    <div v-if="!viewingResume.has_pdf && !viewingResume.structured_data" class="not-parsed-message">
                        This resume hasn't been parsed yet. Delete and re-import to parse it.
                    </div>
                </template>

                <div v-else-if="viewError" class="view-error-state">
                    <p class="view-error-text">{{ viewError }}</p>
                    <button class="btn-secondary" @click="viewResume(_viewResumeId)">Retry</button>
                </div>

            </div>
        </div>

        <div v-if="showPipelineDetails" class="modal-overlay" @click.self="showPipelineDetails = false">
            <div class="modal-box pipeline-details-modal" v-draggable-modal="{ handle: '.modal-drag-header' }">
                <div class="modal-drag-header drag-handle view-modal-header-row">
                    <h2>Resume Parsing Pipelines</h2>
                    <button class="btn-secondary btn-compact" @click="showPipelineDetails = false">Close</button>
                </div>
                <p class="subtitle">UAH parser order (highest reliability/accuracy to lowest): Local AI, Cloud AI, Rules-based.</p>
                <div class="pipeline-cards">
                    <article class="pipeline-card" :class="{ selected: parseMethod === 'local' }">
                        <h4>Local AI</h4>
                        <p>Uses UAH local Ollama OCR and local parsing models. Best for isolated processing and method-specific local queue visibility.</p>
                        <span class="pipeline-meta">Network: internal/VPN · Latency: variable · Privacy: higher</span>
                    </article>
                    <article class="pipeline-card" :class="{ selected: parseMethod === 'cloud' }">
                        <h4>Cloud AI (ZAI)</h4>
                        <p>Uses web ZAI OCR (glm-ocr) and GLM-4.7-Flash parsing. Cloud throughput is concurrency-limited and does not expose a provider-side waiting queue.</p>
                        <span class="pipeline-meta">Network: external · Latency: medium · Privacy: lower</span>
                    </article>
                    <article class="pipeline-card" :class="{ selected: parseMethod === 'rules' }">
                        <h4>Rules-based</h4>
                        <p>Deterministic parser using embedded PDF text only. Rules mode is isolated from OCR/model queues and may fail on scanned image-only PDFs.</p>
                        <span class="pipeline-meta">Network: none · Latency: low · Privacy: highest</span>
                    </article>
                </div>
            </div>
        </div>

    </div><!-- /.page -->
</template>


<script>
import { authedFetch, getCurrentUser, setCurrentUser } from '../lib/auth.js'
import { publishCurrentPageDiagnostics, clearCurrentPageDiagnostics } from '../lib/debugDiagnostics'
import { showToast } from '../services/toastService.js'

const APPINFO_KEY = 'uah_applicant_info'

export default {
    name: 'Resumes',

    data() {
        return {
            activeTab: 'imported',

            // ── Imported Resumes tab ────────────────────────
            resumes: [],
            resumesLoading: false,
            resumesError: null,
            deletingId: null,

            // Inline upload
            uploadStep: 'select',   // 'select' | 'confirm'
            pendingFile: null,
            parseMethod: 'local',
            uploading: false,
            uploadError: null,
            isDragOver: false,

            // Async parse progress
            parseJobId: null,
            parseStatus: null,      // queued|parsing|validating|success|failed|cancelled
            parseStageLabel: '',
            parseError: null,
            _pollTimer: null,
            parseJobMethod: null,
            parseAttempt: null,
            parseElapsedSeconds: null,
            parseQueuePosition: null,
            parseQueueTotal: null,
            parseErrorCode: null,

            // Queue panel
            queueScope: 'user',
            queueStatus: null,
            queueLoading: false,
            queueError: null,
            _queueTimer: null,

            // View modal
            showViewModal: false,
            viewingResume: null,
            viewLoading: false,
            viewError: null,
            viewSubTab: 'pdf',   // 'pdf' | 'parsed'
            _viewResumeId: null,
            pdfObjectUrl: '',
            pdfLoading: false,
            pdfLoadError: null,

            // Parse details popup
            showPipelineDetails: false,

            // ── Applicant Information tab ───────────────────
            currentUser: null,
            profiles: [],
            activeProfileId: null,
            profilesLoading: false,
            firstName: '',
            lastName: '',
            appEmail: '',
            phone: '',
            linkedin: '',
            portfolio: '',
            streetAddress: '',
            city: '',
            appState: '',
            zip: '',
            summary: '',
            workAuth: '',
            requiresSponsorship: '',
            degree: '',
            major: '',
            university: '',
            gradYear: '',
            gpa: '',
            yearsExperience: '',
            jobTitle: '',
            skillsText: '',
            certificationsText: '',
            professionalLinksText: '',
            educationHistoryText: '',
            employmentHistoryText: '',
            demographicGender: '',
            demographicEthnicity: '',
            working: false,
            saveStatus: { type: '', message: '' },
            _saveTimer: null,
            showNewProfileInput: false,
            newProfileName: '',

            // ── Job Application Info tab ────────────────────
            veteranOptions: [
                'I am not a protected veteran',
                'I identify as one or more of the classifications of protected veteran',
                'I prefer not to answer',
            ],
            disabilityOptions: [
                'Yes, I have a disability (or previously had a disability)',
                'No, I do not have a disability',
                'I prefer not to answer',
            ],
            californiaOptions: [
                'Yes, I am a California resident',
                'No, I am not a California resident',
            ],
            veteranStatus: '',
            disabilityStatus: '',
            californiaResident: '',
            jobInfoError: '',
            jobInfoSuccess: '',
            _jobInfoTimer: null,
        }
    },

    computed: {
        portalReadyCount() {
            return this.resumes.filter(r => r.portal_ready).length
        },
        latestUploadDate() {
            if (!this.resumes.length) return '—'
            return this.formatDate(this.resumes[0].created_at)
        },
        parseProgressPercent() {
            if (this.parseStatus === 'queued' && this.parseQueuePosition && this.parseQueueTotal) {
                const queueFraction = (this.parseQueuePosition - 1) / Math.max(this.parseQueueTotal, 1)
                const queuedPercent = Math.round(30 - (queueFraction * 20))
                return Math.min(Math.max(queuedPercent, 10), 35)
            }

            const map = { queued: 15, parsing: 55, validating: 85, success: 100, failed: 0, cancelled: 0 }
            return map[this.parseStatus] ?? 0
        },
        parseProgressHint() {
            const activeMethod = this.parseJobMethod || this.parseMethod
            if (this.parseStatus === 'queued' && this.parseQueuePosition && this.parseQueueTotal) {
                return `Queued #${this.parseQueuePosition} of ${this.parseQueueTotal} in ${activeMethod} pipeline…`
            }

            const map = {
                queued: 'Preparing to parse the selected UAH resume…',
                parsing: activeMethod === 'rules'
                    ? 'Rules engine is reading embedded PDF text…'
                    : activeMethod === 'cloud'
                        ? 'Cloud AI (ZAI OCR + GLM-4.7-Flash) is analyzing the resume…'
                        : 'Local AI is analyzing the resume…',
                validating: 'Validating and normalizing extracted fields…',
                success: 'Parsing complete!',
                failed: 'Parsing failed.',
                cancelled: 'Cancelled.',
            }
            return map[this.parseStatus] ?? ''
        },
        parseElapsedLabel() {
            if (this.parseElapsedSeconds === null || this.parseElapsedSeconds === undefined) return ''
            if (this.parseElapsedSeconds < 60) return `${this.parseElapsedSeconds}s elapsed`
            const mins = Math.floor(this.parseElapsedSeconds / 60)
            const secs = this.parseElapsedSeconds % 60
            return `${mins}m ${secs}s elapsed`
        },
        parseAttemptLabel() {
            if (this.parseAttempt === null || this.parseAttempt === undefined) return ''
            if (this.parseAttempt <= 0) return 'Attempt 1'
            return `Retry ${this.parseAttempt}`
        },
        selectedParseMethodDescription() {
            const map = {
                local: 'Local AI uses UAH local OCR + local parsing with isolated queue visibility.',
                cloud: 'Cloud AI uses web ZAI OCR and GLM-4.7-Flash with concurrency-limited throughput.',
                rules: 'Rules-based parsing is deterministic from embedded PDF text only (no OCR fallback).',
            }
            return map[this.parseMethod] || ''
        },
        canViewGlobalQueue() {
            return !!this.queueStatus?.can_view_global
        },
        pdfViewUrl() {
            return this.pdfObjectUrl || ''
        },
    },

    async mounted() {
        await this.loadResumes()
        await this.loadProfiles()
        await this.loadQueueStatus()
        this.startQueuePolling()
        this.publishDebugState('mounted')
    },

    watch: {
        activeTab(nextTab) {
            if (nextTab === 'imported') {
                this.startQueuePolling()
                return
            }
            this.stopQueuePolling()
        },
        parseMethod() {
            if (this.activeTab === 'imported') {
                this.loadQueueStatus()
            }
        },
    },

    beforeUnmount() {
        if (this._saveTimer) clearTimeout(this._saveTimer)
        if (this._jobInfoTimer) clearTimeout(this._jobInfoTimer)
        if (this._pollTimer) clearTimeout(this._pollTimer)
        this.stopQueuePolling()
        this.cleanupPdfObjectUrl()
        clearCurrentPageDiagnostics()
    },

    methods: {
        isPlaceholderValue(value) {
            if (value === null || value === undefined) return true
            if (typeof value !== 'string') return false
            const cleaned = value.trim().toLowerCase()
            if (!cleaned) return true
            return ['null', 'none', 'n/a', 'na', 'unknown', 'not provided', 'not available', '-', '--'].includes(cleaned)
        },

        cleanTextValue(value) {
            if (value === null || value === undefined) return ''
            if (typeof value !== 'string') return value
            return this.isPlaceholderValue(value) ? '' : value.trim()
        },

        displayValue(value) {
            const cleaned = this.cleanTextValue(value)
            return cleaned || '—'
        },

        parseMethodTagLabel(method) {
            const map = {
                cloud: 'CLOUD | ZAI',
                cloud_ai: 'CLOUD | ZAI',
                cloud_llm: 'CLOUD | ZAI',
                zai: 'CLOUD | ZAI',
                local: 'LOCAL | OLLAMA',
                local_ai: 'LOCAL | OLLAMA',
                local_llm: 'LOCAL | OLLAMA',
                rules: 'RULES | DETERMINISTIC',
                llm: 'AI | AUTO',
            }
            const key = (method || '').toLowerCase()
            return map[key] || method || 'Unknown'
        },

        parseMethodToneClass(method) {
            const normalized = (method || '').toLowerCase()
            if (['cloud', 'cloud_ai', 'cloud_llm', 'zai'].includes(normalized)) return 'method-cloud'
            if (['rules'].includes(normalized)) return 'method-rules'
            return 'method-local'
        },

        stopQueuePolling() {
            if (this._queueTimer) {
                clearTimeout(this._queueTimer)
                this._queueTimer = null
            }
        },

        startQueuePolling() {
            this.stopQueuePolling()
            if (this.activeTab !== 'imported') return

            const tick = async () => {
                await this.loadQueueStatus()
                if (this.activeTab === 'imported') {
                    this._queueTimer = setTimeout(tick, 5000)
                }
            }

            tick()
        },

        async loadQueueStatus() {
            if (this.activeTab !== 'imported') return

            this.queueLoading = true
            this.queueError = null
            try {
                const focusMethod = encodeURIComponent(this.parseJobMethod || this.parseMethod || 'local')
                const res = await authedFetch(`/api/resume/queue/status?scope=${encodeURIComponent(this.queueScope)}&focus_method=${focusMethod}`)
                if (!res.ok) throw new Error(`HTTP ${res.status}`)
                this.queueStatus = await res.json()

                if (!this.queueStatus?.can_view_global && this.queueScope === 'global') {
                    this.queueScope = 'user'
                }
            } catch (e) {
                if (e.message === 'Session expired' || e.message === 'Not authenticated') {
                    this.$router.push('/login')
                    return
                }
                this.queueError = 'Failed to load queue status.'
            } finally {
                this.queueLoading = false
            }
        },

        setQueueScope(scope) {
            if (scope === this.queueScope) return
            this.queueScope = scope
            this.loadQueueStatus()
        },

        cleanupPdfObjectUrl() {
            if (this.pdfObjectUrl) {
                URL.revokeObjectURL(this.pdfObjectUrl)
                this.pdfObjectUrl = ''
            }
        },

        closeViewModal() {
            this.showViewModal = false
            this.cleanupPdfObjectUrl()
            this.pdfLoading = false
            this.pdfLoadError = null
        },

        activateViewSubTab(tab) {
            this.viewSubTab = tab
            if (tab === 'pdf' && this.viewingResume?.has_pdf && !this.pdfObjectUrl && !this.pdfLoading) {
                this.loadPdfForView()
            }
        },

        async loadPdfForView() {
            if (!this.viewingResume?.id || !this.viewingResume?.has_pdf) return

            this.pdfLoading = true
            this.pdfLoadError = null
            this.cleanupPdfObjectUrl()

            try {
                const res = await authedFetch(`/api/resume/${this.viewingResume.id}/pdf`)
                if (!res.ok) throw new Error(`HTTP ${res.status}`)

                const blob = await res.blob()
                this.pdfObjectUrl = URL.createObjectURL(blob)
            } catch (e) {
                if (e.message === 'Session expired' || e.message === 'Not authenticated') {
                    this.$router.push('/login')
                    return
                }
                this.pdfLoadError = 'Failed to load PDF preview.'
            } finally {
                this.pdfLoading = false
            }
        },

        publishDebugState(reason = 'state-update') {
            publishCurrentPageDiagnostics({
                reason,
                activeTab: this.activeTab,
                resumesLoading: this.resumesLoading,
                resumesCount: this.resumes.length,
                resumesError: this.resumesError,
                uploadStep: this.uploadStep,
                uploading: this.uploading,
                uploadError: this.uploadError,
                showViewModal: this.showViewModal,
                viewLoading: this.viewLoading,
                viewingResumeId: this.viewingResume?.id || null,
                saveStatus: this.saveStatus,
                jobInfoError: this.jobInfoError,
                jobInfoSuccess: this.jobInfoSuccess,
            })
        },

        // ── Resume list ─────────────────────────────────────
        async loadResumes() {
            this.resumesLoading = true
            this.resumesError = null
            try {
                const res = await authedFetch('/api/resume/')
                if (!res.ok) throw new Error(`HTTP ${res.status}`)
                this.resumes = await res.json()
                this.publishDebugState('resumes-loaded')
            } catch (e) {
                if (e.message === 'Session expired' || e.message === 'Not authenticated') {
                    this.$router.push('/login')
                } else {
                    this.resumesError = 'Failed to load resumes.'
                }
                this.publishDebugState('resumes-load-error')
            } finally {
                this.resumesLoading = false
            }
        },

        badgeClass(r) {
            if (r.portal_ready) return 'portal-ready'
            if (r.parse_method) return 'needs-fields'
            return 'not-parsed'
        },
        badgeText(r) {
            if (r.portal_ready) return 'Portal Ready'
            if (r.parse_method) return 'Needs Fields'
            return 'Not Parsed'
        },

        handleDelete(id) {
            if (this.deletingId === id) {
                this.confirmDelete(id)
            } else {
                this.deletingId = id
                setTimeout(() => { if (this.deletingId === id) this.deletingId = null }, 3000)
            }
        },
        async confirmDelete(id) {
            this.deletingId = null
            try {
                await authedFetch(`/api/resume/${id}`, { method: 'DELETE' })
                await this.loadResumes()
            } catch { /* ignore */ }
        },

        // ── View modal ──────────────────────────────────────
        async viewResume(id) {
            this._viewResumeId = id
            this.showViewModal = true
            this.viewLoading = true
            this.viewingResume = null
            this.viewError = null
            this.pdfLoadError = null
            this.pdfLoading = false
            this.cleanupPdfObjectUrl()
            this.publishDebugState('view-open')
            try {
                const res = await authedFetch(`/api/resume/${id}`)
                if (!res.ok) throw new Error(`HTTP ${res.status}`)
                this.viewingResume = await res.json()
                // Default to PDF tab if available, else parsed data
                this.viewSubTab = this.viewingResume.has_pdf ? 'pdf' : 'parsed'
                if (this.viewSubTab === 'pdf') {
                    await this.loadPdfForView()
                }
                this.publishDebugState('view-loaded')
            } catch (e) {
                this.viewError = 'Failed to load resume data. Please try again.'
                this.publishDebugState('view-load-error')
            } finally {
                this.viewLoading = false
            }
        },

        fullName(pi) {
            const first = this.cleanTextValue(pi.first_name)
            const last = this.cleanTextValue(pi.last_name)
            return [first, last].filter(Boolean).join(' ')
        },
        locationStr(pi) {
            const city = this.cleanTextValue(pi.city)
            const state = this.cleanTextValue(pi.state)
            return [city, state].filter(Boolean).join(', ')
        },
        hasSkills(skills) {
            if (!skills) return false
            const validCount = (arr) => (Array.isArray(arr) ? arr.filter((item) => !this.isPlaceholderValue(item)).length : 0)
            return !!(
                validCount(skills.technical)
                || validCount(skills.languages)
                || validCount(skills.tools)
                || validCount(skills.soft_skills)
            )
        },
        missingRequiredList(r) {
            const list = r?.structured_data?._validation?.missing_required
            if (!Array.isArray(list)) return []
            return list
        },
        portalFilledCount(r) {
            if (!r.structured_data) return 0
            const pi = r.structured_data.personal_info || {}
            const edu = r.structured_data.education?.[0] || {}
            const work = r.structured_data.work_experience?.[0] || {}
            const fields = [
                pi.first_name, pi.last_name, pi.email, pi.phone, pi.city, pi.state,
                edu.institution, edu.degree, edu.field_of_study, edu.start_date, edu.end_date,
                work.company, work.title, work.start_date, work.end_date,
            ]
            return fields.filter((value) => !this.isPlaceholderValue(value)).length
        },
        portalPercent(r) {
            return Math.round((this.portalFilledCount(r) / 15) * 100)
        },
        goToApplicantInfo() {
            this.closeViewModal()
            this.activeTab = 'applicant'
            this.publishDebugState('navigate-to-applicant-from-readiness')
        },

        // ── Inline upload ───────────────────────────────────
        openUploadModal() {
            this.uploadStep = 'select'
            this.pendingFile = null
            this.parseMethod = 'local'
            this.uploadError = null
            this.isDragOver = false
            this.$nextTick(() => {
                this.$refs.inlineImportSection?.scrollIntoView({ behavior: 'smooth', block: 'start' })
            })
            this.publishDebugState('upload-open')
        },
        resetUploadFlow() {
            this.uploadStep = 'select'
            this.pendingFile = null
            this.uploadError = null
            this.uploading = false
            this.isDragOver = false
            this.parseJobId = null
            this.parseStatus = null
            this.parseStageLabel = ''
            this.parseError = null
            this.parseJobMethod = null
            this.parseAttempt = null
            this.parseElapsedSeconds = null
            this.parseQueuePosition = null
            this.parseQueueTotal = null
            this.parseErrorCode = null
            if (this._pollTimer) clearTimeout(this._pollTimer)
        },
        triggerFileInput() {
            this.$refs.fileInput.value = ''
            this.$refs.fileInput.click()
        },
        onFileChange(e) {
            const file = e.target.files?.[0]
            if (file) this.setPendingFile(file)
        },
        onFileDrop(e) {
            this.isDragOver = false
            const file = e.dataTransfer.files?.[0]
            if (file) this.setPendingFile(file)
        },
        setPendingFile(file) {
            this.uploadError = null
            if (!file.type.includes('pdf') && !file.name.toLowerCase().endsWith('.pdf')) {
                this.uploadError = 'Only PDF files are supported.'
                return
            }
            if (file.size > 5 * 1024 * 1024) {
                this.uploadError = 'File is too large. Maximum size is 5 MB.'
                return
            }
            this.pendingFile = file
            this.uploadStep = 'confirm'
        },
        clearFile() {
            this.pendingFile = null
            this.uploadStep = 'select'
            this.uploadError = null
        },
        async doUpload() {
            if (!this.pendingFile || this.uploading) return
            this.uploading = true
            this.uploadError = null
            try {
                // 1. Upload
                const form = new FormData()
                form.append('file', this.pendingFile)
                const uploadRes = await authedFetch('/api/resume/upload', {
                    method: 'POST',
                    body: form,
                })
                const uploadData = await uploadRes.json().catch(() => null)
                if (!uploadRes.ok) {
                    throw new Error(this.apiErrorMessage(uploadData, uploadRes.status, 'Upload failed'))
                }

                // 2. Start async parse
                const resumeId = uploadData.id
                const parseRes = await authedFetch(`/api/resume/${resumeId}/parse-async`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ method: this.parseMethod }),
                })
                const parseData = await parseRes.json().catch(() => null)
                if (!parseRes.ok) {
                    throw new Error(this.apiErrorMessage(parseData, parseRes.status, 'Parse failed'))
                }

                // 3. Switch to parsing progress stage
                this.parseJobId = parseData.job_id
                this.parseStatus = 'queued'
                this.parseStageLabel = 'Queued…'
                this.parseError = null
                this.parseJobMethod = this.parseMethod
                this.uploadStep = 'parsing'
                this.uploading = false
                this.publishDebugState('parse-started')

                // Start polling
                this.pollParseJob()
            } catch (e) {
                this.uploadError = e.message ?? String(e)
                this.uploading = false
                this.publishDebugState('upload-error')
            }
        },

        async pollParseJob() {
            if (!this.parseJobId) return
            try {
                const res = await authedFetch(`/api/resume/parse-job/${this.parseJobId}?include_queue=true`)
                if (!res.ok) throw new Error(`HTTP ${res.status}`)
                const job = await res.json()

                if (job.queue_snapshot && this.queueScope !== 'global') {
                    this.queueStatus = job.queue_snapshot
                }

                this.parseStatus = job.status
                this.parseStageLabel = job.progress_stage || this.parseStageLabel
                this.parseAttempt = job.attempt
                this.parseElapsedSeconds = job.elapsed_seconds
                this.parseQueuePosition = job.queue_position
                this.parseQueueTotal = job.queue_total
                this.parseErrorCode = job.error_code || null

                if (job.status === 'success') {
                    const summary = job.result_summary || {}
                    const readiness = summary.portal_ready ? 'Portal-ready' : 'Needs additional fields'
                    showToast(`Parse complete. ${readiness}.`, 'success')
                    this.resetUploadFlow()
                    await this.loadResumes()
                    await this.loadQueueStatus()
                    this.publishDebugState('parse-success')
                    return
                }
                if (job.status === 'failed') {
                    const details = job.error_code ? `[${job.error_code}] ${job.error_message || 'Parsing failed.'}` : (job.error_message || 'Parsing failed.')
                    this.uploadError = details
                    showToast('Parse failed. Review the error and retry.', 'error')
                    this.uploadStep = 'confirm'
                    this.parseJobId = null
                    this.parseJobMethod = null
                    this.publishDebugState('parse-failed')
                    return
                }
                if (job.status === 'cancelled') {
                    showToast('Parse cancelled.', 'success')
                    this.uploadStep = 'confirm'
                    this.parseJobId = null
                    this.parseJobMethod = null
                    this.publishDebugState('parse-cancelled')
                    return
                }

                // Still running — poll again
                this._pollTimer = setTimeout(() => this.pollParseJob(), 1800)
            } catch (e) {
                this.uploadError = 'Lost connection while checking parse status.'
                this.uploadStep = 'confirm'
                this.parseJobId = null
                this.publishDebugState('poll-error')
            }
        },

        async cancelParse() {
            if (!this.parseJobId) return
            try {
                await authedFetch(`/api/resume/parse-job/${this.parseJobId}/cancel`, { method: 'POST' })
            } catch { /* best-effort */ }
            if (this._pollTimer) clearTimeout(this._pollTimer)
            this.parseStatus = 'cancelled'
            this.uploadStep = 'confirm'
            this.parseJobId = null
            this.parseJobMethod = null
            showToast('Parse cancelled.', 'success')
            this.publishDebugState('parse-cancelled-by-user')
        },

        // ── Profile Management ────────────────────────────
        async loadProfiles() {
            this.profilesLoading = true
            this.currentUser = getCurrentUser()
            try {
                const res = await authedFetch('/api/applicant-profile/')
                if (!res.ok) throw new Error(`HTTP ${res.status}`)
                this.profiles = await res.json()

                if (this.profiles.length === 0) {
                    // First-time: migrate from localStorage if present, or create empty default
                    await this.migrateLocalToBackend()
                } else {
                    // Load the active profile
                    const active = this.profiles.find(p => p.is_active) || this.profiles[0]
                    await this.loadProfileData(active.id)
                }
            } catch (e) {
                if (e.message === 'Session expired' || e.message === 'Not authenticated') {
                    this.$router.push('/login')
                    return
                }
                // Fallback: try to load from localStorage
                this.loadApplicantInfoFromLocal()
            } finally {
                this.profilesLoading = false
            }
        },

        async migrateLocalToBackend() {
            const payload = this.buildProfilePayload()
            // Check localStorage for existing data
            try {
                const saved = localStorage.getItem(APPINFO_KEY)
                if (saved) {
                    const d = JSON.parse(saved)
                    Object.assign(payload, {
                        phone: d.phone || '', linkedin: d.linkedin || '', portfolio: d.portfolio || '',
                        street_address: d.streetAddress || '', city: d.city || '', state: d.appState || '', zip: d.zip || '',
                        summary: d.summary || '', work_auth: d.workAuth || '', requires_sponsorship: d.requiresSponsorship || '',
                        degree: d.degree || '', major: d.major || '', university: d.university || '',
                        grad_year: d.gradYear || '', gpa: d.gpa || '',
                        years_experience: d.yearsExperience || '', job_title: d.jobTitle || '',
                        skills_text: d.skillsText || '', certifications_text: d.certificationsText || '',
                        professional_links_text: d.professionalLinksText || '',
                        education_history_text: d.educationHistoryText || '',
                        employment_history_text: d.employmentHistoryText || '',
                        demographic_gender: d.demographicGender || '',
                        demographic_ethnicity: d.demographicEthnicity || '',
                    })
                }
                const eeo = localStorage.getItem('uah_job_info')
                if (eeo) {
                    const d = JSON.parse(eeo)
                    payload.veteran_status = d.veteranStatus || ''
                    payload.disability_status = d.disabilityStatus || ''
                    payload.california_resident = d.californiaResident || ''
                }
            } catch { /* ignore local parse errors */ }

            // Fill from current user
            if (this.currentUser) {
                payload.first_name = payload.first_name || this.currentUser.first_name || this.currentUser.firstName || ''
                payload.last_name = payload.last_name || this.currentUser.last_name || this.currentUser.lastName || ''
                payload.email = payload.email || this.currentUser.email || ''
            }

            try {
                const res = await authedFetch('/api/applicant-profile/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                })
                if (res.ok) {
                    const profile = await res.json()
                    this.populateFormFromProfile(profile)
                    this.profiles = [{ id: profile.id, name: profile.name, is_active: true, first_name: profile.first_name, last_name: profile.last_name, created_at: profile.created_at }]
                    // Clean up localStorage after successful migration
                    localStorage.removeItem(APPINFO_KEY)
                    localStorage.removeItem('uah_job_info')
                }
            } catch {
                this.loadApplicantInfoFromLocal()
            }
        },

        async loadProfileData(profileId) {
            try {
                const res = await authedFetch(`/api/applicant-profile/${profileId}`)
                if (!res.ok) throw new Error(`HTTP ${res.status}`)
                const profile = await res.json()
                this.populateFormFromProfile(profile)
            } catch {
                this.loadApplicantInfoFromLocal()
            }
        },

        populateFormFromProfile(p) {
            this.activeProfileId = p.id
            this.firstName = p.first_name || ''
            this.lastName = p.last_name || ''
            this.appEmail = p.email || ''
            this.phone = p.phone || ''
            this.linkedin = p.linkedin || ''
            this.portfolio = p.portfolio || ''
            this.streetAddress = p.street_address || ''
            this.city = p.city || ''
            this.appState = p.state || ''
            this.zip = p.zip || ''
            this.summary = p.summary || ''
            this.workAuth = p.work_auth || ''
            this.requiresSponsorship = p.requires_sponsorship || ''
            this.degree = p.degree || ''
            this.major = p.major || ''
            this.university = p.university || ''
            this.gradYear = p.grad_year || ''
            this.gpa = p.gpa || ''
            this.yearsExperience = p.years_experience || ''
            this.jobTitle = p.job_title || ''
            this.skillsText = p.skills_text || ''
            this.certificationsText = p.certifications_text || ''
            this.professionalLinksText = p.professional_links_text || ''
            this.educationHistoryText = p.education_history_text || ''
            this.employmentHistoryText = p.employment_history_text || ''
            this.demographicGender = p.demographic_gender || ''
            this.demographicEthnicity = p.demographic_ethnicity || ''
            this.veteranStatus = p.veteran_status || ''
            this.disabilityStatus = p.disability_status || ''
            this.californiaResident = p.california_resident || ''
        },

        buildProfilePayload() {
            return {
                name: 'Default',
                first_name: this.firstName, last_name: this.lastName, email: this.appEmail,
                phone: this.phone, linkedin: this.linkedin, portfolio: this.portfolio,
                street_address: this.streetAddress, city: this.city, state: this.appState, zip: this.zip,
                summary: this.summary, work_auth: this.workAuth, requires_sponsorship: this.requiresSponsorship,
                degree: this.degree, major: this.major, university: this.university,
                grad_year: this.gradYear, gpa: this.gpa,
                years_experience: this.yearsExperience, job_title: this.jobTitle,
                skills_text: this.skillsText, certifications_text: this.certificationsText,
                professional_links_text: this.professionalLinksText,
                education_history_text: this.educationHistoryText,
                employment_history_text: this.employmentHistoryText,
                demographic_gender: this.demographicGender, demographic_ethnicity: this.demographicEthnicity,
                veteran_status: this.veteranStatus, disability_status: this.disabilityStatus,
                california_resident: this.californiaResident,
            }
        },

        loadApplicantInfoFromLocal() {
            this.currentUser = getCurrentUser()
            if (this.currentUser) {
                this.firstName = this.currentUser.first_name || this.currentUser.firstName || ''
                this.lastName = this.currentUser.last_name || this.currentUser.lastName || ''
                this.appEmail = this.currentUser.email || ''
            }
            try {
                const saved = localStorage.getItem(APPINFO_KEY)
                if (saved) {
                    const d = JSON.parse(saved)
                    this.phone = d.phone || ''; this.linkedin = d.linkedin || ''; this.portfolio = d.portfolio || ''
                    this.streetAddress = d.streetAddress || ''; this.city = d.city || ''; this.appState = d.appState || ''; this.zip = d.zip || ''
                    this.summary = d.summary || ''; this.workAuth = d.workAuth || ''; this.requiresSponsorship = d.requiresSponsorship || ''
                    this.degree = d.degree || ''; this.major = d.major || ''; this.university = d.university || ''
                    this.gradYear = d.gradYear || ''; this.gpa = d.gpa || ''
                    this.yearsExperience = d.yearsExperience || ''; this.jobTitle = d.jobTitle || ''
                    this.skillsText = d.skillsText || ''; this.certificationsText = d.certificationsText || ''
                    this.professionalLinksText = d.professionalLinksText || ''
                    this.educationHistoryText = d.educationHistoryText || ''; this.employmentHistoryText = d.employmentHistoryText || ''
                    this.demographicGender = d.demographicGender || ''; this.demographicEthnicity = d.demographicEthnicity || ''
                }
            } catch { /* ignore */ }
            try {
                const eeo = localStorage.getItem('uah_job_info')
                if (eeo) {
                    const d = JSON.parse(eeo)
                    this.veteranStatus = d.veteranStatus || ''; this.disabilityStatus = d.disabilityStatus || ''; this.californiaResident = d.californiaResident || ''
                }
            } catch { /* ignore */ }
        },

        async switchProfile(profileId) {
            if (profileId === this.activeProfileId) return
            try {
                const res = await authedFetch(`/api/applicant-profile/${profileId}/activate`, { method: 'POST' })
                if (!res.ok) throw new Error(`HTTP ${res.status}`)
                await this.loadProfileData(profileId)
                await this.refreshProfileList()
                this.publishDebugState('profile-switched')
            } catch (e) {
                this.saveStatus = { type: 'error', message: 'Failed to switch profile.' }
            }
        },

        async refreshProfileList() {
            try {
                const res = await authedFetch('/api/applicant-profile/')
                if (res.ok) this.profiles = await res.json()
            } catch { /* ignore */ }
        },

        async createNewProfile() {
            const name = (this.newProfileName || '').trim()
            if (!name) return
            try {
                const res = await authedFetch('/api/applicant-profile/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        name,
                        is_default: this.profiles.length === 0  // Makes first profile created the default profile.
                    }),
                })
                if (!res.ok) {
                    const data = await res.json().catch(() => null)
                    throw new Error(data?.detail || `HTTP ${res.status}`)
                }
                const profile = await res.json()
                this.showNewProfileInput = false
                this.newProfileName = ''
                await this.switchProfile(profile.id)
                await this.refreshProfileList()
            } catch (e) {
                this.saveStatus = { type: 'error', message: e.message || 'Failed to create profile.' }
            }
        },
        isDefaultProfile(profileId) {
            const profile = this.profiles.find(p => p.id === profileId)
            return profile?.is_default || false
        },
        async deleteProfile(profileId) {
            if (this.profiles.length <= 1) {
                this.saveStatus = { type: 'error', message: 'Cannot delete your only profile.' }
                return
            }
            if (this.isDefaultProfile(profileId)) {
                alert("Default profile cannot be deleted.")
                return
            }
            try {
                const res = await authedFetch(`/api/applicant-profile/${profileId}`, { method: 'DELETE' })
                if (!res.ok) throw new Error(`HTTP ${res.status}`)
                await this.refreshProfileList()
                if (this.profiles.length) {
                    const active = this.profiles.find(p => p.is_active) || this.profiles[0]
                    await this.loadProfileData(active.id)
                }
                this.publishDebugState('profile-deleted')
            } catch (e) {
                this.saveStatus = { type: 'error', message: 'Failed to delete profile.' }
            }
        },

        async saveApplicantInfo() {
            this.working = true
            this.saveStatus = { type: '', message: '' }
            if (this._saveTimer) clearTimeout(this._saveTimer)
            try {
                const payload = this.buildProfilePayload()
                delete payload.name  // don't overwrite profile name on save

                if (this.activeProfileId) {
                    // Update existing profile
                    const res = await authedFetch(`/api/applicant-profile/${this.activeProfileId}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload),
                    })
                    if (!res.ok) {
                        const data = await res.json().catch(() => null)
                        throw new Error(data?.detail || `HTTP ${res.status}`)
                    }

                    // Also update user name if changed
                    const user = getCurrentUser()
                    const nameChanged =
                        this.firstName !== (user?.first_name || user?.firstName || '') ||
                        this.lastName !== (user?.last_name || user?.lastName || '')
                    if (nameChanged && (this.firstName || this.lastName)) {
                        const nameRes = await authedFetch('/api/account/change-name', {
                            method: 'PUT',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ first_name: this.firstName, last_name: this.lastName }),
                        })
                        const nameData = await nameRes.json().catch(() => null)
                        if (nameRes.ok) setCurrentUser(nameData)
                    }
                } else {
                    // Create new profile (shouldn't normally happen after migration)
                    payload.name = 'Default'
                    const res = await authedFetch('/api/applicant-profile/', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload),
                    })
                    if (!res.ok) throw new Error('Failed to create profile')
                    const profile = await res.json()
                    this.activeProfileId = profile.id
                    await this.refreshProfileList()
                }

                this.saveStatus = { type: 'success', message: 'Information saved.' }
                this.publishDebugState('applicant-save-success')
            } catch (e) {
                if (e.message === 'Session expired' || e.message === 'Not authenticated') {
                    this.$router.push('/login')
                    return
                }
                this.saveStatus = { type: 'error', message: e.message ?? 'Save failed.' }
                this.publishDebugState('applicant-save-error')
            } finally {
                this.working = false
                this._saveTimer = setTimeout(() => { this.saveStatus = { type: '', message: '' } }, 3500)
            }
        },

        // ── Job Application Info ────────────────────────────
        saveJobInfo() {
            this.jobInfoError = ''
            this.jobInfoSuccess = ''
            if (this._jobInfoTimer) clearTimeout(this._jobInfoTimer)
            if (!this.veteranStatus || !this.disabilityStatus || !this.californiaResident) {
                this.jobInfoError = 'Please complete all required fields before saving.'
                this.publishDebugState('jobinfo-validation-error')
                return
            }
            // Save EEO data to the active profile
            if (this.activeProfileId) {
                authedFetch(`/api/applicant-profile/${this.activeProfileId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        veteran_status: this.veteranStatus,
                        disability_status: this.disabilityStatus,
                        california_resident: this.californiaResident,
                    }),
                }).catch(() => {})
            }
            this.jobInfoSuccess = 'Information saved.'
            this.publishDebugState('jobinfo-save-success')
            this._jobInfoTimer = setTimeout(() => { this.jobInfoSuccess = '' }, 3500)
        },

        // ── Helpers ─────────────────────────────────────────
        formatDate(iso) {
            if (!iso) return '—'
            try {
                return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
            } catch { return iso }
        },
        formatBytes(bytes) {
            if (bytes < 1024) return bytes + ' B'
            if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
            return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
        },
        apiErrorMessage(payload, status, fallbackLabel) {
            if (status === 413) {
                return 'Upload request too large at gateway. Maximum file size is 5 MB.'
            }
            const detail = payload?.detail
            if (typeof detail === 'string' && detail.trim()) return detail
            if (detail && typeof detail === 'object') {
                if (typeof detail.message === 'string' && detail.message.trim()) return detail.message
                if (typeof detail.code === 'string' && detail.code.trim()) return `${fallbackLabel}: ${detail.code}`
            }
            return `${fallbackLabel} (HTTP ${status})`
        },
    },
}
</script>

<style scoped src="./css/Resumes.css"></style>
