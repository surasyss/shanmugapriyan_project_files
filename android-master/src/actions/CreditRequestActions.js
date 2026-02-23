import api from '../api';
import Urls from '../api/urls';
import { parseUrl } from '../utils/StringFormatter';
import { MixpanelEvents, sendMixpanelEvent } from '../utils/mixpanel/MixPanelAdapter';
import showAlert from '../utils/QubiqleAlert';
import { showSuccessToast } from '../utils/Toaster';

export const LOAD_ALL_CREDIT_REQUESTS = 'load_all_credit_requests';
export const LOAD_ALL_CREDIT_REQUESTS_SUCCESS = 'load_all_credit_requests_success';
export const LOAD_ALL_CREDIT_REQUESTS_FAIL = 'load_all_credit_requests_fail';
export const RESET_ALL_CREDIT_REQUESTS = 'reset_all_credit_requests';

export const LOAD_CREDIT_REQUEST_DETAILS = 'load_credit_request_details';
export const LOAD_CREDIT_REQUEST_DETAILS_SUCCESS = 'load_credit_request_details_success';
export const LOAD_CREDIT_REQUEST_DETAILS_FAIL = 'load_credit_request_details_fail';

export const SET_CURRENT_CREDIT_REQUEST = 'set_current_credit_request';
export const SET_ADD_CREDIT_REQUEST_DATA = 'set_add_credit_request_data';

export const ADD_CREDIT_REQUEST_FLAG = 'add_credit_request_flag';
export const ADD_CREDIT_REQUEST_FLAG_SUCCESS = 'add_credit_request_flag_success';

export const RESOLVE_CREDIT_REQUEST_FLAG = 'resolve_credit_request_flag';
export const RESOLVE_CREDIT_REQUEST_FLAG_SUCCESS = 'resolve_credit_request_flag_success';

export const CREATE_CREDIT_REQUEST = 'create_credit_request';
export const CREATE_CREDIT_REQUEST_SUCCESS = 'create_credit_request_success';
export const CREATE_CREDIT_REQUEST_FAIL = 'create_credit_request_fail';

export const loadAllCreditRequests = (filters) => {
  const body = {
    page: 1,
    sort_order: 'desc',
    sort_by: 'date',
    dashboard_invoice_state: 'other_documents',
    invoice_type: 'credit request',
    limit: 30
  };

  Object.keys(filters).forEach((key) => {
    body[key] = filters[key];
  });

  return async (dispatch) => {
    dispatch({
      type: LOAD_ALL_CREDIT_REQUESTS,
      payload: { firstLoad: body.page === 1 }
    });

    const {
      statusCode, errorMessage, data
    } = await api({
      method: 'GET',
      url: Urls.INVOICES,
      params: body
    });

    if (statusCode === 200) {
      dispatch({ type: LOAD_ALL_CREDIT_REQUESTS_SUCCESS, payload: data });
    } else {
      dispatch({
        type: LOAD_ALL_CREDIT_REQUESTS_FAIL,
        payload: { error: errorMessage }
      });
    }
  };
};

export const resetAllCreditRequests = () => async (dispatch) => {
  dispatch({ type: RESET_ALL_CREDIT_REQUESTS });
};

export const loadCreditRequestDetails = (invoice_id) => async (dispatch) => {
  dispatch({
    type: LOAD_CREDIT_REQUEST_DETAILS
  });

  const lineItemsResponse = await api({
    method: 'GET',
    url: parseUrl(Urls.INVOICE_LINE_ITEMS, { invoice_id })
  });

  const glSplitsReponse = await api({
    method: 'GET',
    url: parseUrl(Urls.INVOICE_GL_SPLITS, { invoice_id })
  });

  const imagesResponse = await api({
    method: 'GET',
    url: parseUrl(Urls.INVOICE_IMAGES, { invoice_id })
  });

  const historyResponse = await api({
    method: 'GET',
    url: parseUrl(Urls.INVOICE_HISTORY, { invoice_id })
  });

  const credit_requestReponse = await api({
    method: 'GET',
    url: parseUrl(Urls.INVOICE_DETAILS, { invoice_id })
  });

  if (credit_requestReponse.statusCode !== 200) {
    dispatch({
      type: LOAD_CREDIT_REQUEST_DETAILS_FAIL,
      payload: { error: credit_requestReponse.errorMessage }
    });
    return;
  }

  dispatch({
    type: LOAD_CREDIT_REQUEST_DETAILS_SUCCESS,
    payload: {
      line_items: lineItemsResponse.data,
      gl_splits: glSplitsReponse.data.splits || glSplitsReponse.data,
      images: imagesResponse.data,
      links: credit_requestReponse.data.links,
      history: historyResponse.data,
      invoice_id
    }
  });
};

export const setCurrentCreditRequest = (index) => async (dispatch) => {
  dispatch({
    type: SET_CURRENT_CREDIT_REQUEST,
    payload: { index }
  });
};

export const addCreditRequestFlag = (invoice_id, flagging_reason) => async (dispatch) => {
  dispatch({
    type: ADD_CREDIT_REQUEST_FLAG
  });

  sendMixpanelEvent(MixpanelEvents.INVOICE_FLAGGED, { credit_request_id: invoice_id });
  const {
    statusCode
  } = await api({
    method: 'POST',
    url: parseUrl(Urls.ADD_INVOICE_FLAG, { invoice_id }),
    data: { flagging_reason }
  });

  if (statusCode === 200) {
    dispatch({
      type: ADD_CREDIT_REQUEST_FLAG_SUCCESS,
      payload: {
        invoice_id
      }
    });
    dispatch(loadCreditRequestDetails(invoice_id));
  }
};

export const resolveCreditRequestFlag = (invoice_id, resolution_reason) => async (dispatch) => {
  dispatch({
    type: RESOLVE_CREDIT_REQUEST_FLAG
  });

  sendMixpanelEvent(MixpanelEvents.CREDIT_REQUESTS_FLAGGED, { credit_request_id: invoice_id });
  const {
    statusCode
  } = await api({
    method: 'POST',
    url: parseUrl(Urls.RESOLVE_INVOICE_FLAG, { invoice_id }),
    data: { resolution_reason }
  });

  if (statusCode === 200) {
    dispatch({
      type: RESOLVE_CREDIT_REQUEST_FLAG_SUCCESS,
      payload: {
        invoice_id
      }
    });
    dispatch(loadCreditRequestDetails(invoice_id));
  }
};

export const setAddCreditRequestData = (key, value) => async (dispatch) => {
  dispatch({
    type: SET_ADD_CREDIT_REQUEST_DATA,
    payload: { key, value }
  });
};

export const createCreditRequest = (data) => async (dispatch) => {
  dispatch({
    type: CREATE_CREDIT_REQUEST
  });

  sendMixpanelEvent(MixpanelEvents.CREDIT_REQUESTS_CREATED);
  const {
    statusCode, errorMessage
  } = await api({
    method: 'POST',
    url: Urls.INVOICES,
    data
  });

  if (statusCode === 200 || statusCode === 201) {
    await dispatch({
      type: CREATE_CREDIT_REQUEST_SUCCESS
    });
    dispatch(loadAllCreditRequests({}));
    showSuccessToast('Credit Request raised!');
  } else {
    await dispatch({
      type: CREATE_CREDIT_REQUEST_FAIL
    });
    showAlert('Credit Request Failed', errorMessage || 'Some Internal error has occurred');
  }
};
