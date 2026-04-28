import { test, expect } from '@playwright/test'

test('sensitive work authorization field is discoverable for approval gate', async ({ page }) => {
  await page.setContent(`
    <form>
      <label for="first_name">First Name</label>
      <input id="first_name" name="first_name" />
      <label for="work_auth">Authorized to work in the US?</label>
      <select id="work_auth" name="work_auth">
        <option value="">Select</option>
        <option value="yes">Yes</option>
        <option value="no">No</option>
      </select>
    </form>
  `)

  const labels = await page.locator('label').allTextContents()
  expect(labels.join(' ').toLowerCase()).toContain('authorized to work')
  await expect(page.locator('#work_auth option')).toHaveCount(3)
})

test('dropdown fallback paths remain selectable in browser context', async ({ page }) => {
  await page.setContent(`
    <label for="state">State</label>
    <select id="state" name="state">
      <option value="">Select</option>
      <option value="AL">Alabama</option>
      <option value="GA">Georgia</option>
    </select>
  `)

  await page.selectOption('#state', { label: 'Alabama' })
  await expect(page.locator('#state')).toHaveValue('AL')
})
