export const showToast = (message) => {
  if (global.toast) {
    global.toast.showToast(message);
  }
};

export const showSuccessToast = (message) => {
  if (global.toast) {
    global.successToast.showToast(message);
  }
};

export const showWarningToast = (message) => {
  if (global.warningToast) {
    global.warningToast.showToast(message);
  }
};

export const showErrorToast = (message) => {
  if (global.errorToast) {
    global.errorToast.showToast(message);
  }
};
