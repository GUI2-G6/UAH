<template>
  <div class="popup-shell">
    <header v-if="surface === 'popup'" class="hero-card">
      <div>
        <p class="eyebrow">UAH Browser Companion</p>
        <h1>Quick Applicant Access</h1>
        <p class="hero-copy">
          Reference your profiles and resume details while browsing job boards, then jump back into the full UAH app when you need more.
        </p>
      </div>
      <div class="hero-actions">
        <button class="btn-secondary btn-compact" :disabled="pinBusy" @click="togglePinnedMode">
          {{ pinBusy ? 'Saving…' : pinEnabled ? 'Unpin' : 'Pin' }}
        </button>
        <button class="btn-secondary btn-compact" @click="closePopupSurface">Close</button>
        <button class="btn-secondary btn-compact" @click="openFullApp('/home')">Open UAH</button>
      </div>
    </header>

    <section v-if="booting" class="state-card">
      <h2>Checking your session</h2>
      <p>Confirming whether your saved UAH extension session is still valid.</p>
    </section>

    <section v-else-if="!authenticated" class="auth-card">
      <div class="panel-heading">
        <div>
          <p class="panel-kicker">Account</p>
          <h2>Sign in to UAH</h2>
        </div>
      </div>

      <p class="auth-copy">
        The extension uses your existing UAH backend account and stores only extension auth metadata locally.
      </p>

      <form class="auth-form" @submit.prevent="handleLogin">
        <label class="field-group">
          <span>Email</span>
          <input
            v-model.trim="email"
            type="email"
            autocomplete="username"
            placeholder="you@example.com"
            :disabled="authBusy"
          />
        </label>

        <label class="field-group">
          <span>Password</span>
          <input
            v-model="password"
            type="password"
            autocomplete="current-password"
            placeholder="Password"
            :disabled="authBusy"
          />
        </label>

        <button class="btn-primary" type="submit" :disabled="authBusy">
          {{ authBusy ? 'Signing in…' : 'Sign in' }}
        </button>
      </form>

      <div class="auth-divider"><span>or</span></div>

      <button class="btn-secondary" :disabled="authBusy" @click="handleGoogleLogin">
        {{ googleBusy ? 'Completing Google sign-in…' : 'Continue with Google' }}
      </button>

      <div v-if="authError" class="inline-banner inline-banner--error">
        {{ authError }}
      </div>

      <div class="footer-actions">
        <button class="text-link" @click="openFullApp('/login')">Open full sign-in page</button>
        <button class="text-link" @click="openFullApp('/register')">Create an account</button>
      </div>
    </section>

    <template v-else>
      <section class="account-strip">
        <div>
          <p class="account-name">{{ displayUserName(currentUser) }}</p>
          <p class="account-email">{{ currentUser?.email }}</p>
        </div>
        <div class="account-meta">
          <span class="status-pill status-pill--success">Signed in</span>
          <span class="status-note">Expires {{ formatDateTime(expiresAt) }}</span>
        </div>
      </section>

      <nav class="tab-row" aria-label="Extension sections">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          :class="['tab-button', { active: activeTab === tab.key }]"
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
        </button>
      </nav>

      <div
        v-if="feedbackMessage"
        :class="['inline-banner', feedbackType === 'error' ? 'inline-banner--error' : 'inline-banner--success']"
      >
        {{ feedbackMessage }}
      </div>

      <section v-if="activeTab === 'profiles'" class="panel-stack">
        <div class="panel-card">
          <div class="panel-heading panel-heading--compact">
            <div>
              <p class="panel-kicker">Active profile</p>
              <h2>Quick source + page actions</h2>
            </div>
            <div class="panel-heading-actions">
              <span class="status-pill">Profile</span>
              <button class="text-link" @click="refreshProfiles">Refresh</button>
            </div>
          </div>

          <div v-if="profilesLoading && !profiles.length" class="state-card state-card--nested">
            <p>Loading your profile options…</p>
          </div>
          <div v-else-if="profilesError" class="inline-banner inline-banner--error">{{ profilesError }}</div>
          <div v-else-if="!profiles.length" class="empty-card">
            <p>No applicant profiles are available yet.</p>
            <button class="text-link" @click="openFullApp('/resumes')">Create one in the full app</button>
          </div>
          <div v-else class="detail-stack">
            <label class="field-group">
              <span>Use this profile in the extension</span>
              <select
                class="field-select"
                :value="selectedProfile?.id || ''"
                :disabled="!profiles.length || profileDetailLoading"
                @change="handleProfilePickerChange"
              >
                <option value="" disabled>Select a profile</option>
                <option v-for="profile in profiles" :key="profile.id" :value="profile.id">
                  {{ profile.name || [profile.first_name, profile.last_name].filter(Boolean).join(' ') || 'Untitled profile' }}
                </option>
              </select>
            </label>

            <div class="autofill-card autofill-card--compact">
              <div class="copy-card-header">
                <div>
                  <p class="detail-label">Manual page scan</p>
                  <p class="autofill-copy">
                    Uses {{ autofillSource?.source?.profileName || 'the selected profile' }}
                    and {{ autofillSource?.tokenCount || 0 }} prepared values from UAH.
                  </p>
                </div>
              </div>

              <div class="autofill-actions">
                <button
                  class="btn-secondary"
                  :disabled="Boolean(autofillBusy)"
                  @click="runProfileAutofill('navigatePreviousPage')"
                >
                  {{ autofillBusy === 'navigatePreviousPage' ? 'Going back…' : 'Previous page' }}
                </button>
                <button
                  class="btn-secondary"
                  :disabled="Boolean(autofillBusy)"
                  @click="runProfileAutofill('navigateNextPage')"
                >
                  {{ autofillBusy === 'navigateNextPage' ? 'Advancing…' : 'Next page' }}
                </button>
                <button
                  class="btn-primary"
                  :disabled="!autofillSource || Boolean(autofillBusy)"
                  @click="runProfileAutofill('autofillScan')"
                >
                  {{ autofillBusy === 'autofillScan' ? 'Scanning…' : 'Scan page' }}
                </button>
                <button
                  class="btn-secondary"
                  :disabled="!autofillSource || Boolean(autofillBusy)"
                  @click="runProfileAutofill('autofillFill')"
                >
                  {{ autofillBusy === 'autofillFill' ? 'Filling…' : 'Fill page' }}
                </button>
              </div>

              <div
                v-if="autofillStatusMessage"
                :class="['inline-banner', autofillStatusType === 'error' ? 'inline-banner--error' : 'inline-banner--success']"
              >
                {{ autofillStatusMessage }}
              </div>
            </div>
          </div>
        </div>

        <div class="panel-card">
          <div class="panel-heading">
            <div>
              <p class="panel-kicker">Profile details</p>
              <h2>{{ selectedProfile?.name || 'Profile' }}</h2>
            </div>
            <button class="text-link" @click="openFullApp('/resumes')">Open full editor</button>
          </div>

          <div v-if="profileDetailLoading" class="state-card state-card--nested">
            <p>Loading this profile…</p>
          </div>
          <div v-else-if="profileDetailError" class="inline-banner inline-banner--error">{{ profileDetailError }}</div>
          <div v-else-if="selectedProfile" class="detail-stack">
            <div class="detail-grid">
              <div v-for="field in profileFields" :key="field.label" class="detail-row">
                <div>
                  <p class="detail-label">{{ field.label }}</p>
                  <p class="detail-value">{{ field.value }}</p>
                </div>
                <button class="copy-button" :disabled="!field.canCopy" @click="copyText(field.copyValue, field.label)">
                  Copy
                </button>
              </div>
            </div>

            <div v-for="block in profileBlocks" :key="block.label" class="copy-card">
              <div class="copy-card-header">
                <div>
                  <p class="detail-label">{{ block.label }}</p>
                </div>
                <button class="copy-button" :disabled="!block.copyValue" @click="copyText(block.copyValue, block.label)">
                  Copy
                </button>
              </div>
              <p class="copy-card-body">{{ block.value }}</p>
            </div>
          </div>
          <div v-else class="empty-card">
            <p>Select a profile to view its quick-reference details.</p>
          </div>
        </div>
      </section>

      <section v-else-if="activeTab === 'resumes'" class="panel-stack">
        <div class="panel-card">
          <div class="panel-heading">
            <div>
              <p class="panel-kicker">Resumes</p>
              <h2>Your parsed resume library</h2>
            </div>
            <button class="text-link" @click="refreshResumes">Refresh</button>
          </div>

          <div v-if="resumesLoading" class="state-card state-card--nested">
            <p>Loading your resumes…</p>
          </div>
          <div v-else-if="resumesError" class="inline-banner inline-banner--error">{{ resumesError }}</div>
          <div v-else-if="!resumes.length" class="empty-card">
            <p>No resumes are saved yet.</p>
            <button class="text-link" @click="openFullApp('/resumes')">Upload one in the full app</button>
          </div>
          <div v-else class="selection-list">
            <button
              v-for="resume in resumes"
              :key="resume.id"
              :class="['selection-item', { active: selectedResume?.id === resume.id }]"
              @click="selectResume(resume.id)"
            >
              <div>
                <p class="selection-title">{{ resume.file_name }}</p>
                <p class="selection-subtitle">Added {{ formatDateTime(resume.created_at) }}</p>
              </div>
              <span :class="['status-pill', resume.portal_ready ? 'status-pill--success' : 'status-pill--warning']">
                {{ resume.portal_ready ? 'Ready' : 'Needs fields' }}
              </span>
            </button>
          </div>
        </div>

        <div class="panel-card">
          <div class="panel-heading">
            <div>
              <p class="panel-kicker">Resume details</p>
              <h2>{{ selectedResume?.file_name || 'Resume' }}</h2>
            </div>
            <button class="text-link" @click="openFullApp('/resumes')">Open resume workspace</button>
          </div>

          <div v-if="resumeDetailLoading" class="state-card state-card--nested">
            <p>Loading this resume…</p>
          </div>
          <div v-else-if="resumeDetailError" class="inline-banner inline-banner--error">{{ resumeDetailError }}</div>
          <div v-else-if="selectedResume" class="detail-stack">
            <div class="detail-grid">
              <div v-for="field in resumeFields" :key="field.label" class="detail-row">
                <div>
                  <p class="detail-label">{{ field.label }}</p>
                  <p class="detail-value">{{ field.value }}</p>
                </div>
                <button class="copy-button" :disabled="!field.canCopy" @click="copyText(field.copyValue, field.label)">
                  Copy
                </button>
              </div>
            </div>

            <div v-for="block in resumeBlocks" :key="block.label" class="copy-card">
              <div class="copy-card-header">
                <div>
                  <p class="detail-label">{{ block.label }}</p>
                </div>
                <button class="copy-button" :disabled="!block.copyValue" @click="copyText(block.copyValue, block.label)">
                  Copy
                </button>
              </div>
              <p class="copy-card-body">{{ block.value }}</p>
            </div>
          </div>
          <div v-else class="empty-card">
            <p>Select a resume to view its parsed summary.</p>
          </div>
        </div>
      </section>

      <section v-else class="panel-stack">
        <div class="panel-card">
          <div class="panel-heading">
            <div>
              <p class="panel-kicker">Account</p>
              <h2>Session and connected sign-in methods</h2>
            </div>
            <button class="text-link" @click="refreshAccount">Refresh</button>
          </div>

          <div class="detail-grid">
            <div class="detail-row">
              <div>
                <p class="detail-label">Signed in as</p>
                <p class="detail-value">{{ displayUserName(currentUser) }}</p>
              </div>
              <button class="copy-button" @click="copyText(currentUser?.email, 'account email')">Copy</button>
            </div>
            <div class="detail-row">
              <div>
                <p class="detail-label">Email</p>
                <p class="detail-value">{{ currentUser?.email }}</p>
              </div>
              <button class="copy-button" @click="copyText(currentUser?.email, 'account email')">Copy</button>
            </div>
            <div class="detail-row">
              <div>
                <p class="detail-label">Extension session</p>
                <p class="detail-value">Expires {{ formatDateTime(expiresAt) }}</p>
              </div>
              <button class="copy-button" disabled>Managed</button>
            </div>
          </div>

          <div v-if="accountLoading" class="state-card state-card--nested">
            <p>Refreshing account status…</p>
          </div>
          <div v-else-if="accountError" class="inline-banner inline-banner--error">{{ accountError }}</div>
          <div v-else-if="connectedAccounts?.providers?.length" class="selection-list selection-list--static">
            <div
              v-for="provider in connectedAccounts.providers"
              :key="provider.provider"
              class="selection-item selection-item--static"
            >
              <div>
                <p class="selection-title">{{ provider.label }}</p>
                <p class="selection-subtitle">
                  {{
                    provider.connected
                      ? provider.account_email || 'Connected'
                      : provider.coming_soon
                        ? 'Coming soon'
                        : 'Not connected'
                  }}
                </p>
              </div>
              <span :class="['status-pill', provider.connected ? 'status-pill--success' : 'status-pill--warning']">
                {{ provider.connected ? 'Connected' : 'Not connected' }}
              </span>
            </div>
          </div>

          <div class="footer-actions">
            <button class="text-link" @click="openFullApp('/settings')">Open settings</button>
            <button class="text-link" @click="openFullApp('/home')">Open dashboard</button>
            <button class="text-link text-link--danger" @click="handleLogout">Sign out</button>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'

import { buildProfileAutofillSource } from '@/autofill/source'
import { requestBackground } from '@/lib/messages'
import {
  buildProfileLinks,
  buildProfileLocation,
  buildResumeLocation,
  buildResumeName,
  displayUserName,
  displayValue,
  flattenResumeSkills,
  formatDateTime,
  summarizeEducation,
  summarizeWork,
} from '@/lib/formatters'

const props = defineProps({
  surface: {
    type: String,
    default: 'popup',
  },
})

const tabs = [
  { key: 'profiles', label: 'Profiles' },
  { key: 'resumes', label: 'Resumes' },
  { key: 'account', label: 'Account' },
]

const booting = ref(true)
const authenticated = ref(false)
const currentUser = ref(null)
const expiresAt = ref(null)
const activeTab = ref('profiles')
const feedbackMessage = ref('')
const feedbackType = ref('success')

const email = ref('')
const password = ref('')
const authBusy = ref(false)
const googleBusy = ref(false)
const authError = ref('')

const profiles = ref([])
const profilesLoading = ref(false)
const profilesError = ref('')
const selectedProfile = ref(null)
const profileDetailLoading = ref(false)
const profileDetailError = ref('')
const autofillBusy = ref('')
const autofillStatusMessage = ref('')
const autofillStatusType = ref('')

const resumes = ref([])
const resumesLoading = ref(false)
const resumesError = ref('')
const selectedResume = ref(null)
const resumeDetailLoading = ref(false)
const resumeDetailError = ref('')

const connectedAccounts = ref(null)
const accountLoading = ref(false)
const accountError = ref('')
const pinEnabled = ref(false)
const pinBusy = ref(false)

function setFeedback(message = '', type = 'success') {
  feedbackMessage.value = message
  feedbackType.value = type
  if (!message) return
  window.clearTimeout(setFeedback.timer)
  setFeedback.timer = window.setTimeout(() => {
    feedbackMessage.value = ''
    feedbackType.value = 'success'
  }, 2200)
}

function setAutofillStatus(message = '', type = '') {
  autofillStatusMessage.value = message
  autofillStatusType.value = type
}

function formatAutofillResult(action, result = {}) {
  if (action === 'autofillScan') {
    return `Scanned ${result.total ?? 0} fields. ${result.matched ?? 0} matched, ${result.review ?? 0} review, ${result.missing ?? 0} missing.`
  }
  if (action === 'autofillFill') {
    return `Filled ${result.filled ?? 0} of ${result.total ?? 0} planned fields.`
  }
  if (action === 'navigatePreviousPage') {
    return result?.usedHistory
      ? 'Went back using browser history.'
      : 'Moved to the previous application step.'
  }
  if (action === 'navigateNextPage') {
    return 'Moved to the next application step.'
  }
  return 'Updated autofill state for the active page.'
}

async function copyText(value, label) {
  const normalized = String(value || '').trim()
  if (!normalized) return
  await navigator.clipboard.writeText(normalized)
  setFeedback(`Copied ${label}.`)
}

async function openFullApp(pathname) {
  await requestBackground('openFullApp', { pathname })
}

async function hydratePinnedUiState() {
  try {
    const state = await requestBackground('getPinnedUiState')
    pinEnabled.value = Boolean(state?.pinEnabled)
  } catch {
    pinEnabled.value = false
  }
}

async function togglePinnedMode() {
  pinBusy.value = true

  try {
    const nextState = await requestBackground('setPinnedUiState', {
      pinEnabled: !pinEnabled.value,
    })
    pinEnabled.value = Boolean(nextState?.pinEnabled)
    setFeedback(
      pinEnabled.value ? 'Pinned panel enabled for supported tabs.' : 'Pinned panel disabled.',
      'success',
    )
  } catch (error) {
    setFeedback(String(error?.message || error), 'error')
  } finally {
    pinBusy.value = false
  }
}

function closePopupSurface() {
  window.close()
}

function applyAuthFailure(error) {
  if (error?.code !== 'AUTH_REQUIRED' && error?.status !== 401) {
    return false
  }

  authenticated.value = false
  currentUser.value = null
  expiresAt.value = null
  profiles.value = []
  resumes.value = []
  selectedProfile.value = null
  selectedResume.value = null
  connectedAccounts.value = null
  authError.value = String(error?.message || error)
  return true
}

async function bootstrap() {
  booting.value = true
  authError.value = ''

  try {
    const session = await requestBackground('bootstrap')
    authenticated.value = Boolean(session.authenticated)
    currentUser.value = session.user || null
    expiresAt.value = session.expiresAt || null

    if (!session.authenticated) {
      profiles.value = []
      selectedProfile.value = null
      resumes.value = []
      selectedResume.value = null
      connectedAccounts.value = null
    }
  } catch (error) {
    authenticated.value = false
    currentUser.value = null
    expiresAt.value = null
    authError.value = String(error?.message || error)
  } finally {
    booting.value = false
  }
}

async function handleLogin() {
  authBusy.value = true
  authError.value = ''

  try {
    const session = await requestBackground('login', {
      email: email.value,
      password: password.value,
    })
    authenticated.value = true
    currentUser.value = session.user
    expiresAt.value = session.expiresAt
    password.value = ''
    activeTab.value = 'profiles'
    await loadProfiles()
  } catch (error) {
    authError.value = String(error?.message || error)
  } finally {
    authBusy.value = false
  }
}

async function handleGoogleLogin() {
  authBusy.value = true
  googleBusy.value = true
  authError.value = ''

  try {
    const session = await requestBackground('loginWithGoogle')
    authenticated.value = true
    currentUser.value = session.user
    expiresAt.value = session.expiresAt
    activeTab.value = 'profiles'
    await loadProfiles()
  } catch (error) {
    authError.value = String(error?.message || error)
  } finally {
    authBusy.value = false
    googleBusy.value = false
  }
}

async function handleLogout() {
  await requestBackground('logout')
  authenticated.value = false
  currentUser.value = null
  expiresAt.value = null
  selectedProfile.value = null
  selectedResume.value = null
  profiles.value = []
  resumes.value = []
  connectedAccounts.value = null
  email.value = ''
  password.value = ''
  setAutofillStatus()
}

async function loadProfiles(force = false) {
  profilesLoading.value = true
  profilesError.value = ''

  try {
    const list = await requestBackground('getProfiles', { force })
    profiles.value = Array.isArray(list) ? list : []

    const defaultProfile = profiles.value.find((profile) => profile.is_active) || profiles.value[0] || null
    if (defaultProfile) {
      await selectProfile(defaultProfile.id)
    } else {
      selectedProfile.value = null
    }
  } catch (error) {
    if (applyAuthFailure(error)) return
    profilesError.value = String(error?.message || error)
  } finally {
    profilesLoading.value = false
  }
}

async function selectProfile(profileId, force = false) {
  if (!profileId) return
  profileDetailLoading.value = true
  profileDetailError.value = ''

  try {
    selectedProfile.value = await requestBackground('getProfile', { profileId, force })
  } catch (error) {
    if (applyAuthFailure(error)) return
    profileDetailError.value = String(error?.message || error)
  } finally {
    profileDetailLoading.value = false
  }
}

async function refreshProfiles() {
  await loadProfiles(true)
}

async function handleProfilePickerChange(event) {
  const profileId = Number(event?.target?.value)
  if (!Number.isFinite(profileId)) return
  await selectProfile(profileId)
}

async function loadResumes(force = false) {
  resumesLoading.value = true
  resumesError.value = ''

  try {
    const list = await requestBackground('getResumes', { force })
    resumes.value = Array.isArray(list) ? list : []
    const defaultResume = resumes.value[0] || null
    if (defaultResume) {
      await selectResume(defaultResume.id)
    } else {
      selectedResume.value = null
    }
  } catch (error) {
    if (applyAuthFailure(error)) return
    resumesError.value = String(error?.message || error)
  } finally {
    resumesLoading.value = false
  }
}

async function selectResume(resumeId, force = false) {
  if (!resumeId) return
  resumeDetailLoading.value = true
  resumeDetailError.value = ''

  try {
    selectedResume.value = await requestBackground('getResume', { resumeId, force })
  } catch (error) {
    if (applyAuthFailure(error)) return
    resumeDetailError.value = String(error?.message || error)
  } finally {
    resumeDetailLoading.value = false
  }
}

async function refreshResumes() {
  await loadResumes(true)
}

async function loadAccount(force = false) {
  accountLoading.value = true
  accountError.value = ''

  try {
    connectedAccounts.value = await requestBackground('getConnectedAccounts', { force })
  } catch (error) {
    if (applyAuthFailure(error)) return
    accountError.value = String(error?.message || error)
  } finally {
    accountLoading.value = false
  }
}

async function refreshAccount() {
  await loadAccount(true)
}

const autofillSource = computed(() => {
  if (!selectedProfile.value) return null
  return buildProfileAutofillSource(selectedProfile.value)
})

async function runProfileAutofill(action) {
  if (
    !selectedProfile.value
    && action !== 'autofillGetStats'
    && action !== 'navigatePreviousPage'
    && action !== 'navigateNextPage'
  ) return
  autofillBusy.value = action
  setAutofillStatus()

  try {
    const payload = action === 'autofillScan' || action === 'autofillFill'
      ? {
          source: autofillSource.value?.source || null,
          tokenMap: autofillSource.value?.tokenMap || null,
        }
      : {}
    const result = await requestBackground(action, payload)
    setAutofillStatus(formatAutofillResult(action, result), 'success')
  } catch (error) {
    if (applyAuthFailure(error)) return
    setAutofillStatus(String(error?.message || error), 'error')
  } finally {
    autofillBusy.value = ''
  }
}

watch(activeTab, async (tab) => {
  if (!authenticated.value) return
  if (tab === 'profiles' && !profiles.value.length && !profilesLoading.value) {
    await loadProfiles()
  }
  if (tab === 'resumes' && !resumes.value.length && !resumesLoading.value) {
    await loadResumes()
  }
  if (tab === 'account' && !connectedAccounts.value && !accountLoading.value) {
    await loadAccount()
  }
})

watch(() => selectedProfile.value?.id, () => {
  setAutofillStatus()
})

const profileFields = computed(() => {
  const profile = selectedProfile.value || {}
  const fullName = [profile.first_name, profile.last_name].filter(Boolean).join(' ')
  const location = buildProfileLocation(profile)

  return [
    { label: 'Name', value: displayValue(fullName), copyValue: fullName, canCopy: Boolean(fullName) },
    { label: 'Email', value: displayValue(profile.email), copyValue: profile.email, canCopy: Boolean(profile.email) },
    { label: 'Phone', value: displayValue(profile.phone), copyValue: profile.phone, canCopy: Boolean(profile.phone) },
    { label: 'Location', value: displayValue(location), copyValue: location, canCopy: Boolean(location) },
    { label: 'Target role', value: displayValue(profile.job_title), copyValue: profile.job_title, canCopy: Boolean(profile.job_title) },
    { label: 'Work auth', value: displayValue(profile.work_auth), copyValue: profile.work_auth, canCopy: Boolean(profile.work_auth) },
  ]
})

const profileBlocks = computed(() => {
  const profile = selectedProfile.value || {}
  const links = buildProfileLinks(profile)
  return [
    { label: 'Summary', value: displayValue(profile.summary), copyValue: profile.summary },
    { label: 'Skills', value: displayValue(profile.skills_text), copyValue: profile.skills_text },
    { label: 'Professional links', value: displayValue(links), copyValue: links },
  ]
})

const resumeFields = computed(() => {
  const structured = selectedResume.value?.structured_data || {}
  const personalInfo = structured.personal_info || {}
  const combinedSkills = flattenResumeSkills(structured.skills || {})
  const resumeName = buildResumeName(personalInfo)
  const location = buildResumeLocation(personalInfo)

  return [
    { label: 'Name', value: displayValue(resumeName), copyValue: resumeName, canCopy: Boolean(resumeName) },
    { label: 'Email', value: displayValue(personalInfo.email), copyValue: personalInfo.email, canCopy: Boolean(personalInfo.email) },
    { label: 'Phone', value: displayValue(personalInfo.phone), copyValue: personalInfo.phone, canCopy: Boolean(personalInfo.phone) },
    { label: 'Location', value: displayValue(location), copyValue: location, canCopy: Boolean(location) },
    {
      label: 'Portal readiness',
      value: selectedResume.value?.portal_ready ? 'Ready for portal checks' : 'Needs additional required fields',
      copyValue: '',
      canCopy: false,
    },
    {
      label: 'Parse method',
      value: displayValue(selectedResume.value?.parse_method, 'Unknown'),
      copyValue: selectedResume.value?.parse_method || '',
      canCopy: Boolean(selectedResume.value?.parse_method),
    },
    {
      label: 'Skills count',
      value: combinedSkills.length ? `${combinedSkills.length} extracted skill${combinedSkills.length === 1 ? '' : 's'}` : 'No skills extracted yet',
      copyValue: combinedSkills.join(', '),
      canCopy: combinedSkills.length > 0,
    },
  ]
})

const resumeBlocks = computed(() => {
  const structured = selectedResume.value?.structured_data || {}
  const combinedSkills = flattenResumeSkills(structured.skills || {})
  const educationSnapshot = summarizeEducation(structured.education || []).join('\n')
  const workSnapshot = summarizeWork(structured.work_experience || []).join('\n')

  return [
    { label: 'Summary', value: displayValue(structured.summary), copyValue: structured.summary },
    { label: 'Skills', value: displayValue(combinedSkills.join(', ')), copyValue: combinedSkills.join(', ') },
    { label: 'Education snapshot', value: displayValue(educationSnapshot), copyValue: educationSnapshot },
    { label: 'Work snapshot', value: displayValue(workSnapshot), copyValue: workSnapshot },
  ]
})

onMounted(async () => {
  await hydratePinnedUiState()
  await bootstrap()
  if (authenticated.value) {
    await loadProfiles()
  }
})
</script>
