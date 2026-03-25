<template>
    <div class="page">

        <!-- ── Greeting ──────────────────────────────────────── -->
        <div class="greeting">
            <div class="greeting-left">
                <h1>Resumes</h1>
                <p>Manage your resumes and application information</p>
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
                <p class="subtitle" style="margin-top:-8px; margin-bottom: 12px;">Upload your resume PDF to extract job-application data inline.</p>

                <div
                    v-if="uploadStep === 'select'"
                    class="drop-zone"
                    :class="{ 'drag-over': isDragOver }"
                    @click="triggerFileInput"
                    @dragover.prevent="isDragOver = true"
                    @dragleave="isDragOver = false"
                    @drop.prevent="onFileDrop"
                >
                    <div class="drop-icon">&#128228;</div>
                    <p>Upload your resume</p>
                    <p class="drop-hint">Drag and drop your PDF file here, or click to browse</p>
                    <button class="btn-primary" @click.stop="triggerFileInput">&#128196; Choose PDF File</button>
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
                    <div class="file-preview-row" style="margin-top:6px;">
                        <div class="pdf-icon">PDF</div>
                        <div class="file-info">
                            <p class="file-name">{{ pendingFile.name }}</p>
                            <p class="file-size">{{ formatBytes(pendingFile.size) }}</p>
                        </div>
                        <button class="clear-btn" @click="clearFile" title="Remove file">&#x2715;</button>
                    </div>

                    <div class="import-options" style="margin-top:10px;">
                        <h4>Import Options</h4>
                        <div class="import-option-row">
                            <div class="check-circle">&#10003;</div>
                            <div class="option-text">
                                <strong>Extract contact information</strong>
                                <span>Name, email, phone number, and location</span>
                            </div>
                        </div>
                        <div class="import-option-row">
                            <div class="check-circle">&#10003;</div>
                            <div class="option-text">
                                <strong>Parse education and work history</strong>
                                <span>School and employment details used in applications</span>
                            </div>
                        </div>
                        <div class="import-option-row">
                            <div class="check-circle">&#10003;</div>
                            <div class="option-text">
                                <strong>Identify skills, links, and certifications</strong>
                                <span>Technical skills and profile-ready metadata</span>
                            </div>
                        </div>
                    </div>

                    <div style="margin-top: 8px;">
                        <label style="font-size:0.82rem;font-weight:600;color:#8a94a6;display:block;margin-bottom:6px;">Parse method</label>
                        <div class="method-toggle">
                            <button :class="{ active: parseMethod === 'llm' }" @click="parseMethod = 'llm'">AI (LLM)</button>
                            <button :class="{ active: parseMethod === 'rules' }" @click="parseMethod = 'rules'">Rules-based</button>
                        </div>
                    </div>

                    <div class="modal-actions" style="justify-content:flex-start;">
                        <button class="btn-secondary" @click="clearFile" :disabled="uploading">Choose Different File</button>
                        <button class="btn-primary" @click="doUpload" :disabled="uploading">
                            <span v-if="uploading">
                                <span class="spinner" style="width:14px;height:14px;border-width:2px;display:inline-block;vertical-align:middle;margin-right:6px;"></span>
                                Importing...
                            </span>
                            <span v-else>Import Resume</span>
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
                    <div class="stat-value" style="font-size:1rem; padding-top:4px;">{{ latestUploadDate }}</div>
                </div>
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
                    <span :class="['badge', badgeClass(r)]">{{ badgeText(r) }}</span>
                    <div class="resume-actions">
                        <button title="View parsed data" @click="viewResume(r.id)">&#128065;</button>
                        <button
                            title="Delete resume"
                            class="delete-btn"
                            :class="{ 'confirm-delete': deletingId === r.id }"
                            @click="handleDelete(r.id)"
                        >
                            {{ deletingId === r.id ? 'Confirm?' : '&#128465;' }}
                        </button>
                    </div>
                </div>
            </div>

            <!-- Empty -->
            <div v-else class="resume-list-card">
                <div class="empty-state">
                    <div style="font-size:2rem">&#128196;</div>
                    <p>No resumes yet. Import a PDF to get started.</p>
                </div>
            </div>

        </div><!-- /tab imported -->


        <!-- ════════════════════════════════════════════════════
             TAB 2 — Applicant Information
        ═════════════════════════════════════════════════════ -->
        <div v-if="activeTab === 'applicant'" class="dashboard">

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
                <div class="field-group" style="margin-bottom:14px;">
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
                    <textarea v-model="summary" placeholder="Brief professional summary highlighting your key skills and experience…" style="min-height:110px;"></textarea>
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
                    <div class="field-group" style="grid-column: 1 / -1;">
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
                <div class="field-group" style="margin-bottom:14px;">
                    <label>Skills (comma-separated)</label>
                    <textarea v-model="skillsText" placeholder="Python, SQL, FastAPI, Vue.js, Docker"></textarea>
                </div>
                <div class="field-group" style="margin-bottom:14px;">
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
                        v-model="educationHistoryText"
                        placeholder="School | Degree | Field | Start Date | End Date&#10;Example University | B.S. | Computer Science | August 2022 | May 2026"
                        style="min-height:130px;"
                    ></textarea>
                </div>
            </div>

            <div class="appinfo-card">
                <h3>Employment History (Additional Entries)</h3>
                <div class="field-group">
                    <label>Employment History</label>
                    <textarea
                        v-model="employmentHistoryText"
                        placeholder="Company | Title | Location | Start Date | End Date&#10;Tech Corp | Software Engineer Intern | Boston, MA | June 2024 | August 2024"
                        style="min-height:130px;"
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
                        <h3>Veteran Status <span style="color:#dc2626;">*</span></h3>
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
                        <h3>Disability Status <span style="color:#dc2626;">*</span></h3>
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
                        <h3>California Resident <span style="color:#dc2626;">*</span></h3>
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
        <div v-if="showViewModal" class="modal-overlay" @click.self="showViewModal = false">
            <div class="modal-box view-modal-box" v-draggable-modal="{ handle: '.modal-drag-header' }">
                <div class="modal-drag-header drag-handle" style="display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;">
                    <h2 style="margin:0;">{{ viewingResume ? viewingResume.file_name : 'Resume' }}</h2>
                    <button class="btn-secondary" style="padding:6px 12px;font-size:0.85rem;" @click="showViewModal = false">Close</button>
                </div>

                <div v-if="viewLoading" class="loading-row">
                    <div class="spinner"></div> Loading…
                </div>

                <template v-else-if="viewingResume && viewingResume.structured_data">
                    <span :class="['badge', badgeClass(viewingResume)]" style="align-self:flex-start;">
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
                            <span style="font-size:0.8rem;color:#8a94a6;">{{ portalFilledCount(viewingResume) }}/15 required fields filled</span>
                        </div>
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
                                <p>{{ viewingResume.structured_data.personal_info.email || '—' }}</p>
                            </div>
                            <div class="view-field">
                                <label>Phone</label>
                                <p>{{ viewingResume.structured_data.personal_info.phone || '—' }}</p>
                            </div>
                            <div class="view-field">
                                <label>Location</label>
                                <p>{{ locationStr(viewingResume.structured_data.personal_info) || '—' }}</p>
                            </div>
                            <div v-if="viewingResume.structured_data.personal_info.linkedin" class="view-field">
                                <label>LinkedIn</label>
                                <p>{{ viewingResume.structured_data.personal_info.linkedin }}</p>
                            </div>
                            <div v-if="viewingResume.structured_data.personal_info.website" class="view-field">
                                <label>Website</label>
                                <p>{{ viewingResume.structured_data.personal_info.website }}</p>
                            </div>
                        </div>
                    </div>

                    <!-- Summary -->
                    <div v-if="viewingResume.structured_data.summary" class="view-section">
                        <h4>Summary</h4>
                        <p style="font-size:0.88rem;color:#374151;line-height:1.55;margin:0;">
                            {{ viewingResume.structured_data.summary }}
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
                            <p v-if="edu.gpa" style="font-size:0.82rem;margin:0;color:#6b7280;">GPA: {{ edu.gpa }}</p>
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

                <div v-else-if="viewingResume && !viewingResume.structured_data"
                     style="color:#8a94a6;font-size:0.9rem;">
                    This resume hasn't been parsed yet. Delete and re-import to parse it.
                </div>

            </div>
        </div>

    </div><!-- /.page -->
</template>


<script>
import { authedFetch, getCurrentUser, setCurrentUser } from '../lib/auth.js'
import { publishCurrentPageDiagnostics, clearCurrentPageDiagnostics } from '../lib/debugDiagnostics'

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
            parseMethod: 'llm',
            uploading: false,
            uploadError: null,
            isDragOver: false,

            // View modal
            showViewModal: false,
            viewingResume: null,
            viewLoading: false,

            // ── Applicant Information tab ───────────────────
            currentUser: null,
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
    },

    async mounted() {
        await this.loadResumes()
        this.loadApplicantInfo()
        this.publishDebugState('mounted')
    },

    beforeUnmount() {
        if (this._saveTimer) clearTimeout(this._saveTimer)
        if (this._jobInfoTimer) clearTimeout(this._jobInfoTimer)
        clearCurrentPageDiagnostics()
    },

    methods: {
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
            this.showViewModal = true
            this.viewLoading = true
            this.viewingResume = null
            this.publishDebugState('view-open')
            try {
                const res = await authedFetch(`/api/resume/${id}`)
                if (!res.ok) throw new Error(`HTTP ${res.status}`)
                this.viewingResume = await res.json()
                this.publishDebugState('view-loaded')
            } catch {
                this.showViewModal = false
                this.publishDebugState('view-load-error')
            } finally {
                this.viewLoading = false
            }
        },

        fullName(pi) {
            return [pi.first_name, pi.last_name].filter(Boolean).join(' ')
        },
        locationStr(pi) {
            return [pi.city, pi.state].filter(Boolean).join(', ')
        },
        hasSkills(skills) {
            if (!skills) return false
            return !!(skills.technical?.length || skills.languages?.length || skills.tools?.length || skills.soft_skills?.length)
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
            return fields.filter(Boolean).length
        },
        portalPercent(r) {
            return Math.round((this.portalFilledCount(r) / 15) * 100)
        },

        // ── Inline upload ───────────────────────────────────
        openUploadModal() {
            this.uploadStep = 'select'
            this.pendingFile = null
            this.parseMethod = 'llm'
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

                // 2. Parse
                const resumeId = uploadData.id
                const parseRes = await authedFetch(`/api/resume/${resumeId}/parse`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ method: this.parseMethod }),
                })
                const parseData = await parseRes.json().catch(() => null)
                if (!parseRes.ok) {
                    throw new Error(this.apiErrorMessage(parseData, parseRes.status, 'Parse failed'))
                }

                this.resetUploadFlow()
                await this.loadResumes()
                this.publishDebugState('upload-success')
            } catch (e) {
                this.uploadError = e.message ?? String(e)
                this.publishDebugState('upload-error')
            } finally {
                this.uploading = false
            }
        },

        // ── Applicant Info ──────────────────────────────────
        loadApplicantInfo() {
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
                    this.phone = d.phone || ''
                    this.linkedin = d.linkedin || ''
                    this.portfolio = d.portfolio || ''
                    this.streetAddress = d.streetAddress || ''
                    this.city = d.city || ''
                    this.appState = d.appState || ''
                    this.zip = d.zip || ''
                    this.summary = d.summary || ''
                    this.workAuth = d.workAuth || ''
                    this.requiresSponsorship = d.requiresSponsorship || ''
                    this.degree = d.degree || ''
                    this.major = d.major || ''
                    this.university = d.university || ''
                    this.gradYear = d.gradYear || ''
                    this.gpa = d.gpa || ''
                    this.yearsExperience = d.yearsExperience || ''
                    this.jobTitle = d.jobTitle || ''
                    this.skillsText = d.skillsText || ''
                    this.certificationsText = d.certificationsText || ''
                    this.professionalLinksText = d.professionalLinksText || ''
                    this.educationHistoryText = d.educationHistoryText || ''
                    this.employmentHistoryText = d.employmentHistoryText || ''
                    this.demographicGender = d.demographicGender || ''
                    this.demographicEthnicity = d.demographicEthnicity || ''
                }
            } catch { /* ignore */ }
            try {
                const eeo = localStorage.getItem('uah_job_info')
                if (eeo) {
                    const d = JSON.parse(eeo)
                    this.veteranStatus = d.veteranStatus || ''
                    this.disabilityStatus = d.disabilityStatus || ''
                    this.californiaResident = d.californiaResident || ''
                }
            } catch { /* ignore */ }
        },

        async saveApplicantInfo() {
            this.working = true
            this.saveStatus = { type: '', message: '' }
            if (this._saveTimer) clearTimeout(this._saveTimer)
            try {
                const user = getCurrentUser()
                const nameChanged =
                    this.firstName !== (user?.first_name || user?.firstName || '') ||
                    this.lastName !== (user?.last_name || user?.lastName || '')
                if (nameChanged && (this.firstName || this.lastName)) {
                    const res = await authedFetch('/api/account/change-name', {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ first_name: this.firstName, last_name: this.lastName }),
                    })
                    const data = await res.json().catch(() => null)
                    if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`)
                    setCurrentUser(data)
                }
                localStorage.setItem(APPINFO_KEY, JSON.stringify({
                    phone: this.phone, linkedin: this.linkedin, portfolio: this.portfolio,
                    streetAddress: this.streetAddress, city: this.city, appState: this.appState, zip: this.zip,
                    summary: this.summary, workAuth: this.workAuth, requiresSponsorship: this.requiresSponsorship,
                    degree: this.degree, major: this.major, university: this.university,
                    gradYear: this.gradYear, gpa: this.gpa,
                    yearsExperience: this.yearsExperience, jobTitle: this.jobTitle,
                    skillsText: this.skillsText,
                    certificationsText: this.certificationsText,
                    professionalLinksText: this.professionalLinksText,
                    educationHistoryText: this.educationHistoryText,
                    employmentHistoryText: this.employmentHistoryText,
                    demographicGender: this.demographicGender,
                    demographicEthnicity: this.demographicEthnicity,
                }))
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
            localStorage.setItem('uah_job_info', JSON.stringify({
                veteranStatus: this.veteranStatus,
                disabilityStatus: this.disabilityStatus,
                californiaResident: this.californiaResident,
            }))
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
