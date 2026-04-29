<template>
    <div class="page app-flow-page resumes-page">

        <div class="greeting resume-hero">
            <div class="resume-hero-copy">
                <div class="greeting-left">
                    <h1>Resumes</h1>
                    <p>{{ activeTabSummary }}</p>
                </div>
            </div>
        </div>

        <div class="resume-nav-shell">
            <nav class="resume-nav">
                <button :class="{ active: activeTab === 'imported' }" @click="requestTabChange('imported')">
                    Imported Resumes
                </button>
                <button :class="{ active: activeTab === 'applicant' }" @click="requestTabChange('applicant')">
                    Applicant Information
                </button>
                <button :class="{ active: activeTab === 'jobinfo' }" @click="requestTabChange('jobinfo')">
                    Mandatory Disclosures
                </button>
            </nav>
        </div>

        <!-- ════════════════════════════════════════════════════
             TAB 1 — Imported Resumes
        ═════════════════════════════════════════════════════ -->
        <div v-if="activeTab === 'imported'" class="dashboard dashboard--imported">

            <Card
                ref="inlineImportSection"
                class="resume-card resume-card--workflow"
                :class="{ 'dashboard-span-full': !showImportSecondaryPanels }"
                variant="job"
            >
                <template #header>
                    <div class="panel-header">
                        <div>
                            <p class="panel-eyebrow">Workflow</p>
                            <h3>Import Resume</h3>
                        </div>
                    </div>
                </template>

                <p class="subtitle import-subtitle">Upload a UAH resume PDF and follow the staged flow: Select file, Confirm settings, Parse, then review readiness.</p>

                <div class="upload-stage-row">
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

                    <details class="pipeline-guardrails import-options-spaced">
                        <summary>Pipeline Guarantees</summary>
                        <p class="pipeline-ordering-note">UAH parser order (highest reliability/accuracy to lowest): Local AI, Cloud AI, Rules-based.</p>
                        <ul class="pipeline-guarantee-list" role="list">
                            <li class="pipeline-guarantee-item" role="listitem">
                                <strong>Local AI uses isolated local infrastructure.</strong>
                                <span>Local OCR plus local LLM processing, with method-specific local queue metrics.</span>
                            </li>
                            <li class="pipeline-guarantee-item" role="listitem">
                                <strong>Cloud AI uses web ZAI OCR and GLM-4.7-Flash.</strong>
                                <span>Cloud throughput is concurrency-limited; provider-side waiting queue is not exposed.</span>
                            </li>
                            <li class="pipeline-guarantee-item" role="listitem">
                                <strong>Rules-based parsing is deterministic and isolated.</strong>
                                <span>Rules mode reads embedded PDF text only and does not use OCR/model queues.</span>
                            </li>
                        </ul>
                    </details>

                    <div class="parse-method-group">
                        <div class="parse-method-header">
                            <label class="parse-method-label">Parse Pipeline</label>
                            <button class="btn-secondary btn-compact parse-details-btn" type="button" @click="showPipelineDetails = true">View Details</button>
                        </div>
                        <div class="method-toggle method-toggle-3">
                            <button :class="{ active: parseMethod === 'local' }" :disabled="!isLocalParseMethodAvailable" @click="parseMethod = 'local'">Local AI</button>
                            <button :class="{ active: parseMethod === 'cloud' }" @click="parseMethod = 'cloud'">Cloud AI (ZAI)</button>
                            <button :class="{ active: parseMethod === 'rules' }" @click="parseMethod = 'rules'">Rules-based</button>
                        </div>
                        <p v-if="!isLocalParseMethodAvailable && localParseMethodUnavailableMessage" class="parse-method-note parse-method-note-unavailable">{{ localParseMethodUnavailableMessage }}</p>
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
                            <span v-if="parseQueuePosition && parseQueueTotal"> · Queue {{ parseQueuePosition }}/{{ parseQueueTotal }} ({{ queueEnvironmentLabel }} scope)</span>
                        </p>
                        <p class="parse-progress-hint" v-if="parseErrorCode">Code: {{ parseErrorCode }}</p>
                        <button class="btn-secondary" @click="cancelParse" :disabled="parseStatus === 'cancelled'">
                            Cancel
                        </button>
                    </div>
                </template>

                <div v-if="uploadError" class="upload-error">{{ uploadError }}</div>
            </Card>

            <p v-if="!showImportSecondaryPanels" class="task-mode-note dashboard-span-full">
                Upload focus mode is active. Queue diagnostics and summary metrics will return after this import step.
            </p>
            <Card v-if="showImportSecondaryPanels" class="resume-card resume-card--library" variant="job">
                <template #header>
                    <div class="panel-header">
                        <div>
                            <p class="panel-eyebrow">Library</p>
                            <h3>Imported Resumes</h3>
                        </div>
                        <div class="library-header-actions">
                            <label v-if="resumes.length" class="sort-control">
                                <span>Sort</span>
                                <select v-model="resumeSort" name="resume_sort" autocomplete="off">
                                    <option value="newest">Newest first</option>
                                    <option value="oldest">Oldest first</option>
                                    <option value="name-asc">File name A-Z</option>
                                    <option value="name-desc">File name Z-A</option>
                                </select>
                            </label>
                            <button
                                v-if="libraryHasOverflow"
                                class="btn-secondary btn-compact"
                                type="button"
                                @click="showLibraryModal = true"
                            >
                                View All
                            </button>
                        </div>
                    </div>
                </template>

                <div v-if="resumesLoading" class="loading-row">
                    <div class="spinner"></div> Loading resumes…
                </div>

                <div v-else-if="resumesError" class="upload-error">{{ resumesError }}</div>

                <div v-else-if="sortedResumes.length" class="resume-list">
                    <div v-for="r in libraryPreviewResumes" :key="r.id" class="resume-list-item">
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
                            <button v-if="canReviewResume(r)" title="Review parsed data before profile fill" class="review-btn" @click="openReviewModal(r)">Review</button>
                            <button title="View parsed data" @click="viewResume(r.id)">View</button>
                            <button
                                title="Re-parse this resume"
                                :disabled="isReparseBusy(r.id)"
                                @click="startReparse(r)"
                            >
                                {{ isReparseBusy(r.id) ? 'Re-parsing…' : 'Re-parse' }}
                            </button>
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

                <div v-if="libraryHasOverflow" class="library-preview-footer">
                    <p class="library-preview-note">
                        Showing {{ libraryPreviewResumes.length }} of {{ resumes.length }} resumes.
                    </p>
                    <button class="btn-secondary" type="button" @click="showLibraryModal = true">
                        Expand Library
                    </button>
                </div>

                <div v-else class="empty-state">
                    <p>No resumes yet. Import a PDF to get started.</p>
                </div>
            </Card>

            <Card v-if="showImportSecondaryPanels" class="resume-card resume-card--stats" variant="job">
                <template #header>
                    <div class="panel-header">
                        <div>
                            <p class="panel-eyebrow">Insights</p>
                            <h3>Resume Summary</h3>
                        </div>
                    </div>
                </template>

                <div class="stats-grid">
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
            </Card>

            <Card v-if="showImportSecondaryPanels" class="resume-card resume-card--queue" variant="job">
                <template #header>
                    <div class="panel-header panel-header--stacked">
                        <div>
                            <p class="panel-eyebrow">Insights</p>
                            <h3>Parse Queue</h3>
                            <p class="panel-copy">Track queue load, method-level activity, and your environment-scoped parse position in real time.</p>
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
                </template>

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
                                {{ parseMethodTagLabel(queueStatus.current_user?.focus_method || parseMethod || 'local') }} · {{ queueEnvironmentLabel }} scope
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
                        Active job: {{ parseMethodTagLabel(queueStatus.current_user?.latest_active_job_method) }} · {{ queueStatus.current_user?.latest_active_job_status }} · {{ queueEnvironmentLabel }}
                    </p>

                    <details class="queue-details">
                        <summary>Queue details</summary>
                        <div class="queue-details-body">
                            <p class="queue-details-line">Worker mode: {{ queueStatus.worker_status?.mode || 'unknown' }}</p>
                            <p class="queue-details-line" v-if="queueStatus.current_user?.position_scope_label">Position scope: {{ queueStatus.current_user.position_scope_label }}</p>
                            <p class="queue-details-line" v-if="queueStatus.queue_namespace">Queue namespace: {{ queueStatus.queue_namespace }}</p>
                            <p class="queue-details-line" v-if="queueStatus.local_queue_note">{{ queueStatus.local_queue_note }}</p>
                            <p class="queue-details-line" v-if="queueStatus.cloud_behavior?.description">{{ queueStatus.cloud_behavior.description }}</p>
                            <p class="queue-details-line" v-if="queueStatus.pipeline_availability?.cloud?.message">{{ queueStatus.pipeline_availability.cloud.message }}</p>
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
            </Card>

        </div><!-- /tab imported -->


        <!-- ════════════════════════════════════════════════════
             TAB 2 — Applicant Information
        ═════════════════════════════════════════════════════ -->
        <div v-if="activeTab === 'applicant'" class="dashboard dashboard--applicant">

            <Card class="resume-card resume-card--profile-bar dashboard-span-full" variant="job">
                <template #header>
                    <div class="panel-header">
                        <div>
                            <p class="panel-eyebrow">Profiles</p>
                            <h3>Applicant Profiles</h3>
                        </div>
                        <span class="panel-badge">{{ profiles.length }} saved</span>
                    </div>
                </template>

                <p class="profile-switcher-copy">Switch the active profile or create a new one before editing the sections below.</p>
                <div class="autosave-status-row">
                    <p class="autosave-hint">Double-click text fields to edit. Dropdowns autosave as soon as you choose an option.</p>
                    <div
                        v-if="applicantSavingField || saveStatus.message"
                        :class="[
                            'save-feedback',
                            applicantSavingField ? 'is-saving' : saveStatus.type === 'success' ? 'is-success' : 'is-error'
                        ]"
                    >
                        {{ applicantSavingField ? 'Saving changes…' : saveStatus.message }}
                    </div>
                </div>

                <div v-if="profilesLoading" class="loading-row profile-loading-row">
                    <div class="spinner"></div> Loading profiles…
                </div>

                <div v-else-if="profiles.length > 0" class="profile-switcher">
                    <div class="profile-switcher-row">
                        <label class="profile-switcher-label">Active Profile:</label>
                        <select
                            id="resume-active-profile"
                            name="active_profile"
                            class="profile-select"
                            autocomplete="off"
                            :value="activeProfileId"
                            @change="switchProfile(Number($event.target.value))"
                        >
                            <option v-for="p in profiles" :key="p.id" :value="p.id">
                                {{ p.name }}{{ p.is_active ? ' (active)' : '' }}
                            </option>
                        </select>
                        <button class="btn-secondary btn-compact" @click="showNewProfileInput = !showNewProfileInput" title="New profile">+</button>
                        <button
                            v-if="profiles.length > 1 && Number(activeProfileId) > 0"
                            class="btn-secondary btn-compact delete-profile-btn"
                            @click="deleteProfile(activeProfileId)"
                            title="Delete current profile"
                        >Delete</button>
                    </div>
                    <div v-if="showNewProfileInput" class="new-profile-row">
                        <input
                            id="resume-new-profile-name"
                            name="new_profile_name"
                            v-model="newProfileName"
                            type="text"
                            autocomplete="off"
                            placeholder="New profile name…"
                            class="new-profile-input"
                            @keyup.enter="createNewProfile"
                        />
                        <button class="btn-primary btn-compact" @click="createNewProfile" :disabled="!newProfileName.trim()">Create</button>
                        <button class="btn-secondary btn-compact" @click="showNewProfileInput = false">Cancel</button>
                    </div>
                </div>

                <p v-else class="not-parsed-message">Preparing your applicant profile…</p>
            </Card>

            <Card class="resume-card resume-section resume-section--summary dashboard-span-2" variant="job">
                <template #header><h3>Professional Summary</h3></template>
                <div
                    :class="['field-group', applicantFieldGroupClass('summary')]"
                    @dblclick="unlockApplicantField('summary', 'resume-professional-summary')"
                    title="Double-click to edit"
                >
                    <label>Summary</label>
                    <textarea
                        id="resume-professional-summary"
                        name="professional_summary"
                        autocomplete="off"
                        v-model="summary"
                        class="textarea-summary"
                        :readonly="isApplicantFieldLocked('summary')"
                        @blur="handleApplicantFieldBlur('summary')"
                        placeholder="Brief professional summary highlighting your key skills and experience…"
                    ></textarea>
                </div>
            </Card>

            <Card class="resume-card resume-section resume-section--personal" variant="job">
                <template #header><h3>Personal Information</h3></template>
                <div class="appinfo-grid">
                    <div :class="['field-group', applicantFieldGroupClass('firstName')]" @dblclick="unlockApplicantField('firstName', 'resume-first-name')" title="Double-click to edit">
                        <label>First Name</label>
                        <input id="resume-first-name" type="text" name="first_name" autocomplete="off" v-model="firstName" :readonly="isApplicantFieldLocked('firstName')" @blur="handleApplicantFieldBlur('firstName')" placeholder="John">
                    </div>
                    <div :class="['field-group', applicantFieldGroupClass('middleName')]" @dblclick="unlockApplicantField('middleName', 'resume-middle-name')" title="Double-click to edit">
                        <label>Middle Name</label>
                        <input id="resume-middle-name" type="text" name="middle_name" autocomplete="off" v-model="middleName" :readonly="isApplicantFieldLocked('middleName')" @blur="handleApplicantFieldBlur('middleName')" placeholder="A.">
                    </div>
                    <div :class="['field-group', applicantFieldGroupClass('lastName')]" @dblclick="unlockApplicantField('lastName', 'resume-last-name')" title="Double-click to edit">
                        <label>Last Name</label>
                        <input id="resume-last-name" type="text" name="last_name" autocomplete="off" v-model="lastName" :readonly="isApplicantFieldLocked('lastName')" @blur="handleApplicantFieldBlur('lastName')" placeholder="Doe">
                    </div>
                    <div :class="['field-group', applicantFieldGroupClass('fullLegalName')]" @dblclick="unlockApplicantField('fullLegalName', 'resume-full-legal-name')" title="Double-click to edit">
                        <label>Full Legal Name</label>
                        <input id="resume-full-legal-name" type="text" name="full_legal_name" autocomplete="off" v-model="fullLegalName" :readonly="isApplicantFieldLocked('fullLegalName')" @blur="handleApplicantFieldBlur('fullLegalName')" placeholder="John Adam Doe">
                    </div>
                    <div :class="['field-group', applicantFieldGroupClass('preferredName')]" @dblclick="unlockApplicantField('preferredName', 'resume-preferred-name')" title="Double-click to edit">
                        <label>Preferred Name</label>
                        <input id="resume-preferred-name" type="text" name="preferred_name" autocomplete="off" v-model="preferredName" :readonly="isApplicantFieldLocked('preferredName')" @blur="handleApplicantFieldBlur('preferredName')" placeholder="Johnny">
                    </div>
                    <div :class="['field-group', applicantFieldGroupClass('suffix')]" @dblclick="unlockApplicantField('suffix', 'resume-suffix')" title="Double-click to edit">
                        <label>Suffix</label>
                        <input id="resume-suffix" type="text" name="suffix" autocomplete="off" v-model="suffix" :readonly="isApplicantFieldLocked('suffix')" @blur="handleApplicantFieldBlur('suffix')" placeholder="Jr">
                    </div>
                    <div :class="['field-group', applicantFieldGroupClass('appEmail')]" @dblclick="unlockApplicantField('appEmail', 'resume-email')" title="Double-click to edit">
                        <label>Email</label>
                        <input id="resume-email" type="email" name="email" autocomplete="off" autocapitalize="none" autocorrect="off" spellcheck="false" v-model="appEmail" :readonly="isApplicantFieldLocked('appEmail')" @blur="handleApplicantFieldBlur('appEmail')" placeholder="john.doe@email.com">
                    </div>
                    <div :class="['field-group', applicantFieldGroupClass('phone')]" @dblclick="unlockApplicantField('phone', 'resume-phone')" title="Double-click to edit">
                        <label>Phone</label>
                        <input id="resume-phone" type="tel" name="phone" autocomplete="off" v-model="phone" :readonly="isApplicantFieldLocked('phone')" @blur="handleApplicantFieldBlur('phone')" placeholder="(555) 123-4567">
                    </div>
                    <div :class="['field-group', applicantFieldGroupClass('linkedin')]" @dblclick="unlockApplicantField('linkedin', 'resume-linkedin')" title="Double-click to edit">
                        <label>LinkedIn URL</label>
                        <input id="resume-linkedin" type="url" name="linkedin_url" autocomplete="off" autocapitalize="none" autocorrect="off" spellcheck="false" v-model="linkedin" :readonly="isApplicantFieldLocked('linkedin')" @blur="handleApplicantFieldBlur('linkedin')" placeholder="linkedin.com/in/johndoe">
                    </div>
                    <div :class="['field-group', applicantFieldGroupClass('portfolio')]" @dblclick="unlockApplicantField('portfolio', 'resume-portfolio')" title="Double-click to edit">
                        <label>Portfolio/Website</label>
                        <input id="resume-portfolio" type="url" name="portfolio_url" autocomplete="off" autocapitalize="none" autocorrect="off" spellcheck="false" v-model="portfolio" :readonly="isApplicantFieldLocked('portfolio')" @blur="handleApplicantFieldBlur('portfolio')" placeholder="johndoe.com">
                    </div>
                </div>
            </Card>

            <Card class="resume-card resume-section resume-section--address" variant="job">
                <template #header><h3>Address</h3></template>
                <div :class="['field-group', 'field-group-spaced', applicantFieldGroupClass('streetAddress')]" @dblclick="unlockApplicantField('streetAddress', 'resume-street-address')" title="Double-click to edit">
                    <label>Street Address</label>
                    <input id="resume-street-address" type="text" name="street_address" autocomplete="off" v-model="streetAddress" :readonly="isApplicantFieldLocked('streetAddress')" @blur="handleApplicantFieldBlur('streetAddress')" placeholder="123 Main Street">
                </div>
                <div class="appinfo-3col">
                    <div :class="['field-group', applicantFieldGroupClass('city')]" @dblclick="unlockApplicantField('city', 'resume-city')" title="Double-click to edit">
                        <label>City</label>
                        <input id="resume-city" type="text" name="city" autocomplete="off" v-model="city" :readonly="isApplicantFieldLocked('city')" @blur="handleApplicantFieldBlur('city')" placeholder="San Francisco">
                    </div>
                    <div :class="['field-group', applicantFieldGroupClass('appState')]" @dblclick="unlockApplicantField('appState', 'resume-state')" title="Double-click to edit">
                        <label>State</label>
                        <input id="resume-state" type="text" name="state" autocomplete="off" v-model="appState" :readonly="isApplicantFieldLocked('appState')" @blur="handleApplicantFieldBlur('appState')" placeholder="CA">
                    </div>
                    <div :class="['field-group', applicantFieldGroupClass('zip')]" @dblclick="unlockApplicantField('zip', 'resume-zip')" title="Double-click to edit">
                        <label>ZIP Code</label>
                        <input id="resume-zip" type="text" name="postal_code" autocomplete="off" inputmode="numeric" v-model="zip" :readonly="isApplicantFieldLocked('zip')" @blur="handleApplicantFieldBlur('zip')" placeholder="94105">
                    </div>
                </div>
            </Card>

            <Card class="resume-card resume-section resume-section--skills dashboard-span-2" variant="job">
                <template #header><h3>Skills and Certifications</h3></template>
                <div :class="['field-group', 'field-group-spaced', applicantFieldGroupClass('skillsText')]" @dblclick="unlockApplicantField('skillsText', 'resume-skills')" title="Double-click to edit">
                    <label>Skills (comma-separated)</label>
                    <textarea id="resume-skills" name="skills_text" autocomplete="off" v-model="skillsText" :readonly="isApplicantFieldLocked('skillsText')" @blur="handleApplicantFieldBlur('skillsText')" placeholder="Python, SQL, FastAPI, Vue.js, Docker"></textarea>
                </div>
                <div :class="['field-group', 'field-group-spaced', applicantFieldGroupClass('certificationsText')]" @dblclick="unlockApplicantField('certificationsText', 'resume-certifications')" title="Double-click to edit">
                    <label>Certifications and Licenses</label>
                    <textarea id="resume-certifications" name="certifications_text" autocomplete="off" v-model="certificationsText" :readonly="isApplicantFieldLocked('certificationsText')" @blur="handleApplicantFieldBlur('certificationsText')" placeholder="AWS Certified Cloud Practitioner - Amazon - 2025"></textarea>
                </div>
                <div :class="['field-group', applicantFieldGroupClass('professionalLinksText')]" @dblclick="unlockApplicantField('professionalLinksText', 'resume-professional-links')" title="Double-click to edit">
                    <label>Professional Links</label>
                    <textarea id="resume-professional-links" name="professional_links_text" autocomplete="off" v-model="professionalLinksText" :readonly="isApplicantFieldLocked('professionalLinksText')" @blur="handleApplicantFieldBlur('professionalLinksText')" placeholder="LinkedIn: https://...&#10;GitHub: https://...&#10;Portfolio: https://..."></textarea>
                </div>
            </Card>

            <Card class="resume-card resume-section resume-section--authorization" variant="job">
                <template #header><h3>Work Authorization</h3></template>
                <div class="appinfo-grid">
                    <div :class="['field-group', 'field-group--select']" title="Choose an option to autosave">
                        <label>Authorization Status</label>
                        <select id="resume-work-authorization" name="authorization_status" autocomplete="off" v-model="workAuth" :disabled="working" @change="handleApplicantSelectChange('workAuth')">
                            <option value="">Select…</option>
                            <option>US Citizen</option>
                            <option>Green Card</option>
                            <option>H1-B</option>
                            <option>OPT/CPT</option>
                            <option>Other</option>
                            <option>Require Sponsorship</option>
                        </select>
                    </div>
                    <div :class="['field-group', 'field-group--select']" title="Choose an option to autosave">
                        <label>Requires Sponsorship?</label>
                        <select id="resume-requires-sponsorship" name="requires_sponsorship" autocomplete="off" v-model="requiresSponsorship" :disabled="working" @change="handleApplicantSelectChange('requiresSponsorship')">
                            <option value="">Select…</option>
                            <option>Yes</option>
                            <option>No</option>
                            <option>In the future</option>
                        </select>
                    </div>
                </div>
            </Card>

            <Card class="resume-card resume-section resume-section--experience" variant="job">
                <template #header><h3>Current Experience</h3></template>
                <div class="appinfo-grid">
                    <div :class="['field-group', applicantFieldGroupClass('yearsExperience')]" @dblclick="unlockApplicantField('yearsExperience', 'resume-years-experience')" title="Double-click to edit">
                        <label>Years of Experience</label>
                        <input id="resume-years-experience" type="text" name="years_experience" inputmode="numeric" autocomplete="off" v-model="yearsExperience" :readonly="isApplicantFieldLocked('yearsExperience')" @blur="handleApplicantFieldBlur('yearsExperience')" placeholder="2">
                    </div>
                    <div :class="['field-group', applicantFieldGroupClass('jobTitle')]" @dblclick="unlockApplicantField('jobTitle', 'resume-job-title')" title="Double-click to edit">
                        <label>Current / Most Recent Job Title</label>
                        <input id="resume-job-title" type="text" name="job_title" autocomplete="off" v-model="jobTitle" :readonly="isApplicantFieldLocked('jobTitle')" @blur="handleApplicantFieldBlur('jobTitle')" placeholder="Software Engineer Intern">
                    </div>
                </div>
            </Card>

            <Card class="resume-card resume-section resume-section--education" variant="job">
                <template #header><h3>Education</h3></template>
                <div class="appinfo-grid">
                    <div :class="['field-group', applicantFieldGroupClass('degree')]" @dblclick="unlockApplicantField('degree', 'resume-degree')" title="Double-click to edit">
                        <label>Degree</label>
                        <input id="resume-degree" type="text" name="degree" autocomplete="off" v-model="degree" :readonly="isApplicantFieldLocked('degree')" @blur="handleApplicantFieldBlur('degree')" placeholder="Bachelor of Science">
                    </div>
                    <div :class="['field-group', applicantFieldGroupClass('major')]" @dblclick="unlockApplicantField('major', 'resume-major')" title="Double-click to edit">
                        <label>Major / Field of Study</label>
                        <input id="resume-major" type="text" name="major" autocomplete="off" v-model="major" :readonly="isApplicantFieldLocked('major')" @blur="handleApplicantFieldBlur('major')" placeholder="Computer Science">
                    </div>
                    <div :class="['field-group', 'appinfo-full', applicantFieldGroupClass('university')]" @dblclick="unlockApplicantField('university', 'resume-university')" title="Double-click to edit">
                        <label>University</label>
                        <input id="resume-university" type="text" name="university" autocomplete="off" v-model="university" :readonly="isApplicantFieldLocked('university')" @blur="handleApplicantFieldBlur('university')" placeholder="University of Alabama in Huntsville">
                    </div>
                    <div :class="['field-group', applicantFieldGroupClass('gradYear')]" @dblclick="unlockApplicantField('gradYear', 'resume-graduation-year')" title="Double-click to edit">
                        <label>Graduation Year</label>
                        <input id="resume-graduation-year" type="text" name="graduation_year" inputmode="numeric" autocomplete="off" v-model="gradYear" :readonly="isApplicantFieldLocked('gradYear')" @blur="handleApplicantFieldBlur('gradYear')" placeholder="2026">
                    </div>
                    <div :class="['field-group', applicantFieldGroupClass('gpa')]" @dblclick="unlockApplicantField('gpa', 'resume-gpa')" title="Double-click to edit">
                        <label>GPA (optional)</label>
                        <input id="resume-gpa" type="text" name="gpa" inputmode="decimal" autocomplete="off" v-model="gpa" :readonly="isApplicantFieldLocked('gpa')" @blur="handleApplicantFieldBlur('gpa')" placeholder="3.8">
                    </div>
                </div>
            </Card>

            <Card class="resume-card resume-section resume-section--education-history dashboard-span-2" variant="job">
                <template #header><h3>Education History (Additional Entries)</h3></template>
                <div :class="['field-group', applicantFieldGroupClass('educationHistoryText')]" @dblclick="unlockApplicantField('educationHistoryText', 'resume-education-history')" title="Double-click to edit">
                    <label>Education History</label>
                    <textarea
                        id="resume-education-history"
                        name="education_history_text"
                        autocomplete="off"
                        class="textarea-tall"
                        v-model="educationHistoryText"
                        :readonly="isApplicantFieldLocked('educationHistoryText')"
                        @blur="handleApplicantFieldBlur('educationHistoryText')"
                        placeholder="School | Degree | Field | Start Date | End Date&#10;Example University | B.S. | Computer Science | August 2022 | May 2026"
                    ></textarea>
                </div>
            </Card>

            <Card class="resume-card resume-section resume-section--employment-history dashboard-span-2" variant="job">
                <template #header><h3>Employment History (Additional Entries)</h3></template>
                <div :class="['field-group', applicantFieldGroupClass('employmentHistoryText')]" @dblclick="unlockApplicantField('employmentHistoryText', 'resume-employment-history')" title="Double-click to edit">
                    <label>Employment History</label>
                    <textarea
                        id="resume-employment-history"
                        name="employment_history_text"
                        autocomplete="off"
                        class="textarea-tall"
                        v-model="employmentHistoryText"
                        :readonly="isApplicantFieldLocked('employmentHistoryText')"
                        @blur="handleApplicantFieldBlur('employmentHistoryText')"
                        placeholder="Company | Title | Location | Start Date | End Date&#10;Tech Corp | Software Engineer Intern | Boston, MA | June 2024 | August 2024"
                    ></textarea>
                </div>
            </Card>

            <Card class="resume-card resume-section resume-section--demographics" variant="job">
                <template #header><h3>Demographics (Optional)</h3></template>
                <div class="appinfo-grid">
                    <div :class="['field-group', 'field-group--select']" title="Choose an option to autosave">
                        <label>Gender Identity (Optional)</label>
                        <select id="resume-demographic-gender" name="demographic_gender" autocomplete="off" v-model="demographicGender" :disabled="working" @change="handleApplicantSelectChange('demographicGender')">
                            <option value="">Prefer not to answer</option>
                            <option>Female</option>
                            <option>Male</option>
                            <option>Non-binary</option>
                            <option>Another identity</option>
                        </select>
                    </div>
                    <div :class="['field-group', 'field-group--select']" title="Choose an option to autosave">
                        <label>Ethnicity / Race (Optional)</label>
                        <select id="resume-demographic-ethnicity" name="demographic_ethnicity" autocomplete="off" v-model="demographicEthnicity" :disabled="working" @change="handleApplicantSelectChange('demographicEthnicity')">
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
            </Card>

        </div><!-- /tab applicant -->


        <!-- ════════════════════════════════════════════════════
             TAB 3 — Job Application Info (EEO)
        ═════════════════════════════════════════════════════ -->
        <div v-if="activeTab === 'jobinfo'" class="dashboard dashboard--jobinfo">

            <Card class="resume-card resume-card--compliance dashboard-span-full" variant="minimal">
                <template #header>
                    <div class="panel-header">
                        <div>
                            <p class="panel-eyebrow">Disclosures</p>
                            <h3>Mandatory Disclosures</h3>
                        </div>
                    </div>
                </template>

                <div class="eeo-banner">
                    Required: Federal and state laws require employers to collect this information for equal employment
                    opportunity reporting. Your responses are confidential and will not affect your application.
                </div>
                <div class="jobinfo-status-row">
                    <p class="autosave-hint">Selections save automatically when chosen. If you leave this section after making changes, we’ll remind you what changed.</p>
                    <div
                        v-if="jobInfoSaving || jobInfoError || jobInfoSuccess"
                        :class="[
                            'save-feedback',
                            jobInfoSaving ? 'is-saving' : jobInfoError ? 'is-error' : 'is-success'
                        ]"
                    >
                        {{ jobInfoSaving ? 'Saving disclosures…' : (jobInfoError || jobInfoSuccess) }}
                    </div>
                </div>
            </Card>

            <Card class="resume-card resume-card--eeo resume-card--eeo-veteran" variant="job">
                <template #header>
                    <div class="eeo-header-row">
                        <div>
                            <h3>Veteran Status <span class="required-mark">*</span></h3>
                            <p class="eeo-subtitle">Protected veteran status under VEVRAA</p>
                        </div>
                    </div>
                </template>
                <div
                    v-for="opt in veteranOptions"
                    :key="opt"
                    class="option-row"
                    :class="{ selected: veteranStatus === opt }"
                    @click="selectDisclosure('veteranStatus', opt)"
                >
                    <div class="radio-dot"></div>
                    {{ opt }}
                </div>
                <p class="eeo-footnote">
                    Protected veterans include: Disabled veterans, recently separated veterans, active duty wartime
                    or campaign badge veterans, and Armed Forces service medal veterans.
                </p>
            </Card>

            <Card class="resume-card resume-card--eeo resume-card--eeo-disability" variant="job">
                <template #header>
                    <div class="eeo-header-row">
                        <div>
                            <h3>Disability Status <span class="required-mark">*</span></h3>
                            <p class="eeo-subtitle">Voluntary self-identification under Section 503</p>
                        </div>
                    </div>
                </template>
                <div
                    v-for="opt in disabilityOptions"
                    :key="opt"
                    class="option-row"
                    :class="{ selected: disabilityStatus === opt }"
                    @click="selectDisclosure('disabilityStatus', opt)"
                >
                    <div class="radio-dot"></div>
                    {{ opt }}
                </div>
            </Card>

            <Card class="resume-card resume-card--eeo resume-card--eeo-california" variant="job">
                <template #header>
                    <div class="eeo-header-row">
                        <div>
                            <h3>California Resident <span class="required-mark">*</span></h3>
                            <p class="eeo-subtitle">Required for CCPA compliance</p>
                        </div>
                    </div>
                </template>
                <div
                    v-for="opt in californiaOptions"
                    :key="opt"
                    class="option-row"
                    :class="{ selected: californiaResident === opt }"
                    @click="selectDisclosure('californiaResident', opt)"
                >
                    <div class="radio-dot"></div>
                    {{ opt }}
                </div>
            </Card>

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
                                    <p>
                                        <a
                                            v-if="emailHref(viewingResume.structured_data.personal_info.email)"
                                            class="contact-link"
                                            :href="emailHref(viewingResume.structured_data.personal_info.email)"
                                        >
                                            {{ displayValue(viewingResume.structured_data.personal_info.email) }}
                                        </a>
                                        <span v-else>{{ displayValue(viewingResume.structured_data.personal_info.email) }}</span>
                                    </p>
                                </div>
                                <div class="view-field">
                                    <label>Phone</label>
                                    <p class="contact-line">
                                        <span
                                            v-if="phoneCountryBadge(viewingResume.structured_data.personal_info.phone)"
                                            class="phone-country-badge"
                                            :title="phoneCountryBadge(viewingResume.structured_data.personal_info.phone).label"
                                        >
                                            {{ phoneCountryBadge(viewingResume.structured_data.personal_info.phone).code }}
                                        </span>
                                        <a
                                            v-if="phoneHref(viewingResume.structured_data.personal_info.phone)"
                                            class="contact-link"
                                            :href="phoneHref(viewingResume.structured_data.personal_info.phone)"
                                        >
                                            {{ displayValue(viewingResume.structured_data.personal_info.phone) }}
                                        </a>
                                        <span v-else>{{ displayValue(viewingResume.structured_data.personal_info.phone) }}</span>
                                    </p>
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

        <ResumeReviewModal
            v-if="showReviewModal && reviewResumeId"
            :resume-id="reviewResumeId"
            :resume-name="reviewResumeName"
            :profiles="profiles"
            :active-profile-id="activeProfileId"
            @close="closeReviewModal"
            @applied="handleReviewApplied"
        />

        <ConfirmModal
            v-if="jobInfoConfirmVisible"
            title="Leave Mandatory Disclosures?"
            :message="jobInfoLeaveConfirmMessage"
            cancel-text="Stay Here"
            confirm-text="Leave Section"
            @cancel="cancelJobInfoLeave"
            @confirm="confirmJobInfoLeave"
        />

        <div v-if="showLibraryModal" class="modal-overlay" @click.self="showLibraryModal = false">
            <div class="modal-box library-modal-box" v-draggable-modal="{ handle: '.modal-drag-header' }">
                <div class="modal-drag-header library-modal-header">
                    <div>
                        <h2>Imported Resume Library</h2>
                        <p class="subtitle">Browse all imported resumes in one place without stretching the main page layout.</p>
                    </div>
                    <div class="library-header-actions">
                        <label v-if="resumes.length" class="sort-control">
                            <span>Sort</span>
                            <select v-model="resumeSort" name="resume_sort_modal" autocomplete="off">
                                <option value="newest">Newest first</option>
                                <option value="oldest">Oldest first</option>
                                <option value="name-asc">File name A-Z</option>
                                <option value="name-desc">File name Z-A</option>
                            </select>
                        </label>
                        <button class="btn-secondary btn-compact" @click="showLibraryModal = false">Close</button>
                    </div>
                </div>

                <div v-if="resumesLoading" class="loading-row">
                    <div class="spinner"></div> Loading resumes…
                </div>

                <div v-else-if="resumesError" class="upload-error">{{ resumesError }}</div>

                <div v-else-if="sortedResumes.length" class="resume-list resume-list--modal">
                    <div v-for="r in sortedResumes" :key="`modal-${r.id}`" class="resume-list-item">
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
                            <button v-if="canReviewResume(r)" title="Review parsed data before profile fill" class="review-btn" @click="openReviewModal(r)">Review</button>
                            <button title="View parsed data" @click="viewResume(r.id)">View</button>
                            <button
                                title="Re-parse this resume"
                                :disabled="isReparseBusy(r.id)"
                                @click="startReparse(r)"
                            >
                                {{ isReparseBusy(r.id) ? 'Re-parsing…' : 'Re-parse' }}
                            </button>
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

                <div v-else class="empty-state">
                    <p>No resumes yet. Import a PDF to get started.</p>
                </div>
            </div>
        </div>

    </div><!-- /.page -->
</template>


<script>
import Card from '../components/Card.vue'
import ConfirmModal from '../components/ConfirmModal.vue'
import ResumeReviewModal from '../components/ResumeReviewModal.vue'
import { authedFetch, getCurrentUser, setCurrentUser } from '../lib/auth.js'
import { publishCurrentPageDiagnostics, clearCurrentPageDiagnostics } from '../lib/debugDiagnostics'
import { assertValidEmail, buildMailtoHref, buildPhoneHref, inferPhoneCountry, normalizePhone } from '../lib/validation.js'
import { showToast } from '../services/toastService.js'

const APPINFO_KEY = 'uah_applicant_info'

export default {
    name: 'Resumes',
    components: {
        Card,
        ConfirmModal,
        ResumeReviewModal,
    },

    data() {
        return {
            activeTab: 'imported',

            // ── Imported Resumes tab ────────────────────────
            resumes: [],
            resumesLoading: false,
            resumesError: null,
            deletingId: null,
            showLibraryModal: false,
            resumeSort: 'newest',

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
            parseResumeId: null,
            reparseBusyId: null,

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
            showReviewModal: false,
            reviewResumeId: null,
            reviewResumeName: '',

            // Parse details popup
            showPipelineDetails: false,

            // ── Applicant Information tab ───────────────────
            currentUser: null,
            profiles: [],
            activeProfileId: null,
            profilesLoading: false,
            firstName: '',
            middleName: '',
            lastName: '',
            fullLegalName: '',
            preferredName: '',
            suffix: '',
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
            applicantEditingField: '',
            applicantSavingField: '',
            lastApplicantSavedSignature: '',
            loadedEducationHistoryText: '',
            loadedEmploymentHistoryText: '',
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
            jobInfoSaving: false,
            jobInfoSessionBaseline: {
                veteranStatus: '',
                disabilityStatus: '',
                californiaResident: '',
            },
            jobInfoChangedFields: [],
            jobInfoConfirmVisible: false,
            pendingTabTarget: '',
            pendingRouteTarget: '',
            bypassJobInfoLeaveConfirm: false,
            jobInfoError: '',
            jobInfoSuccess: '',
            _jobInfoTimer: null,
        }
    },

    computed: {
        activeTabSummary() {
            const map = {
                imported: 'Import, parse, and review resume readiness in a layout that matches the rest of UAH.',
                applicant: 'Keep reusable applicant profile data organized for portal autofill and resume-driven updates.',
                jobinfo: 'Review and confirm your mandatory disclosures with instant autosave feedback.',
            }
            return map[this.activeTab] || 'Manage UAH resumes and application information.'
        },
        jobInfoLeaveConfirmMessage() {
            const changed = this.jobInfoChangedFields
                .map((field) => this.jobInfoFieldLabel(field))
                .join(', ')
            if (!changed) {
                return 'Your mandatory disclosures were autosaved. Leave this section?'
            }
            return `You changed ${changed}. These disclosures were autosaved. Leave this section?`
        },
        portalReadyCount() {
            return this.resumes.filter(r => r.portal_ready).length
        },
        sortedResumes() {
            const resumes = [...this.resumes]

            if (this.resumeSort === 'oldest') {
                return resumes.sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
            }

            if (this.resumeSort === 'name-asc') {
                return resumes.sort((a, b) => (a.file_name || '').localeCompare(b.file_name || '', undefined, { sensitivity: 'base' }))
            }

            if (this.resumeSort === 'name-desc') {
                return resumes.sort((a, b) => (b.file_name || '').localeCompare(a.file_name || '', undefined, { sensitivity: 'base' }))
            }

            return resumes.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
        },
        libraryPreviewResumes() {
            return this.sortedResumes.slice(0, 3)
        },
        libraryHasOverflow() {
            return this.resumes.length > 3
        },
        latestUploadDate() {
            if (!this.resumes.length) return '—'
            const latest = [...this.resumes].sort((a, b) => new Date(b.created_at) - new Date(a.created_at))[0]
            return latest ? this.formatDate(latest.created_at) : '—'
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
            if (activeMethod === 'cloud' && this.parseStageLabel && this.parseStageLabel.toLowerCase().includes('retrying')) {
                return 'Cloud AI is throttled right now. UAH is retrying with provider-aware backoff…'
            }
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
        pipelineAvailability() {
            return this.queueStatus?.pipeline_availability || null
        },
        isLocalParseMethodAvailable() {
            return this.pipelineAvailability?.local?.available !== false
        },
        localParseMethodUnavailableMessage() {
            if (this.isLocalParseMethodAvailable) return ''
            const message = this.pipelineAvailability?.local?.message
            if (typeof message === 'string' && message.trim()) return message.trim()
            return 'Local AI is unavailable right now.'
        },
        selectedParseMethodDescription() {
            const map = {
                local: 'Local AI uses UAH local OCR + local parsing with isolated queue visibility.',
                cloud: 'Cloud AI uses web ZAI OCR and GLM-4.7-Flash with concurrency-limited throughput.',
                rules: 'Rules-based parsing is deterministic from embedded PDF text only (no OCR fallback).',
            }
            return map[this.parseMethod] || ''
        },
        showImportSecondaryPanels() {
            return this.uploadStep === 'select' && !this.uploading
        },
        canViewGlobalQueue() {
            return !!this.queueStatus?.can_view_global
        },
        queueEnvironmentLabel() {
            const explicit = (this.queueStatus?.environment_label || '').trim()
            if (explicit) return explicit

            const env = (this.queueStatus?.environment || '').trim().toLowerCase()
            if (env === 'dev' || env === 'development' || env === 'local') return 'Dev'
            if (env === 'beta' || env === 'staging') return 'Beta'
            if (env === 'prod' || env === 'production') return 'Prod'

            const host = (window?.location?.hostname || '').toLowerCase()
            if (host.startsWith('beta.')) return 'Beta'
            if (host.startsWith('dev.')) return 'Dev'
            return 'Current Environment'
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

    beforeRouteLeave(to) {
        if (this.bypassJobInfoLeaveConfirm) {
            this.bypassJobInfoLeaveConfirm = false
            return true
        }
        if (this.shouldConfirmJobInfoLeave()) {
            this.openJobInfoLeaveConfirm({ routeTarget: to?.fullPath || '/home' })
            return false
        }
        return true
    },

    methods: {
        requestTabChange(tab) {
            if (tab === this.activeTab) return
            if (this.activeTab === 'jobinfo' && tab !== 'jobinfo' && this.shouldConfirmJobInfoLeave()) {
                this.openJobInfoLeaveConfirm({ tabTarget: tab })
                return
            }
            this.setActiveTab(tab)
        },
        setActiveTab(tab) {
            this.activeTab = tab
            if (tab === 'jobinfo') {
                this.startJobInfoSession()
            }
            this.publishDebugState(`tab-${tab}`)
        },
        isApplicantFieldLocked(fieldKey) {
            return this.applicantEditingField !== fieldKey
        },
        applicantFieldGroupClass(fieldKey) {
            return {
                'field-group--locked': this.isApplicantFieldLocked(fieldKey),
                'field-group--editing': this.applicantEditingField === fieldKey,
            }
        },
        unlockApplicantField(fieldKey, controlId) {
            if (this.working) return
            this.applicantEditingField = fieldKey
            this.$nextTick(() => {
                const control = document.getElementById(controlId)
                control?.focus?.()
                if (control && typeof control.select === 'function' && control.tagName !== 'SELECT') {
                    control.select()
                }
            })
        },
        async handleApplicantFieldBlur(fieldKey) {
            if (this.applicantEditingField !== fieldKey) return
            if (fieldKey === 'appEmail') {
                this.onApplicantEmailBlur()
            }
            if (fieldKey === 'phone') {
                this.onApplicantPhoneBlur()
            }
            const saved = await this.saveApplicantInfo({
                successMessage: 'Changes autosaved.',
                showToastOnSuccess: true,
                showToastOnError: true,
                isAutosave: true,
            })
            if (saved) {
                this.applicantEditingField = ''
                this.applicantSavingField = ''
            }
        },
        async handleApplicantSelectChange(fieldKey) {
            this.applicantSavingField = fieldKey
            const saved = await this.saveApplicantInfo({
                successMessage: 'Changes autosaved.',
                showToastOnSuccess: true,
                showToastOnError: true,
                isAutosave: true,
                savingFieldKey: fieldKey,
            })
            if (saved) {
                this.applicantSavingField = ''
            }
        },
        serializeApplicantPayload(payload = this.buildProfilePayload()) {
            return JSON.stringify(payload)
        },
        normalizedTextValue(value) {
            return String(value || '').trim()
        },
        syncApplicantSavedSignature() {
            this.lastApplicantSavedSignature = this.serializeApplicantPayload()
        },
        normalizeApplicantContactFields() {
            if (this.appEmail) {
                this.appEmail = assertValidEmail(this.appEmail)
            }
            this.phone = normalizePhone(this.phone)
        },
        onApplicantEmailBlur() {
            if (!this.appEmail) return
            try {
                this.appEmail = assertValidEmail(this.appEmail)
            } catch {
                // Keep user's raw input in place until save validation.
            }
        },
        onApplicantPhoneBlur() {
            if (!this.phone) return
            try {
                this.phone = normalizePhone(this.phone)
            } catch {
                // Keep user's raw input in place until save validation.
            }
        },
        currentJobInfoState() {
            return {
                veteranStatus: this.veteranStatus || '',
                disabilityStatus: this.disabilityStatus || '',
                californiaResident: this.californiaResident || '',
            }
        },
        startJobInfoSession() {
            this.jobInfoError = ''
            this.jobInfoSuccess = ''
            this.jobInfoSessionBaseline = { ...this.currentJobInfoState() }
            this.jobInfoChangedFields = []
        },
        refreshJobInfoChangedFields() {
            const current = this.currentJobInfoState()
            this.jobInfoChangedFields = Object.keys(this.jobInfoSessionBaseline).filter(
                (field) => (current[field] || '') !== (this.jobInfoSessionBaseline[field] || '')
            )
        },
        jobInfoFieldLabel(fieldKey) {
            const labels = {
                veteranStatus: 'Veteran Status',
                disabilityStatus: 'Disability Status',
                californiaResident: 'California Resident',
            }
            return labels[fieldKey] || fieldKey
        },
        shouldConfirmJobInfoLeave() {
            return this.activeTab === 'jobinfo' && this.jobInfoChangedFields.length > 0
        },
        openJobInfoLeaveConfirm({ tabTarget = '', routeTarget = '' } = {}) {
            this.pendingTabTarget = tabTarget
            this.pendingRouteTarget = routeTarget
            this.jobInfoConfirmVisible = true
        },
        cancelJobInfoLeave() {
            this.pendingTabTarget = ''
            this.pendingRouteTarget = ''
            this.jobInfoConfirmVisible = false
        },
        confirmJobInfoLeave() {
            const tabTarget = this.pendingTabTarget
            const routeTarget = this.pendingRouteTarget
            this.cancelJobInfoLeave()
            this.startJobInfoSession()
            if (tabTarget) {
                this.setActiveTab(tabTarget)
                return
            }
            if (routeTarget) {
                this.bypassJobInfoLeaveConfirm = true
                this.$router.push(routeTarget)
            }
        },
        async selectDisclosure(fieldKey, value) {
            if (this[fieldKey] === value) return
            this[fieldKey] = value
            await this.saveJobInfo(fieldKey)
        },
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
        emailHref(value) {
            return buildMailtoHref(this.cleanTextValue(value))
        },
        phoneHref(value) {
            return buildPhoneHref(this.cleanTextValue(value))
        },
        phoneCountryBadge(value) {
            return inferPhoneCountry(this.cleanTextValue(value))
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

        applyQueueStatus(status) {
            this.queueStatus = status

            if (!this.queueStatus?.can_view_global && this.queueScope === 'global') {
                this.queueScope = 'user'
            }

            if (status?.pipeline_availability?.local?.available === false && this.parseMethod === 'local') {
                this.parseMethod = 'cloud'
            }
        },

        async loadQueueStatus() {
            if (this.activeTab !== 'imported') return

            this.queueLoading = true
            this.queueError = null
            try {
                const focusMethod = encodeURIComponent(this.parseJobMethod || this.parseMethod || 'local')
                const res = await authedFetch(`/api/resume/queue/status?scope=${encodeURIComponent(this.queueScope)}&focus_method=${focusMethod}`)
                if (!res.ok) throw new Error(`HTTP ${res.status}`)
                this.applyQueueStatus(await res.json())
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
                showReviewModal: this.showReviewModal,
                viewLoading: this.viewLoading,
                viewingResumeId: this.viewingResume?.id || null,
                reviewResumeId: this.reviewResumeId || null,
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
            if (r?.review_status === 'pending' || (r?.has_review_draft && !r?.review_status)) return 'review-pending'
            if (r.portal_ready) return 'portal-ready'
            if (r.parse_method) return 'needs-fields'
            return 'not-parsed'
        },
        badgeText(r) {
            if (r?.review_status === 'pending' || (r?.has_review_draft && !r?.review_status)) return 'Review Pending'
            if (r.portal_ready) return 'Portal Ready'
            if (r.parse_method) return 'Needs Fields'
            return 'Not Parsed'
        },
        canReviewResume(r) {
            return Boolean(r?.review_status === 'pending' || (r?.has_review_draft && !r?.review_status))
        },

        openReviewModal(resume) {
            const resumeId = typeof resume === 'object' ? resume?.id : resume
            if (!resumeId) return
            const resumeName = typeof resume === 'object' ? resume?.file_name || '' : ''
            this.showLibraryModal = false
            this.closeViewModal()
            this.reviewResumeId = Number(resumeId)
            this.reviewResumeName = resumeName
            this.showReviewModal = true
            this.publishDebugState('review-open')
        },
        closeReviewModal() {
            this.showReviewModal = false
            this.reviewResumeId = null
            this.reviewResumeName = ''
            this.publishDebugState('review-close')
        },
        async handleReviewApplied(result) {
            const profileId = Number(result?.profile_id || 0) || null
            await this.loadResumes()
            await this.refreshProfileList()
            if (profileId) {
                await this.loadProfileData(profileId)
            }
            this.closeReviewModal()
            this.publishDebugState('review-applied')
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
            this.showLibraryModal = false
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
            this.requestTabChange('applicant')
            this.publishDebugState('navigate-to-applicant-from-readiness')
        },

        // ── Inline upload ───────────────────────────────────
        openUploadModal() {
            this.showLibraryModal = false
            this.uploadStep = 'select'
            this.pendingFile = null
            this.parseMethod = this.isLocalParseMethodAvailable ? 'local' : 'cloud'
            this.uploadError = null
            this.isDragOver = false
            this.$nextTick(() => {
                const target = this.$refs.inlineImportSection?.$el || this.$refs.inlineImportSection
                target?.scrollIntoView({ behavior: 'smooth', block: 'start' })
            })
            this.publishDebugState('upload-open')
        },
        resetUploadFlow() {
            this.uploadStep = 'select'
            this.pendingFile = null
            this.uploadError = null
            this.uploading = false
            this.reparseBusyId = null
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
            this.parseResumeId = null
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
        isReparseBusy(resumeId) {
            const id = Number(resumeId || 0)
            if (!id) return false
            return Number(this.reparseBusyId || 0) === id || (Number(this.parseResumeId || 0) === id && Boolean(this.parseJobId))
        },
        async queueParseForResume(resumeId, selectedMethod) {
            const parseRes = await authedFetch(`/api/resume/${resumeId}/parse-async`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ method: selectedMethod }),
            })
            const parseData = await parseRes.json().catch(() => null)
            if (!parseRes.ok) {
                throw new Error(this.apiErrorMessage(parseData, parseRes.status, 'Parse failed'))
            }
            this.parseJobId = parseData.job_id
            this.parseResumeId = Number(resumeId)
            this.parseStatus = 'queued'
            this.parseStageLabel = 'Queued…'
            this.parseError = null
            this.parseJobMethod = selectedMethod
            this.uploadStep = 'parsing'
            this.publishDebugState('parse-started')
            this.pollParseJob()
        },
        async startReparse(resume) {
            const resumeId = Number(resume?.id || resume || 0)
            if (!resumeId || this.parseJobId) return
            const selectedMethod = this.parseMethod === 'local' && !this.isLocalParseMethodAvailable
                ? 'cloud'
                : this.parseMethod
            if (selectedMethod !== this.parseMethod) {
                this.parseMethod = selectedMethod
            }
            this.reparseBusyId = resumeId
            this.uploadError = null
            this.showLibraryModal = false
            try {
                await this.queueParseForResume(resumeId, selectedMethod)
                showToast('Re-parse started. Tracking progress now.', 'success')
            } catch (e) {
                this.uploadError = e.message ?? String(e)
                showToast(this.uploadError || 'Could not start re-parse.', 'error')
                this.uploadStep = 'confirm'
                this.parseJobId = null
                this.parseResumeId = null
                this.parseJobMethod = null
                this.publishDebugState('reparse-error')
            } finally {
                this.reparseBusyId = null
            }
        },
        async doUpload() {
            if (!this.pendingFile || this.uploading) return
            const selectedMethod = this.parseMethod === 'local' && !this.isLocalParseMethodAvailable
                ? 'cloud'
                : this.parseMethod
            if (selectedMethod !== this.parseMethod) {
                this.parseMethod = selectedMethod
            }
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

                const resumeId = uploadData.id
                // 2. Start async parse + switch to progress stage
                await this.queueParseForResume(resumeId, selectedMethod)
                this.uploading = false
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
                    this.applyQueueStatus(job.queue_snapshot)
                }

                this.parseStatus = job.status
                this.parseStageLabel = job.progress_stage || this.parseStageLabel
                this.parseAttempt = job.attempt
                this.parseElapsedSeconds = job.elapsed_seconds
                this.parseQueuePosition = job.queue_position
                this.parseQueueTotal = job.queue_total
                this.parseErrorCode = job.error_code || null

                if (job.status === 'success') {
                    const completedResumeId = this.parseResumeId
                    const effectiveMethod = String(job?.result_summary?.effective_method || '').trim().toLowerCase()
                    const fallbackUsed = job?.result_summary?.fallback_used === true
                    const effectiveMethodLabel = this.parseMethodDisplayName(effectiveMethod)
                    if (fallbackUsed && effectiveMethodLabel) {
                        showToast(`Cloud parse recovered via ${effectiveMethodLabel}. Review the extracted data before filling a profile.`, 'success')
                    } else {
                        showToast('Parse complete. Review the extracted data before filling a profile.', 'success')
                    }
                    this.resetUploadFlow()
                    await this.loadResumes()
                    await this.loadQueueStatus()
                    if (completedResumeId) {
                        const completedResume = this.resumes.find((resume) => Number(resume.id) === Number(completedResumeId))
                        this.openReviewModal(completedResume || completedResumeId)
                    }
                    this.publishDebugState('parse-success')
                    return
                }
                if (job.status === 'failed') {
                    const details = this.describeParseFailure(job)
                    this.uploadError = details
                    showToast('Parse failed. Review the error and retry.', 'error')
                    this.uploadStep = 'confirm'
                    this.parseJobId = null
                    this.parseJobMethod = null
                    this.parseResumeId = null
                    this.publishDebugState('parse-failed')
                    return
                }
                if (job.status === 'cancelled') {
                    showToast('Parse cancelled.', 'success')
                    this.uploadStep = 'confirm'
                    this.parseJobId = null
                    this.parseJobMethod = null
                    this.parseResumeId = null
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
            this.parseResumeId = null
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
                        middle_name: d.middleName || '',
                        full_legal_name: d.fullLegalName || '',
                        preferred_name: d.preferredName || '',
                        suffix: d.suffix || '',
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
                payload.middle_name = payload.middle_name || this.currentUser.middle_name || this.currentUser.middleName || ''
                payload.last_name = payload.last_name || this.currentUser.last_name || this.currentUser.lastName || ''
                payload.full_legal_name = payload.full_legal_name || this.currentUser.full_legal_name || this.currentUser.fullLegalName || ''
                payload.preferred_name = payload.preferred_name || this.currentUser.preferred_name || this.currentUser.preferredName || ''
                payload.suffix = payload.suffix || this.currentUser.suffix || ''
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
            this.applicantEditingField = ''
            this.applicantSavingField = ''
            this.firstName = p.first_name || ''
            this.middleName = p.middle_name || ''
            this.lastName = p.last_name || ''
            this.fullLegalName = p.full_legal_name || ''
            this.preferredName = p.preferred_name || ''
            this.suffix = p.suffix || ''
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
            this.loadedEducationHistoryText = this.educationHistoryText
            this.loadedEmploymentHistoryText = this.employmentHistoryText
            this.demographicGender = p.demographic_gender || ''
            this.demographicEthnicity = p.demographic_ethnicity || ''
            this.veteranStatus = p.veteran_status || ''
            this.disabilityStatus = p.disability_status || ''
            this.californiaResident = p.california_resident || ''
            this.syncApplicantSavedSignature()
            if (this.activeTab === 'jobinfo') {
                this.startJobInfoSession()
            }
        },

        buildProfilePayload() {
            const activeProfile = this.profiles.find((profile) => Number(profile?.id) === Number(this.activeProfileId))
            const payload = {
                name: activeProfile?.name || 'Default',
                first_name: this.firstName, middle_name: this.middleName, last_name: this.lastName,
                full_legal_name: this.fullLegalName, preferred_name: this.preferredName, suffix: this.suffix,
                email: this.appEmail,
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
            if (this.normalizedTextValue(this.educationHistoryText) === this.normalizedTextValue(this.loadedEducationHistoryText)) {
                delete payload.education_history_text
            }
            if (this.normalizedTextValue(this.employmentHistoryText) === this.normalizedTextValue(this.loadedEmploymentHistoryText)) {
                delete payload.employment_history_text
            }
            return payload
        },

        loadApplicantInfoFromLocal() {
            this.currentUser = getCurrentUser()
            this.applicantEditingField = ''
            this.applicantSavingField = ''
            if (this.currentUser) {
                this.firstName = this.currentUser.first_name || this.currentUser.firstName || ''
                this.middleName = this.currentUser.middle_name || this.currentUser.middleName || ''
                this.lastName = this.currentUser.last_name || this.currentUser.lastName || ''
                this.fullLegalName = this.currentUser.full_legal_name || this.currentUser.fullLegalName || ''
                this.preferredName = this.currentUser.preferred_name || this.currentUser.preferredName || ''
                this.suffix = this.currentUser.suffix || ''
                this.appEmail = this.currentUser.email || ''
            }
            try {
                const saved = localStorage.getItem(APPINFO_KEY)
                if (saved) {
                    const d = JSON.parse(saved)
                    this.middleName = d.middleName || this.middleName || ''
                    this.fullLegalName = d.fullLegalName || this.fullLegalName || ''
                    this.preferredName = d.preferredName || this.preferredName || ''
                    this.suffix = d.suffix || this.suffix || ''
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
            this.syncApplicantSavedSignature()
            if (this.activeTab === 'jobinfo') {
                this.startJobInfoSession()
            }
        },

        async switchProfile(profileId) {
            if (profileId === this.activeProfileId) return
            try {
                const res = await authedFetch(`/api/applicant-profile/${profileId}/activate`, { method: 'POST' })
                if (!res.ok) throw new Error(`HTTP ${res.status}`)
                await this.loadProfileData(profileId)
                await this.refreshProfileList()
                showToast('Profile switched.', 'success')
                this.publishDebugState('profile-switched')
            } catch (e) {
                this.saveStatus = { type: 'error', message: 'Failed to switch profile.' }
                showToast('Failed to switch profile.', 'error')
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
                    body: JSON.stringify({ name }),
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
                this.saveStatus = { type: 'success', message: 'Profile created.' }
                showToast('Profile created.', 'success')
            } catch (e) {
                this.saveStatus = { type: 'error', message: e.message || 'Failed to create profile.' }
                showToast(e.message || 'Failed to create profile.', 'error')
            }
        },
        async deleteProfile(profileId) {
            if (this.profiles.length <= 1) {
                this.saveStatus = { type: 'error', message: 'Cannot delete your only profile.' }
                return
            }
            if (Number(profileId) === Number(this.activeProfileId)) {
                alert("Active profile cannot be deleted. Switch profiles first.")
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
                this.saveStatus = { type: 'success', message: 'Profile deleted.' }
                showToast('Profile deleted.', 'success')
                this.publishDebugState('profile-deleted')
            } catch (e) {
                this.saveStatus = { type: 'error', message: 'Failed to delete profile.' }
                showToast('Failed to delete profile.', 'error')
            }
        },

        async saveApplicantInfo(options = {}) {
            const {
                successMessage = 'Information saved.',
                showToastOnSuccess = false,
                showToastOnError = false,
                isAutosave = false,
                savingFieldKey = '',
            } = options
            this.working = true
            this.saveStatus = { type: '', message: '' }
            if (this._saveTimer) clearTimeout(this._saveTimer)
            try {
                this.normalizeApplicantContactFields()
                const payload = this.buildProfilePayload()
                const nextSignature = this.serializeApplicantPayload(payload)
                if (nextSignature === this.lastApplicantSavedSignature) {
                    this.applicantSavingField = ''
                    return true
                }
                if (isAutosave) {
                    this.applicantSavingField = savingFieldKey || this.applicantEditingField
                }
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

                this.syncApplicantSavedSignature()
                this.saveStatus = { type: 'success', message: successMessage }
                if (showToastOnSuccess) {
                    showToast(successMessage, 'success')
                }
                this.publishDebugState('applicant-save-success')
                return true
            } catch (e) {
                if (e.message === 'Session expired' || e.message === 'Not authenticated') {
                    this.$router.push('/login')
                    return false
                }
                this.saveStatus = { type: 'error', message: e.message ?? 'Save failed.' }
                if (showToastOnError) {
                    showToast(this.saveStatus.message, 'error')
                }
                this.publishDebugState('applicant-save-error')
                return false
            } finally {
                this.working = false
                if (this.applicantSavingField || this.saveStatus.message) {
                    this._saveTimer = setTimeout(() => {
                        this.saveStatus = { type: '', message: '' }
                        this.applicantSavingField = ''
                    }, 3500)
                }
            }
        },

        // ── Job Application Info ────────────────────────────
        async saveJobInfo(changedField = '') {
            this.jobInfoError = ''
            this.jobInfoSuccess = ''
            if (this._jobInfoTimer) clearTimeout(this._jobInfoTimer)
            this.jobInfoSaving = true
            try {
                const payload = {
                    veteran_status: this.veteranStatus,
                    disability_status: this.disabilityStatus,
                    california_resident: this.californiaResident,
                }
                if (this.activeProfileId) {
                    const res = await authedFetch(`/api/applicant-profile/${this.activeProfileId}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload),
                    })
                    if (!res.ok) {
                        const data = await res.json().catch(() => null)
                        throw new Error(data?.detail || `HTTP ${res.status}`)
                    }
                } else {
                    const saved = await this.saveApplicantInfo({
                        successMessage: 'Mandatory disclosures autosaved.',
                        showToastOnSuccess: false,
                        showToastOnError: false,
                        isAutosave: true,
                    })
                    if (!saved) throw new Error('Failed to save mandatory disclosures.')
                }
                this.syncApplicantSavedSignature()
                this.refreshJobInfoChangedFields()
                this.jobInfoSuccess = 'Autosaved just now.'
                if (changedField) {
                    showToast(`${this.jobInfoFieldLabel(changedField)} saved.`, 'success')
                }
                this.publishDebugState('jobinfo-save-success')
                this._jobInfoTimer = setTimeout(() => { this.jobInfoSuccess = '' }, 3500)
            } catch (e) {
                this.jobInfoError = e.message || 'Failed to save mandatory disclosures.'
                showToast(this.jobInfoError, 'error')
                this.publishDebugState('jobinfo-save-error')
            } finally {
                this.jobInfoSaving = false
            }
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
                if (detail.code === 'CLOUD_LLM_QUOTA_EXHAUSTED' || detail.code === 'CLOUD_OCR_QUOTA_EXHAUSTED') {
                    return 'Cloud AI quota or usage limits are exhausted right now. Please try again later.'
                }
                if (detail.code === 'CLOUD_LLM_RATE_LIMITED' || detail.code === 'CLOUD_LLM_PROVIDER_BUSY' || detail.code === 'CLOUD_OCR_RATE_LIMITED' || detail.code === 'CLOUD_OCR_PROVIDER_BUSY') {
                    return 'Cloud AI is temporarily rate limited. Please wait a moment and retry.'
                }
                if (typeof detail.message === 'string' && detail.message.trim()) return detail.message
                if (typeof detail.code === 'string' && detail.code.trim()) return `${fallbackLabel}: ${detail.code}`
            }
            return `${fallbackLabel} (HTTP ${status})`
        },
        describeParseFailure(job) {
            const code = String(job?.error_code || '').trim()
            const message = String(job?.error_message || '').trim()
            if (code === 'LLM_EMPTY_RESPONSE') {
                return `[${code}] Cloud AI was reachable, but it returned no structured data for this resume. Retry, or switch pipelines if this keeps happening.`
            }
            if (code === 'CLOUD_LLM_QUOTA_EXHAUSTED' || code === 'CLOUD_OCR_QUOTA_EXHAUSTED') {
                return `[${code}] Cloud AI quota or usage limits are exhausted right now. Please try again later.`
            }
            if (code === 'CLOUD_LLM_RATE_LIMITED' || code === 'CLOUD_LLM_PROVIDER_BUSY' || code === 'CLOUD_OCR_RATE_LIMITED' || code === 'CLOUD_OCR_PROVIDER_BUSY') {
                return `[${code}] Cloud AI capacity is temporarily constrained. UAH retried with backoff and still needs another attempt later.`
            }
            return code ? `[${code}] ${message || 'Parsing failed.'}` : (message || 'Parsing failed.')
        },
        parseMethodDisplayName(method) {
            const normalized = String(method || '').trim().toLowerCase()
            if (normalized === 'cloud') return 'Cloud AI'
            if (normalized === 'local') return 'Local AI'
            if (normalized === 'rules') return 'Rules-based parsing'
            return ''
        },
    },
}
</script>

<style scoped src="./css/Resumes.css"></style>
