import { reactive } from 'vue';

export const toastStore = reactive({
  message: '',
  type: 'success',
  visible: false
});

export function showToast(message, type = 'success') {
  toastStore.message = message;
  toastStore.type = type;
  toastStore.visible = true;

  setTimeout(() => toastStore.visible = false, 3000);
}