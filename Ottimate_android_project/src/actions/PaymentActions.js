import api from '../api';
import Urls from '../api/urls';
import { MixpanelEvents, sendMixpanelEvent } from '../utils/mixpanel/MixPanelAdapter';
import { parseUrl } from '../utils/StringFormatter';
import showAlert from '../utils/QubiqleAlert';
import { showSuccessToast } from '../utils/Toaster';

export const LOAD_PENDING_APPROVAL_PAYMENTS = 'load_pending_approval_payments';
export const LOAD_PENDING_APPROVAL_PAYMENTS_SUCCESS = 'load_pending_approval_payments_success';
export const LOAD_PENDING_APPROVAL_PAYMENTS_FAIL = 'load_pending_approval_payments_fail';
export const RESET_PENDING_APPROVAL_PAYMENTS = 'reset_pending_payments';

export const LOAD_ALL_PAYMENTS = 'load_all_payments';
export const LOAD_ALL_PAYMENTS_SUCCESS = 'load_all_payments_success';
export const LOAD_ALL_PAYMENTS_FAIL = 'load_all_payments_fail';
export const RESET_ALL_PAYMENTS = 'reset_all_payments';

export const SET_CURRENT_PAYMENT = 'set_current_payment';

export const APPROVE_PAYMENT = 'approve_payment';
export const APPROVE_PAYMENT_SUCCESS = 'approve_payment_success';
export const APPROVE_PAYMENT_FAIL = 'approve_payment_fail';

export const loadPendingApprovalPayments = (filters) => {
  const body = {
    page: 1,
    sort_order: 'asc',
    sort_by: 'created_date',
    status: 'pending approval',
    limit: 30
  };
  Object.keys(filters).forEach((key) => {
    body[key] = filters[key];
  });

  return async (dispatch) => {
    dispatch({
      type: LOAD_PENDING_APPROVAL_PAYMENTS,
      payload: { firstLoad: body.page === 1 }
    });

    const {
      statusCode, errorMessage, data
    } = await api({
      method: 'GET',
      url: Urls.PAYMENTS,
      params: body
    });

    if (statusCode === 200) {
      dispatch({ type: LOAD_PENDING_APPROVAL_PAYMENTS_SUCCESS, payload: data });
    } else {
      dispatch({
        type: LOAD_PENDING_APPROVAL_PAYMENTS_FAIL,
        payload: { error: errorMessage }
      });
    }
  };
};

export const resetPendingApprovalPayments = () => async (dispatch) => {
  dispatch({ type: RESET_PENDING_APPROVAL_PAYMENTS });
};

export const loadAllPayments = (filters) => {
  const body = {
    page: 1,
    sort_order: 'desc',
    sort_by: 'created_date',
    limit: 30
  };

  Object.keys(filters).forEach((key) => {
    body[key] = filters[key];
  });

  return async (dispatch) => {
    dispatch({
      type: LOAD_ALL_PAYMENTS,
      payload: { firstLoad: body.page === 1 }
    });

    const {
      statusCode, errorMessage, data
    } = await api({
      method: 'GET',
      url: Urls.PAYMENTS,
      params: body
    });

    if (statusCode === 200) {
      dispatch({ type: LOAD_ALL_PAYMENTS_SUCCESS, payload: data });
    } else {
      dispatch({
        type: LOAD_ALL_PAYMENTS_FAIL,
        payload: { error: errorMessage }
      });
    }
  };
};

export const resetAllPayments = () => async (dispatch) => {
  dispatch({ type: RESET_ALL_PAYMENTS });
};

export const setCurrentPayment = (index) => async (dispatch) => {
  dispatch({
    type: SET_CURRENT_PAYMENT,
    payload: { index }
  });
};

export const approvePayment = (payment_id, invoices) => async (dispatch) => {
  dispatch({
    type: APPROVE_PAYMENT
  });

  sendMixpanelEvent(MixpanelEvents.PAYMENT_APPROVED, { payment_id });
  const {
    statusCode, errorMessage
  } = await api({
    method: 'POST',
    url: parseUrl(Urls.APPROVE_PAYMENT, { payment_id }),
    data: { invoices }
  });

  if (statusCode === 200) {
    showSuccessToast('Payment Approved!');
    dispatch({
      type: APPROVE_PAYMENT_SUCCESS,
      payload: {
        payment_id
      }
    });
  } else {
    dispatch({
      type: APPROVE_PAYMENT_FAIL,
      payload: { error: errorMessage, payment_id }
    });
    showAlert('Approval Failed', errorMessage || 'Some Internal error has occurred');
  }
};
