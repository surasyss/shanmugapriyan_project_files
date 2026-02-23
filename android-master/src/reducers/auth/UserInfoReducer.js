import {
  LOAD_COMPANY_SUCCESS,
  LOAD_RESTAURANTS_SUCCESS,
  LOAD_USER_DETAILS,
  LOAD_USER_SUCCESS,
} from '../../actions';

const INITIAL_STATE = {
  loadingUserInfo: true,
  restaurants: [],
  showPayments: false,
  canUploadInvoice: false,
  expandGlSplits: false,
  showInvoiceHistory: false,
  showTransactions: false,
  tabs: [],
  moreTabs: [],
  companies: [],
};

export default (state = INITIAL_STATE, action) => {
  const { type, payload } = action;
  switch (type) {
    case LOAD_RESTAURANTS_SUCCESS:
      return { ...state, restaurants: payload };
    case LOAD_USER_DETAILS:
      return {
        ...state, loadingUserInfo: true, tabs: [], moreTabs: []
      };
    case LOAD_USER_SUCCESS:
      let canAccessDashboard = false;
      let showPayments = false;
      let containsBillpay = false;
      let expandGlSplits = false;
      let showInvoiceHistory = false;
      let showCreditRequest = false;
      let canAddCreditRequest = false;
      let canUploadInvoice = false;
      let showItems = false;
      let showTransactions = false;

      if (payload) {
        const { optional_features, permissions } = payload;
        if (optional_features['mobile-billpay'] && optional_features['mobile-billpay'].enabled) {
          showPayments = true;
        }
        if (optional_features['mobile-expand-glsplits'] && optional_features['mobile-expand-glsplits'].enabled) {
          expandGlSplits = true;
        }
        if (optional_features['mobile-invoice-history'] && optional_features['mobile-invoice-history'].enabled) {
          showInvoiceHistory = true;
        }
        if (optional_features['credit-request'] && optional_features['credit-request'].enabled) {
          showCreditRequest = true;
        }
        if (optional_features['mobile-items'] && optional_features['mobile-items'].enabled) {
          showItems = true;
        }
        if (optional_features['mobile-expenses-transactions'] && optional_features['mobile-expenses-transactions'].enabled) {
          showTransactions = true;
        }
        showTransactions = true;

        // eslint-disable-next-line no-restricted-syntax
        for (const permission of permissions) {
          if (permission.indexOf('accounts.can_access_dashboard') !== -1) {
            canAccessDashboard = true;
            break;
          }
        }

        // eslint-disable-next-line no-restricted-syntax
        for (const permission of permissions) {
          if (permission.indexOf('billpay.') !== -1) {
            containsBillpay = true;
            break;
          }
        }

        if (canAccessDashboard) {
          // eslint-disable-next-line no-restricted-syntax
          for (const permission of permissions) {
            if (permission.indexOf('invoices.create_invoice') !== -1) {
              canAddCreditRequest = true;
              break;
            }
          }

          // eslint-disable-next-line no-restricted-syntax
          for (const permission of permissions) {
            if (permission.indexOf('invoices.add_invoice') !== -1) {
              canUploadInvoice = true;
              break;
            }
          }
        }
      }
      const tabs = ['uploads', 'invoices'];
      const moreTabs = [];

      if (showPayments && containsBillpay) {
        tabs.push('payments');
      }
      if (showItems) {
        tabs.push('items');
      }
      if (showTransactions) {
        tabs.push('transactions');
      }
      if (showCreditRequest) {
        tabs.push('credit_request');
      }

      if (tabs.length > 5) {
        tabs.splice(4, 0, 'more');
      }

      while (tabs.length > 5) {
        const splicedItem = tabs.splice(tabs.length - 1, 1);
        moreTabs.push(splicedItem[0]);
      }
      return {
        ...state,
        loadingUserInfo: false,
        canAccessDashboard,
        showPayments: showPayments && containsBillpay,
        expandGlSplits,
        showInvoiceHistory,
        showCreditRequest,
        canAddCreditRequest,
        canUploadInvoice,
        showItems,
        showTransactions,
        tabs,
        moreTabs,
      };
    case LOAD_COMPANY_SUCCESS:
      return { ...state, companies: payload };
    default:
      return state;
  }
};
