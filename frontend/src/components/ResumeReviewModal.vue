<template>
  <div class="review-overlay" @click.self="requestClose">
    <div class="review-dialog" v-draggable-modal="{ handle: '.review-header' }" @click.stop>
      <div class="review-header drag-handle">
        <div>
          <p class="review-eyebrow">Resume Parse Review</p>
          <h2>{{ meta.file_name || resumeName || 'Review Parsed Resume' }}</h2>
          <p class="review-subtitle">
            {{ parseMethodLabel(meta.parse_method) }}
            <span v-if="meta.review_updated_at"> · Draft updated {{ formatDate(meta.review_updated_at) }}</span>
          </p>
        </div>
        <button type="button" class="btn-secondary btn-compact" @click="requestClose">Close</button>
      </div>

      <div v-if="loading" class="review-state"><div class="spinner"></div><p>Loading parsed resume draft…</p></div>
      <div v-else-if="error" class="review-state review-state--error">
        <p>{{ error }}</p>
        <button type="button" class="btn-secondary" @click="loadReviewDraft">Retry</button>
      </div>

      <template v-else>
        <div class="review-steps">
          <button type="button" :class="['review-step', step === 'review' ? 'active' : '']" @click="step = 'review'">1. Review</button>
          <button type="button" :class="['review-step', step === 'profile' ? 'active' : '']" @click="openProfileStep">2. Choose Profile</button>
          <button type="button" :class="['review-step', step === 'conflicts' ? 'active' : '', conflicts.length ? '' : 'is-disabled']" :disabled="!conflicts.length">3. Conflicts</button>
        </div>

        <div v-if="step === 'review'" class="review-body">
          <section class="review-banner" :class="{ 'is-warning': missingRequired.length || fixesApplied.length || !portalReady }">
            <div>
              <h3>Review extracted fields before filling an applicant profile.</h3>
              <p>Blank values and required parser fields are highlighted so they are easier to catch before the merge.</p>
            </div>
            <div class="review-pill-row">
              <span class="review-pill" :class="portalReady ? 'is-success' : 'is-warning'">{{ portalReady ? 'Portal Ready' : 'Needs Review' }}</span>
              <span class="review-pill">{{ sectionCount }} sections parsed</span>
              <span v-if="fixesApplied.length" class="review-pill">{{ fixesApplied.length }} parser fixes</span>
            </div>
          </section>

          <section v-if="missingRequired.length" class="review-alert">
            <h4>Missing required fields</h4>
            <div class="review-pill-row">
              <span v-for="path in missingRequired" :key="path" class="review-pill is-warning">{{ prettifyPath(path) }}</span>
            </div>
          </section>

          <section v-if="fixesApplied.length" class="review-alert">
            <h4>Parser fixes applied</h4>
            <ul class="review-list"><li v-for="item in fixesApplied" :key="item">{{ item }}</li></ul>
          </section>

          <section class="review-section">
            <div class="review-section-head"><div><h3>Personal Information</h3><p>Confirm contact details and location before saving.</p></div></div>
            <div class="review-grid review-grid--two">
              <label v-for="field in personalFields" :key="field.key" :class="['review-field', field.full ? 'review-field--full' : '']">
                <span>{{ field.label }}</span>
                <input v-model="reviewDraft.personal_info[field.key]" :type="field.type || 'text'" :class="fieldClass(`personal_info.${field.key}`, reviewDraft.personal_info[field.key])">
              </label>
            </div>
          </section>

          <section class="review-section">
            <div class="review-section-head"><div><h3>Summary</h3><p>Keep this reusable for downstream autofill and profile generation.</p></div></div>
            <label class="review-field"><span>Professional Summary</span><textarea v-model="reviewDraft.summary" rows="5" :class="fieldClass('summary', reviewDraft.summary)"></textarea></label>
          </section>

          <section class="review-section">
            <div class="review-section-head"><div><h3>Skills</h3><p>Use comma-separated values so the data remains easy to tokenize later.</p></div></div>
            <div class="review-grid review-grid--two">
              <label v-for="field in skillFields" :key="field.key" class="review-field">
                <span>{{ field.label }}</span>
                <textarea :value="joinList(reviewDraft.skills[field.key])" rows="3" :class="fieldClass(`skills.${field.key}`, reviewDraft.skills[field.key])" @input="setInlineList(reviewDraft.skills, field.key, $event.target.value)"></textarea>
              </label>
            </div>
          </section>

          <section v-for="section in structuredSections" :key="section.key" class="review-section">
            <div class="review-section-head">
              <div><h3>{{ section.title }}</h3><p>{{ section.description }}</p></div>
              <button type="button" class="btn-secondary btn-compact" @click="addStructuredEntry(section.key)">Add Entry</button>
            </div>

            <p v-if="!reviewDraft[section.key].length" class="review-empty">{{ section.emptyText }}</p>

            <details v-for="(entry, index) in reviewDraft[section.key]" :key="`${section.key}-${index}`" class="review-entry" open>
              <summary>
                <div>
                  <strong>{{ entryTitle(section.key, entry, index) }}</strong>
                  <span>{{ entrySubtitle(section.key, entry) }}</span>
                </div>
                <button type="button" class="review-inline-btn" @click.stop="removeStructuredEntry(section.key, index)">Remove</button>
              </summary>

              <div class="review-grid review-grid--two">
                <template v-for="field in section.fields" :key="`${section.key}-${field.key}`">
                  <label :class="['review-field', field.full ? 'review-field--full' : '']">
                    <span>{{ field.label }}</span>
                    <textarea
                      v-if="field.kind === 'textarea'"
                      v-model="entry[field.key]"
                      rows="3"
                      :class="fieldClass(`${section.pathStem}.${field.key}`, entry[field.key])"
                    ></textarea>
                    <textarea
                      v-else-if="field.kind === 'inline-list'"
                      :value="joinList(entry[field.key])"
                      rows="2"
                      :class="fieldClass(`${section.pathStem}.${field.key}`, entry[field.key])"
                      @input="setInlineList(entry, field.key, $event.target.value)"
                    ></textarea>
                    <textarea
                      v-else-if="field.kind === 'line-list'"
                      :value="joinLines(entry[field.key])"
                      rows="4"
                      :class="fieldClass(`${section.pathStem}.${field.key}`, entry[field.key])"
                      @input="setLineList(entry, field.key, $event.target.value)"
                    ></textarea>
                    <select v-else-if="field.kind === 'current-select'" v-model="entry.is_current" @change="syncCurrentRole(entry)">
                      <option :value="false">No</option>
                      <option :value="true">Yes</option>
                    </select>
                    <input
                      v-else
                      v-model="entry[field.key]"
                      :type="field.type || 'text'"
                      :class="fieldClass(`${section.pathStem}.${field.key}`, entry[field.key])"
                    >
                  </label>
                </template>
              </div>
            </details>
          </section>

          <section class="review-section">
            <div class="review-section-head"><div><h3>Additional Sections</h3><p>Optional sections still matter for long-term autofill coverage, so they stay editable here too.</p></div></div>
            <div class="review-grid review-grid--three">
              <label v-for="field in extraListSections" :key="field.key" class="review-field">
                <span>{{ field.label }}</span>
                <textarea :value="joinLines(reviewDraft[field.key])" rows="4" :class="fieldClass(field.key, reviewDraft[field.key])" @input="setRootLineList(field.key, $event.target.value)"></textarea>
              </label>
            </div>
          </section>
        </div>

        <div v-else-if="step === 'profile'" class="review-body">
          <section class="review-section">
            <div class="review-section-head"><div><h3>Choose where this reviewed data should go</h3><p>Merge into an existing profile or create a new one from this parse.</p></div></div>
            <div class="review-toggle">
              <button type="button" :class="['review-toggle-btn', selectedMode === 'existing' ? 'active' : '']" @click="selectedMode = 'existing'">Fill Existing Profile</button>
              <button type="button" :class="['review-toggle-btn', selectedMode === 'new' ? 'active' : '']" @click="selectedMode = 'new'">Create New Profile</button>
            </div>

            <template v-if="selectedMode === 'existing'">
              <label class="review-field review-field--full"><span>Search Profiles</span><input v-model="profileQuery" type="text" placeholder="Search by name, title, city, or state"></label>
              <div v-if="filteredProfiles.length" class="profile-list">
                <button v-for="profile in filteredProfiles" :key="profile.id" type="button" :class="['profile-option', Number(selectedProfileId) === Number(profile.id) ? 'is-selected' : '']" @click="selectedProfileId = Number(profile.id)">
                  <div>
                    <strong>{{ profile.name }}</strong>
                    <p>{{ profileSummary(profile) }}</p>
                    <p>Updated {{ formatDate(profile.updated_at || profile.created_at) }}</p>
                  </div>
                  <span v-if="profile.is_active" class="review-pill is-success">Active</span>
                </button>
              </div>
              <p v-else class="review-empty">No profiles matched that search. You can create a new one instead.</p>
            </template>

            <template v-else>
              <label class="review-field review-field--full"><span>Profile Name</span><input v-model="newProfileName" type="text" placeholder="Name this new applicant profile"></label>
              <p class="review-helper">Suggested name: <strong>{{ suggestedProfileName }}</strong></p>
            </template>
          </section>
        </div>

        <div v-else class="review-body">
          <section class="review-section">
            <div class="review-section-head"><div><h3>Resolve merge conflicts</h3><p>Existing non-empty values are preserved by default unless you explicitly choose the reviewed parse.</p></div></div>
            <article v-for="conflict in conflicts" :key="conflict.id" class="conflict-card">
              <div class="conflict-head"><h4>{{ conflict.label }}</h4><span class="review-pill is-warning">{{ prettifyPath(conflict.path) }}</span></div>
              <div class="conflict-grid">
                <label :class="['conflict-option', conflictChoice(conflict.path) === 'existing' ? 'is-selected' : '']">
                  <input :checked="conflictChoice(conflict.path) === 'existing'" type="radio" :name="`conflict-${conflict.id}`" @change="setConflictChoice(conflict.path, 'existing')">
                  <span class="conflict-option-title">Keep existing profile value</span>
                  <code>{{ displayConflictValue(conflict.existing_value) }}</code>
                </label>
                <label :class="['conflict-option', conflictChoice(conflict.path) === 'incoming' ? 'is-selected' : '']">
                  <input :checked="conflictChoice(conflict.path) === 'incoming'" type="radio" :name="`conflict-${conflict.id}`" @change="setConflictChoice(conflict.path, 'incoming')">
                  <span class="conflict-option-title">Use parsed value</span>
                  <code>{{ displayConflictValue(conflict.incoming_value) }}</code>
                </label>
              </div>
            </article>
          </section>
        </div>

        <div class="review-footer">
          <p class="review-footer-note">{{ footerNote }}</p>
          <div class="review-footer-actions">
            <button v-if="step !== 'review'" type="button" class="btn-secondary" :disabled="busy" @click="goBack">Back</button>
            <button v-if="step === 'review'" type="button" class="btn-secondary" :disabled="busy" @click="persistDraft({ toastOnSuccess: true })">{{ savingDraft ? 'Saving Draft…' : 'Save Draft' }}</button>
            <button v-if="step === 'review'" type="button" class="btn-primary" :disabled="busy" @click="openProfileStep">Continue</button>
            <button v-else-if="step === 'profile'" type="button" class="btn-primary" :disabled="busy || !canApplySelection" @click="submitProfileStep">{{ conflictsLoading ? 'Checking Conflicts…' : applying ? 'Saving Profile…' : selectedMode === 'existing' ? 'Review Merge' : 'Create Profile and Save' }}</button>
            <button v-else type="button" class="btn-primary" :disabled="busy" @click="applyReview">{{ applying ? 'Applying Review…' : 'Apply to Profile' }}</button>
          </div>
        </div>
      </template>
    </div>

    <ConfirmModal
      v-if="closeConfirmVisible"
      title="Leave Resume Review?"
      message="Your parsed draft remains saved on this resume, but unsaved edits in this modal will be lost. Close anyway?"
      cancel-text="Keep Reviewing"
      confirm-text="Close Review"
      @cancel="closeConfirmVisible = false"
      @confirm="confirmClose"
    />
  </div>
</template>

<script>
import ConfirmModal from './ConfirmModal.vue'
import { authedFetch } from '../lib/auth.js'
import { showToast } from '../services/toastService.js'

const PERSONAL_FIELDS = [
  { key: 'first_name', label: 'First Name' },
  { key: 'last_name', label: 'Last Name' },
  { key: 'email', label: 'Email', type: 'email' },
  { key: 'phone', label: 'Phone' },
  { key: 'address', label: 'Street Address', full: true },
  { key: 'city', label: 'City' },
  { key: 'state', label: 'State' },
  { key: 'zip', label: 'ZIP' },
  { key: 'linkedin', label: 'LinkedIn', type: 'url' },
  { key: 'website', label: 'Website', type: 'url' },
]

const SKILL_FIELDS = [
  { key: 'technical', label: 'Technical Skills' },
  { key: 'languages', label: 'Languages' },
  { key: 'tools', label: 'Tools' },
  { key: 'soft_skills', label: 'Soft Skills' },
]

const STRUCTURED_SECTIONS = [
  {
    key: 'education',
    pathStem: 'education',
    title: 'Education',
    description: 'Education stays structured so it can be flattened back into token paths later.',
    emptyText: 'The parser did not return any education entries.',
    fields: [
      { key: 'institution', label: 'Institution' },
      { key: 'degree', label: 'Degree' },
      { key: 'field_of_study', label: 'Field of Study' },
      { key: 'gpa', label: 'GPA' },
      { key: 'start_date', label: 'Start Date' },
      { key: 'end_date', label: 'End Date' },
      { key: 'honors', label: 'Honors', kind: 'inline-list', full: true },
      { key: 'relevant_coursework', label: 'Relevant Coursework', kind: 'inline-list', full: true },
    ],
  },
  {
    key: 'work_experience',
    pathStem: 'work_experience',
    title: 'Work Experience',
    description: 'Review titles, dates, and bullets before the merge step.',
    emptyText: 'The parser did not return any work experience entries.',
    fields: [
      { key: 'company', label: 'Company' },
      { key: 'title', label: 'Title' },
      { key: 'location', label: 'Location' },
      { key: 'is_current', label: 'Current Role', kind: 'current-select' },
      { key: 'start_date', label: 'Start Date' },
      { key: 'end_date', label: 'End Date' },
      { key: 'bullets', label: 'Bullets', kind: 'line-list', full: true },
    ],
  },
  {
    key: 'projects',
    pathStem: 'projects',
    title: 'Projects',
    description: 'Project details are kept structured for later token regeneration.',
    emptyText: 'No projects were extracted from this parse.',
    fields: [
      { key: 'name', label: 'Name' },
      { key: 'date', label: 'Date' },
      { key: 'description', label: 'Description', kind: 'textarea', full: true },
      { key: 'technologies', label: 'Technologies', kind: 'inline-list', full: true },
    ],
  },
  {
    key: 'certifications',
    pathStem: 'certifications',
    title: 'Certifications',
    description: 'Review certification names and issuers before the merge.',
    emptyText: 'No certifications were extracted from this parse.',
    fields: [
      { key: 'name', label: 'Name' },
      { key: 'issuer', label: 'Issuer' },
      { key: 'date', label: 'Date', full: true },
    ],
  },
]

const EXTRA_LIST_SECTIONS = [
  { key: 'awards', label: 'Awards' },
  { key: 'activities', label: 'Activities' },
  { key: 'volunteer', label: 'Volunteer' },
]

export default {
  name: 'ResumeReviewModal',
  components: { ConfirmModal },
  props: {
    resumeId: { type: Number, required: true },
    resumeName: { type: String, default: '' },
    profiles: { type: Array, default: () => [] },
    activeProfileId: { type: Number, default: null },
  },
  emits: ['close', 'applied'],
  data() {
    return {
      personalFields: PERSONAL_FIELDS,
      skillFields: SKILL_FIELDS,
      structuredSections: STRUCTURED_SECTIONS,
      extraListSections: EXTRA_LIST_SECTIONS,
      reviewSchemaVersion: '',
      loading: false,
      error: '',
      step: 'review',
      meta: { file_name: '', parse_method: '', review_status: '', review_updated_at: '' },
      reviewDraft: this.normalizeDraft({}),
      selectedMode: 'existing',
      selectedProfileId: null,
      newProfileName: '',
      profileQuery: '',
      conflicts: [],
      conflictResolutions: {},
      savingDraft: false,
      conflictsLoading: false,
      applying: false,
      closeConfirmVisible: false,
      lastSavedSignature: '',
    }
  },
  computed: {
    busy() { return this.savingDraft || this.conflictsLoading || this.applying },
    missingRequired() { return Array.isArray(this.reviewDraft?._validation?.missing_required) ? this.reviewDraft._validation.missing_required.filter(Boolean) : [] },
    fixesApplied() { return Array.isArray(this.reviewDraft?._validation?.fixes_applied) ? this.reviewDraft._validation.fixes_applied.filter(Boolean) : [] },
    portalReady() { return Boolean(this.reviewDraft?._validation?.portal_ready) },
    currentSignature() { return JSON.stringify(this.reviewDraft || {}) },
    dirty() { return this.currentSignature !== this.lastSavedSignature },
    sectionCount() {
      return [
        this.hasObjectContent(this.reviewDraft.personal_info),
        Boolean(this.cleanText(this.reviewDraft.summary)),
        this.hasListContent(this.reviewDraft.education),
        this.hasListContent(this.reviewDraft.work_experience),
        this.hasSkillsContent(this.reviewDraft.skills),
        this.hasListContent(this.reviewDraft.projects),
        this.hasListContent(this.reviewDraft.certifications),
        this.hasListContent(this.reviewDraft.awards),
        this.hasListContent(this.reviewDraft.activities),
        this.hasListContent(this.reviewDraft.volunteer),
      ].filter(Boolean).length
    },
    filteredProfiles() {
      const query = this.cleanText(this.profileQuery).toLowerCase()
      const profiles = Array.isArray(this.profiles) ? this.profiles : []
      if (!query) return profiles
      return profiles.filter((profile) => [profile.name, profile.first_name, profile.last_name, profile.job_title, profile.city, profile.state].join(' ').toLowerCase().includes(query))
    },
    suggestedProfileName() {
      if (this.cleanText(this.newProfileName)) return this.newProfileName.trim()
      const name = [this.cleanText(this.reviewDraft.personal_info.first_name), this.cleanText(this.reviewDraft.personal_info.last_name)].filter(Boolean).join(' ')
      return name || this.resumeName || this.meta.file_name || 'Imported Profile'
    },
    canApplySelection() { return this.selectedMode === 'existing' ? Boolean(this.selectedProfileId) : Boolean(this.cleanText(this.suggestedProfileName)) },
    footerNote() {
      if (this.step === 'review') return this.dirty ? 'Save the draft or continue to persist your latest edits.' : 'This review draft is already persisted on the resume and can be resumed later.'
      if (this.step === 'profile') return this.selectedMode === 'existing' ? 'Existing non-empty values stay in place by default whenever there is a conflict.' : 'A new applicant profile will be created from this reviewed parse and made active.'
      return 'Choose the value that should remain in the applicant profile after the merge.'
    },
  },
  watch: {
    resumeId: { immediate: true, handler(value) { if (value) this.loadReviewDraft() } },
    profiles: {
      immediate: true,
      handler(nextProfiles) {
        if (!Array.isArray(nextProfiles) || !nextProfiles.length) {
          this.selectedMode = 'new'
          this.selectedProfileId = null
          return
        }
        const fallbackId = Number(this.activeProfileId) || Number(nextProfiles.find((profile) => profile.is_active)?.id) || Number(nextProfiles[0].id)
        if (!nextProfiles.some((profile) => Number(profile.id) === Number(this.selectedProfileId))) this.selectedProfileId = fallbackId
      },
    },
  },
  methods: {
    cleanText(value) { return typeof value === 'string' ? value.trim() : '' },
    cloneValue(value) { return JSON.parse(JSON.stringify(value || {})) },
    normalizeText(value) { return typeof value === 'string' ? value : '' },
    normalizeList(value) { return Array.isArray(value) ? value.map((item) => (typeof item === 'string' ? item.trim() : '')).filter(Boolean) : [] },
    splitInline(value) { return String(value || '').split(/[\n,;]+/).map((item) => item.trim()).filter(Boolean) },
    splitLines(value) { return String(value || '').split(/\r?\n+/).map((item) => item.trim()).filter(Boolean) },
    joinList(value) { return this.normalizeList(value).join(', ') },
    joinLines(value) { return this.normalizeList(value).join('\n') },
    normalizeValidation(value) {
      const validation = value && typeof value === 'object' ? value : {}
      return { ...validation, missing_required: this.normalizeList(validation.missing_required), fixes_applied: this.normalizeList(validation.fixes_applied) }
    },
    normalizeEntry(sectionKey, entry = {}) {
      if (sectionKey === 'education') return { institution: this.normalizeText(entry.institution), degree: this.normalizeText(entry.degree), field_of_study: this.normalizeText(entry.field_of_study), gpa: this.normalizeText(entry.gpa), start_date: this.normalizeText(entry.start_date), end_date: this.normalizeText(entry.end_date), honors: this.normalizeList(entry.honors), relevant_coursework: this.normalizeList(entry.relevant_coursework) }
      if (sectionKey === 'work_experience') return { company: this.normalizeText(entry.company), title: this.normalizeText(entry.title), location: this.normalizeText(entry.location), start_date: this.normalizeText(entry.start_date), end_date: this.normalizeText(entry.end_date), is_current: Boolean(entry.is_current || String(entry.end_date || '').toLowerCase() === 'present'), bullets: this.normalizeList(entry.bullets) }
      if (sectionKey === 'projects') return { name: this.normalizeText(entry.name), description: this.normalizeText(entry.description), date: this.normalizeText(entry.date), technologies: this.normalizeList(entry.technologies) }
      return typeof entry === 'string' ? { name: entry.trim(), issuer: '', date: '' } : { name: this.normalizeText(entry.name), issuer: this.normalizeText(entry.issuer), date: this.normalizeText(entry.date) }
    },
    normalizeDraft(value) {
      const draft = value && typeof value === 'object' ? value : {}
      const personal = draft.personal_info && typeof draft.personal_info === 'object' ? draft.personal_info : {}
      const skills = draft.skills && typeof draft.skills === 'object' ? draft.skills : {}
      const personalFields = Array.isArray(this.personalFields) && this.personalFields.length ? this.personalFields : PERSONAL_FIELDS
      const skillFields = Array.isArray(this.skillFields) && this.skillFields.length ? this.skillFields : SKILL_FIELDS
      return {
        personal_info: Object.fromEntries(personalFields.map((field) => [field.key, this.normalizeText(personal[field.key])])),
        summary: this.normalizeText(draft.summary),
        skills: Object.fromEntries(skillFields.map((field) => [field.key, this.normalizeList(skills[field.key])])),
        education: Array.isArray(draft.education) ? draft.education.map((entry) => this.normalizeEntry('education', entry)) : [],
        work_experience: Array.isArray(draft.work_experience) ? draft.work_experience.map((entry) => this.normalizeEntry('work_experience', entry)) : [],
        projects: Array.isArray(draft.projects) ? draft.projects.map((entry) => this.normalizeEntry('projects', entry)) : [],
        certifications: Array.isArray(draft.certifications) ? draft.certifications.map((entry) => this.normalizeEntry('certifications', entry)) : [],
        awards: this.normalizeList(draft.awards),
        activities: this.normalizeList(draft.activities),
        volunteer: this.normalizeList(draft.volunteer),
        _validation: this.normalizeValidation(draft._validation),
      }
    },
    applyReviewSchema(schema) {
      const normalized = schema && typeof schema === 'object' ? schema : {}
      const personalFields = Array.isArray(normalized.personal_fields) ? normalized.personal_fields : PERSONAL_FIELDS
      const skillFields = Array.isArray(normalized.skill_fields) ? normalized.skill_fields : SKILL_FIELDS
      const structuredSections = Array.isArray(normalized.structured_sections) ? normalized.structured_sections : STRUCTURED_SECTIONS
      const extraListSections = Array.isArray(normalized.extra_list_sections) ? normalized.extra_list_sections : EXTRA_LIST_SECTIONS
      this.personalFields = personalFields
      this.skillFields = skillFields
      this.structuredSections = structuredSections
      this.extraListSections = extraListSections
      this.reviewSchemaVersion = typeof normalized.version === 'string' ? normalized.version : ''
    },
    hasObjectContent(value) { return Object.values(value || {}).some((item) => Array.isArray(item) ? item.length > 0 : Boolean(this.cleanText(item))) },
    hasListContent(value) { return Array.isArray(value) && value.some((item) => typeof item === 'string' ? Boolean(this.cleanText(item)) : this.hasObjectContent(item)) },
    hasSkillsContent(value) { return Object.values(value || {}).some((items) => Array.isArray(items) && items.length > 0) },
    setInlineList(target, key, value) { target[key] = this.splitInline(value) },
    setLineList(target, key, value) { target[key] = this.splitLines(value) },
    setRootLineList(key, value) { this.reviewDraft[key] = this.splitLines(value) },
    newStructuredEntry(sectionKey) { return this.normalizeEntry(sectionKey, {}) },
    addStructuredEntry(sectionKey) { this.reviewDraft[sectionKey].push(this.newStructuredEntry(sectionKey)) },
    removeStructuredEntry(sectionKey, index) { this.reviewDraft[sectionKey].splice(index, 1) },
    syncCurrentRole(entry) { if (entry.is_current) entry.end_date = this.cleanText(entry.end_date) || 'Present'; else if (String(entry.end_date || '').toLowerCase() === 'present') entry.end_date = '' },
    prettifyPath(path) { return String(path || '').replace(/^personal_info\./, '').replace(/_/g, ' ').replace(/\[(\d+)\]/g, (_, n) => ` #${Number(n) + 1}`).replace(/\./g, ' ').replace(/\s+/g, ' ').trim().replace(/\b\w/g, (char) => char.toUpperCase()) },
    fieldClass(path, value) { return { 'is-attention': this.isBlank(value) || this.pathNeedsReview(path) } },
    isBlank(value) { return Array.isArray(value) ? value.length === 0 : !this.cleanText(value) },
    pathNeedsReview(path) { return this.missingRequired.some((item) => item === path || item.startsWith(`${path}.`) || path.startsWith(`${item}.`)) },
    parseMethodLabel(method) { const normalized = String(method || '').toLowerCase(); return normalized === 'cloud' ? 'Cloud AI Parse' : normalized === 'rules' ? 'Rules-based Parse' : normalized === 'local' ? 'Local AI Parse' : 'Parsed Resume Draft' },
    formatDate(iso) { try { return iso ? new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'recently' } catch { return iso } },
    entryTitle(sectionKey, entry, index) { if (sectionKey === 'education') return entry.institution || entry.degree || `Education #${index + 1}`; if (sectionKey === 'work_experience') return entry.title || entry.company || `Role #${index + 1}`; if (sectionKey === 'projects') return entry.name || `Project #${index + 1}`; return entry.name || `Certification #${index + 1}` },
    entrySubtitle(sectionKey, entry) { if (sectionKey === 'education') return [entry.degree, entry.field_of_study].filter(Boolean).join(' · ') || 'Review entry'; if (sectionKey === 'work_experience') return [entry.company, entry.location].filter(Boolean).join(' · ') || 'Review entry'; if (sectionKey === 'projects') return entry.date || 'Review entry'; return [entry.issuer, entry.date].filter(Boolean).join(' · ') || 'Review entry' },
    profileSummary(profile) { return [[profile.first_name, profile.last_name].filter(Boolean).join(' '), profile.job_title, [profile.city, profile.state].filter(Boolean).join(', ')].filter(Boolean).join(' · ') || 'No profile details yet' },
    requestClose() { if (this.busy) return; if (this.dirty) { this.closeConfirmVisible = true; return } this.$emit('close') },
    confirmClose() { this.closeConfirmVisible = false; this.$emit('close') },
    async loadReviewDraft() {
      this.loading = true
      this.error = ''
      this.step = 'review'
      this.conflicts = []
      this.conflictResolutions = {}
      try {
        const response = await authedFetch(`/api/resume/${this.resumeId}/review-draft`)
        const payload = await response.json().catch(() => null)
        if (!response.ok) throw new Error(payload?.detail || `HTTP ${response.status}`)
        this.meta = { file_name: payload.file_name || '', parse_method: payload.parse_method || '', review_status: payload.review_status || '', review_updated_at: payload.review_updated_at || '' }
        this.applyReviewSchema(payload.review_schema)
        this.reviewDraft = this.normalizeDraft(this.cloneValue(payload.review_draft))
        this.lastSavedSignature = this.currentSignature
        if (!this.cleanText(this.newProfileName)) this.newProfileName = this.suggestedProfileName
      } catch (error) {
        this.error = error?.message || 'Failed to load the review draft.'
      } finally {
        this.loading = false
      }
    },
    async persistDraft({ toastOnSuccess = false, quietIfClean = false } = {}) {
      if (quietIfClean && !this.dirty) return true
      this.savingDraft = true
      try {
        const response = await authedFetch(`/api/resume/${this.resumeId}/review-draft`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ review_draft: this.reviewDraft }),
        })
        const payload = await response.json().catch(() => null)
        if (!response.ok) throw new Error(payload?.detail || `HTTP ${response.status}`)
        this.applyReviewSchema(payload.review_schema)
        this.meta.review_status = payload.review_status || 'pending'
        this.meta.review_updated_at = payload.review_updated_at || ''
        this.reviewDraft = this.normalizeDraft(this.cloneValue(payload.review_draft))
        this.lastSavedSignature = this.currentSignature
        if (toastOnSuccess) showToast('Review draft saved.', 'success')
        return true
      } catch (error) {
        showToast(error?.message || 'Failed to save review draft.', 'error')
        return false
      } finally {
        this.savingDraft = false
      }
    },
    async openProfileStep() {
      if (!(await this.persistDraft({ quietIfClean: true }))) return
      if (!this.profiles.length) this.selectedMode = 'new'
      if (!this.cleanText(this.newProfileName)) this.newProfileName = this.suggestedProfileName
      this.step = 'profile'
    },
    goBack() { this.step = this.step === 'conflicts' ? 'profile' : 'review' },
    async submitProfileStep() {
      if (!(await this.persistDraft({ quietIfClean: true }))) return
      if (this.selectedMode === 'new') { await this.applyReview(); return }
      if (!this.selectedProfileId) { showToast('Choose a profile to continue.', 'error'); return }
      this.conflictsLoading = true
      try {
        const response = await authedFetch(`/api/resume/${this.resumeId}/review-conflicts`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ profile_id: Number(this.selectedProfileId), reviewed_data: this.reviewDraft }),
        })
        const payload = await response.json().catch(() => null)
        if (!response.ok) throw new Error(payload?.detail || `HTTP ${response.status}`)
        this.conflicts = Array.isArray(payload.conflicts) ? payload.conflicts : []
        this.conflictResolutions = this.conflicts.reduce((acc, item) => ({ ...acc, [item.path]: 'existing' }), {})
        if (this.conflicts.length) { this.step = 'conflicts'; return }
        await this.applyReview()
      } catch (error) {
        showToast(error?.message || 'Failed to check merge conflicts.', 'error')
      } finally {
        this.conflictsLoading = false
      }
    },
    conflictChoice(path) { return this.conflictResolutions[path] || 'existing' },
    setConflictChoice(path, value) { this.conflictResolutions = { ...this.conflictResolutions, [path]: value } },
    displayConflictValue(value) { return Array.isArray(value) ? value.join(', ') : value && typeof value === 'object' ? JSON.stringify(value) : String(value ?? '—') },
    async applyReview() {
      this.applying = true
      try {
        const payload = { mode: this.selectedMode, reviewed_data: this.reviewDraft }
        if (this.selectedMode === 'existing') {
          payload.profile_id = Number(this.selectedProfileId)
          if (this.conflicts.length) payload.conflict_resolutions = this.conflictResolutions
        } else {
          payload.profile_name = this.suggestedProfileName
        }
        const response = await authedFetch(`/api/resume/${this.resumeId}/apply-review`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
        const result = await response.json().catch(() => null)
        if (!response.ok) throw new Error(result?.detail || `HTTP ${response.status}`)
        this.meta.review_status = result.review_status || 'applied'
        this.lastSavedSignature = this.currentSignature
        showToast('Applicant profile updated from reviewed parse.', 'success')
        this.$emit('applied', result)
      } catch (error) {
        showToast(error?.message || 'Failed to apply reviewed parse.', 'error')
      } finally {
        this.applying = false
      }
    },
  },
}
</script>

<style scoped>
.review-overlay{position:fixed;inset:0;z-index:9100;display:flex;align-items:center;justify-content:center;padding:20px;background:rgba(15,23,42,.42)}
.review-dialog{width:min(1160px,100%);max-height:calc(100vh - 40px);display:flex;flex-direction:column;overflow:hidden;border:1px solid var(--border-color);border-radius:18px;background:rgba(255,255,255,.98);box-shadow:0 20px 50px rgba(15,23,42,.18)}
.review-header,.review-footer,.review-section-head,.conflict-head,.review-banner{display:flex;align-items:flex-start;justify-content:space-between;gap:16px}
.review-header{padding:22px 24px 18px;border-bottom:1px solid var(--border-color-light);cursor:grab}
.review-eyebrow{margin:0 0 6px;font-size:.74rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#0f766e}
.review-header h2,.review-banner h3,.review-alert h4,.review-section h3,.conflict-head h4{margin:0;color:var(--color-text-primary)}
.review-subtitle,.review-banner p,.review-section-head p,.review-helper,.review-empty,.review-footer-note,.profile-option p,.review-entry summary span{margin:6px 0 0;color:var(--color-text-muted);line-height:1.5}
.review-steps{display:flex;gap:10px;padding:16px 24px;border-bottom:1px solid var(--border-color-light);background:rgba(248,250,252,.9)}
.review-step,.review-pill,.review-toggle-btn,.review-inline-btn,.profile-option,.conflict-option{border:1px solid rgba(203,213,225,.85);background:#fff}
.review-step{border-radius:999px;padding:8px 14px;color:var(--color-text-secondary);font-size:.84rem;font-weight:700}
.review-step.active,.review-toggle-btn.active{border-color:rgba(37,99,235,.3);background:rgba(37,99,235,.1);color:var(--color-primary-700)}
.review-step.is-disabled{opacity:.6}
.review-body{flex:1;overflow:auto;padding:24px;display:flex;flex-direction:column;gap:18px}
.review-state{min-height:280px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;color:var(--color-text-secondary)}
.review-state--error{color:var(--color-danger-600)}
.review-banner,.review-alert,.review-section,.conflict-card{border:1px solid rgba(203,213,225,.85);border-radius:16px;background:rgba(248,250,252,.78);padding:18px}
.review-banner.is-warning,.conflict-card{border-color:rgba(234,179,8,.3);background:rgba(255,251,235,.88)}
.review-pill-row,.profile-list{display:flex;flex-wrap:wrap;gap:8px}
.review-pill{display:inline-flex;align-items:center;border-radius:999px;padding:5px 10px;font-size:.76rem;font-weight:700;color:var(--color-text-secondary)}
.review-pill.is-success{border-color:rgba(34,197,94,.32);background:rgba(34,197,94,.12);color:#15803d}
.review-pill.is-warning{border-color:rgba(234,179,8,.32);background:rgba(234,179,8,.13);color:#92400e}
.review-list{margin:10px 0 0 18px;color:var(--color-text-secondary)}
.review-grid{display:grid;gap:14px}
.review-grid--two{grid-template-columns:repeat(2,minmax(0,1fr))}
.review-grid--three{grid-template-columns:repeat(3,minmax(0,1fr))}
.review-field{display:flex;flex-direction:column;gap:7px}
.review-field--full{grid-column:1/-1}
.review-field span{font-size:.82rem;font-weight:700;color:var(--color-text-secondary)}
.review-field input,.review-field select,.review-field textarea{width:100%;border:1px solid rgba(203,213,225,.95);border-radius:10px;background:rgba(255,255,255,.96);padding:10px 12px;color:var(--color-text-primary)}
.review-field textarea{resize:vertical}
.review-field input:focus,.review-field select:focus,.review-field textarea:focus{outline:none;border-color:var(--color-primary-600);box-shadow:0 0 0 3px rgba(37,99,235,.14)}
.review-field .is-attention{border-color:rgba(234,179,8,.7);background:rgba(255,251,235,.92)}
.review-entry{border:1px solid rgba(203,213,225,.85);border-radius:14px;background:rgba(255,255,255,.92);overflow:hidden}
.review-entry summary{list-style:none;display:flex;align-items:center;justify-content:space-between;gap:14px;padding:14px 16px;cursor:pointer;border-bottom:1px solid rgba(226,232,240,.86)}
.review-entry summary::-webkit-details-marker{display:none}
.review-entry summary strong,.profile-option strong{display:block;color:var(--color-text-primary)}
.review-entry>.review-grid{padding:16px}
.review-inline-btn{border-radius:999px;padding:6px 10px;color:var(--color-danger-600);font-size:.78rem;font-weight:700;background:rgba(254,242,242,.85)}
.review-toggle{display:inline-flex;gap:8px;margin-bottom:16px;padding:6px;border:1px solid rgba(203,213,225,.85);border-radius:14px;background:rgba(248,250,252,.9)}
.review-toggle-btn{border-radius:10px;padding:10px 14px;color:var(--color-text-secondary);font-weight:700}
.profile-list{flex-direction:column}
.profile-option{display:flex;align-items:flex-start;justify-content:space-between;gap:14px;padding:14px 16px;border-radius:14px;text-align:left}
.profile-option.is-selected,.conflict-option.is-selected{border-color:rgba(37,99,235,.42);background:rgba(239,246,255,.92);box-shadow:0 0 0 3px rgba(37,99,235,.08)}
.conflict-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.conflict-option{display:flex;flex-direction:column;gap:8px;min-width:0;padding:14px;border-radius:14px;cursor:pointer}
.conflict-option-title{font-weight:700;color:var(--color-text-primary)}
.conflict-option code{display:block;white-space:pre-wrap;word-break:break-word;padding:10px;border-radius:10px;background:rgba(248,250,252,.92);color:#0f172a;font-size:.82rem}
.review-footer{padding:16px 24px 20px;border-top:1px solid var(--border-color-light);background:rgba(255,255,255,.98)}
.review-footer-actions{display:flex;align-items:center;gap:10px;flex-shrink:0}
@media (max-width:900px){.review-overlay{padding:12px}.review-dialog{max-height:calc(100vh - 24px)}.review-grid--two,.review-grid--three,.conflict-grid{grid-template-columns:1fr}.review-header,.review-footer,.review-section-head,.conflict-head,.review-banner{flex-direction:column;align-items:stretch}.review-footer-actions{width:100%;justify-content:flex-end}}
@media (max-width:640px){.review-header,.review-steps,.review-body,.review-footer{padding-left:16px;padding-right:16px}.review-steps{overflow:auto}.review-footer-actions{flex-direction:column-reverse;align-items:stretch}.review-footer-actions .btn-primary,.review-footer-actions .btn-secondary{width:100%}}

html[data-theme="dark"] .review-overlay{background:rgba(2,6,23,.72)}
html[data-theme="dark"] .review-dialog{background:var(--color-surface);border-color:var(--border-color);box-shadow:0 24px 52px rgba(2,6,23,.55)}
html[data-theme="dark"] .review-header,
html[data-theme="dark"] .review-steps,
html[data-theme="dark"] .review-footer{background:var(--color-surface)}
html[data-theme="dark"] .review-header,
html[data-theme="dark"] .review-steps,
html[data-theme="dark"] .review-footer{border-color:var(--border-color)}
html[data-theme="dark"] .review-eyebrow{color:#5eead4}
html[data-theme="dark"] .review-subtitle,
html[data-theme="dark"] .review-banner p,
html[data-theme="dark"] .review-section-head p,
html[data-theme="dark"] .review-helper,
html[data-theme="dark"] .review-empty,
html[data-theme="dark"] .review-footer-note,
html[data-theme="dark"] .profile-option p,
html[data-theme="dark"] .review-entry summary span{color:var(--color-text-secondary)}
html[data-theme="dark"] .review-step,
html[data-theme="dark"] .review-pill,
html[data-theme="dark"] .review-toggle-btn,
html[data-theme="dark"] .review-inline-btn,
html[data-theme="dark"] .profile-option,
html[data-theme="dark"] .conflict-option{border-color:var(--border-color);background:var(--color-surface);color:var(--color-text-primary)}
html[data-theme="dark"] .review-step:hover,
html[data-theme="dark"] .review-toggle-btn:hover,
html[data-theme="dark"] .profile-option:hover,
html[data-theme="dark"] .conflict-option:hover{background:var(--color-surface-hover)}
html[data-theme="dark"] .review-step.active,
html[data-theme="dark"] .review-toggle-btn.active{border-color:rgba(96,165,250,.58);background:rgba(59,130,246,.22);color:#dbeafe}
html[data-theme="dark"] .review-step.is-disabled{opacity:.52}
html[data-theme="dark"] .review-state{color:var(--color-text-secondary)}
html[data-theme="dark"] .review-banner,
html[data-theme="dark"] .review-alert,
html[data-theme="dark"] .review-section,
html[data-theme="dark"] .conflict-card{border-color:var(--border-color);background:var(--color-surface-muted)}
html[data-theme="dark"] .review-banner.is-warning,
html[data-theme="dark"] .conflict-card{border-color:rgba(250,204,21,.35);background:rgba(82,61,10,.22)}
html[data-theme="dark"] .review-pill{color:var(--color-text-secondary)}
html[data-theme="dark"] .review-pill.is-success{border-color:rgba(34,197,94,.45);background:rgba(34,197,94,.2);color:#bbf7d0}
html[data-theme="dark"] .review-pill.is-warning{border-color:rgba(245,158,11,.45);background:rgba(245,158,11,.2);color:#fde68a}
html[data-theme="dark"] .review-list{color:var(--color-text-secondary)}
html[data-theme="dark"] .review-field span{color:var(--color-text-secondary)}
html[data-theme="dark"] .review-field input,
html[data-theme="dark"] .review-field select,
html[data-theme="dark"] .review-field textarea{border-color:var(--border-color);background:var(--color-surface);color:var(--color-text-primary)}
html[data-theme="dark"] .review-field input::placeholder,
html[data-theme="dark"] .review-field textarea::placeholder{color:var(--color-text-muted)}
html[data-theme="dark"] .review-field input:focus,
html[data-theme="dark"] .review-field select:focus,
html[data-theme="dark"] .review-field textarea:focus{box-shadow:0 0 0 3px rgba(96,165,250,.3)}
html[data-theme="dark"] .review-field .is-attention{border-color:rgba(245,158,11,.62);background:rgba(120,53,15,.22)}
html[data-theme="dark"] .review-entry{border-color:var(--border-color);background:var(--color-surface)}
html[data-theme="dark"] .review-entry summary{border-bottom-color:var(--border-color)}
html[data-theme="dark"] .review-inline-btn{color:#fecaca;background:rgba(127,29,29,.42);border-color:rgba(248,113,113,.42)}
html[data-theme="dark"] .review-toggle{border-color:var(--border-color);background:var(--color-surface-muted)}
html[data-theme="dark"] .profile-option.is-selected,
html[data-theme="dark"] .conflict-option.is-selected{border-color:rgba(96,165,250,.62);background:rgba(59,130,246,.22);box-shadow:0 0 0 3px rgba(59,130,246,.22)}
html[data-theme="dark"] .conflict-option-title{color:var(--color-text-primary)}
html[data-theme="dark"] .conflict-option code{background:rgba(2,6,23,.46);color:#e2e8f0}
</style>
