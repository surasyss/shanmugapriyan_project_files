import api from '../api';
import Urls from '../api/urls';
import { parseUrl } from '../utils/StringFormatter';
import showAlert from '../utils/QubiqleAlert';
import { MixpanelEvents, sendMixpanelEvent } from '../utils/mixpanel/MixPanelAdapter';

export const LOAD_PENDING_APPROVAL_INVOICES = 'load_pending_approval_invoices';
export const LOAD_PENDING_APPROVAL_INVOICES_SUCCESS = 'load_pending_approval_invoices_success';
export const LOAD_PENDING_APPROVAL_INVOICES_FAIL = 'load_pending_approval_invoices_fail';
export const RESET_PENDING_APPROVAL_INVOICES = 'reset_pending_invoices';

export const LOAD_ALL_INVOICES = 'load_all_invoices';
export const LOAD_ALL_INVOICES_SUCCESS = 'load_all_invoices_success';
export const LOAD_ALL_INVOICES_FAIL = 'load_all_invoices_fail';
export const RESET_ALL_INVOICES = 'reset_all_invoices';

export const LOAD_INVOICE_LINE_ITEMS = 'load_invoice_line_items';
export const LOAD_INVOICE_LINE_ITEMS_SUCCESS = 'load_invoice_line_items_success';
export const LOAD_INVOICE_LINE_ITEMS_FAIL = 'load_invoice_line_items_fail';

export const LOAD_INVOICE_GL_SPLITS = 'load_invoice_gl_splits';
export const LOAD_INVOICE_GL_SPLITS_SUCCESS = 'load_invoice_gl_splits_success';
export const LOAD_INVOICE_GL_SPLITS_FAIL = 'load_invoice_gl_splits_fail';

export const LOAD_INVOICE_IMAGES = 'load_invoice_images';
export const LOAD_INVOICE_IMAGES_SUCCESS = 'load_invoice_images_success';
export const LOAD_INVOICE_IMAGES_FAIL = 'load_invoice_images_fail';

export const APPROVE_INVOICE = 'approve_invoice';
export const APPROVE_INVOICE_SUCCESS = 'approve_invoice_success';
export const APPROVE_INVOICE_FAIL = 'approve_invoice_fail';

export const LOAD_INVOICE_DETAILS = 'load_invoice_details';
export const LOAD_INVOICE_DETAILS_SUCCESS = 'load_invoice_details_success';
export const LOAD_INVOICE_DETAILS_FAIL = 'load_invoice_details_fail';

export const SET_CURRENT_INVOICE = 'set_current_invoice';

export const ADD_INVOICE_FLAG = 'add_invoice_flag';
export const ADD_INVOICE_FLAG_SUCCESS = 'add_invoice_flag_success';

export const RESOLVE_INVOICE_FLAG = 'resolve_invoice_flag';
export const RESOLVE_INVOICE_FLAG_SUCCESS = 'resolve_invoice_flag_success';

export const loadPendingApprovalInvoices = (filters) => {
  const body = {
    page: 1,
    sort_order: 'desc',
    sort_by: 'date',
    dashboard_invoice_state: 'my_pending_approval',
    limit: 30
  };
  Object.keys(filters).forEach((key) => {
    body[key] = filters[key];
  });

  return async (dispatch) => {
    dispatch({
      type: LOAD_PENDING_APPROVAL_INVOICES,
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
      dispatch({ type: LOAD_PENDING_APPROVAL_INVOICES_SUCCESS, payload: data });
    } else {
      dispatch({
        type: LOAD_PENDING_APPROVAL_INVOICES_FAIL,
        payload: { error: errorMessage }
      });
    }
  };
};

export const resetPendingApprovalInvoices = () => async (dispatch) => {
  dispatch({ type: RESET_PENDING_APPROVAL_INVOICES });
};

export const loadAllInvoices = (filters) => {
  const body = {
    page: 1,
    sort_order: 'desc',
    sort_by: 'date',
    dashboard_invoice_state: 'all_documents',
    limit: 30
  };

  Object.keys(filters).forEach((key) => {
    body[key] = filters[key];
  });

  return async (dispatch) => {
    dispatch({
      type: LOAD_ALL_INVOICES,
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
      dispatch({ type: LOAD_ALL_INVOICES_SUCCESS, payload: data });
    } else {
      dispatch({
        type: LOAD_ALL_INVOICES_FAIL,
        payload: { error: errorMessage }
      });
    }
  };
};

export const resetAllInvoices = () => async (dispatch) => {
  dispatch({ type: RESET_ALL_INVOICES });
};

export const loadLineItems = (invoice_id) => async (dispatch) => {
  dispatch({
    type: LOAD_INVOICE_LINE_ITEMS
  });

  const {
    statusCode, errorMessage, data
  } = await api({
    method: 'GET',
    url: parseUrl(Urls.INVOICE_LINE_ITEMS, { invoice_id })
  });

  if (statusCode === 200) {
    dispatch({
      type: LOAD_INVOICE_LINE_ITEMS_SUCCESS,
      payload: {
        items: data,
        invoice_id
      }
    });
  } else {
    dispatch({
      type: LOAD_INVOICE_LINE_ITEMS_FAIL,
      payload: { error: errorMessage }
    });
  }
};

export const loadGlSplits = (invoice_id) => async (dispatch) => {
  dispatch({
    type: LOAD_INVOICE_GL_SPLITS
  });

  const {
    statusCode, errorMessage, data
  } = await api({
    method: 'GET',
    url: parseUrl(Urls.INVOICE_GL_SPLITS, { invoice_id })
  });

  if (statusCode === 200) {
    dispatch({
      type: LOAD_INVOICE_GL_SPLITS_SUCCESS,
      payload: {
        items: data.splits,
        invoice_id
      }
    });
  } else {
    dispatch({
      type: LOAD_INVOICE_GL_SPLITS_FAIL,
      payload: { error: errorMessage }
    });
  }
};

export const loadInvoiceImages = (invoice_id) => async (dispatch) => {
  dispatch({
    type: LOAD_INVOICE_IMAGES
  });

  const {
    statusCode, errorMessage, data
  } = await api({
    method: 'GET',
    url: parseUrl(Urls.INVOICE_IMAGES, { invoice_id })
  });

  if (statusCode === 200) {
    dispatch({
      type: LOAD_INVOICE_IMAGES_SUCCESS,
      payload: {
        items: data,
        invoice_id
      }
    });
  } else {
    dispatch({
      type: LOAD_INVOICE_IMAGES_FAIL,
      payload: { error: errorMessage }
    });
  }
};

export const loadInvoiceDetails = (invoice_id) => async (dispatch) => {
  dispatch({
    type: LOAD_INVOICE_DETAILS
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

  const invoiceReponse = await api({
    method: 'GET',
    url: parseUrl(Urls.INVOICE_DETAILS, { invoice_id })
  });

  if (invoiceReponse.statusCode !== 200) {
    dispatch({
      type: LOAD_INVOICE_DETAILS_FAIL,
      payload: { error: invoiceReponse.errorMessage }
    });
    return;
  }

  dispatch({
    type: LOAD_INVOICE_DETAILS_SUCCESS,
    payload: {
      line_items: lineItemsResponse.data,
      gl_splits: glSplitsReponse.data.splits || glSplitsReponse.data,
      images: imagesResponse.data,
      links: invoiceReponse.data.links,
      history: historyResponse.data,
      invoice_id
    }
  });
};

export const loadInvoiceDetailsStatic = async (invoice_id) => {
  const lineItemsResponse = await api({
    method: 'GET',
    url: parseUrl(Urls.INVOICE_LINE_ITEMS, { invoice_id })
  });

  const glSplitsReponse = await api({
    method: 'GET',
    url: parseUrl(Urls.INVOICE_GL_SPLITS, { invoice_id })
  });

  const historyResponse = await api({
    method: 'GET',
    url: parseUrl(Urls.INVOICE_HISTORY, { invoice_id })
  });

  const invoiceReponse = await api({
    method: 'GET',
    url: parseUrl(Urls.INVOICE_DETAILS, { invoice_id })
  });

  const response = invoiceReponse.data;
  response.line_items = lineItemsResponse.data;
  response.gl_splits = glSplitsReponse.data.splits || glSplitsReponse.data;
  response.history = historyResponse.data;
  response.invoice_id = response.id;
  response.has_line_items_loaded = true;
  response.has_gl_splits_loaded = true;
  response.has_images_loaded = true;
  response.has_history_loaded = true;

  if (invoiceReponse.statusCode === 200) {
    return response;
  }
  return null;
};

export const approveInvoice = (invoice_id) => async (dispatch) => {
  dispatch({
    type: APPROVE_INVOICE
  });

  sendMixpanelEvent(MixpanelEvents.INVOICE_APPROVED, { invoice_id });
  const {
    statusCode, errorMessage
  } = await api({
    method: 'POST',
    url: parseUrl(Urls.APPROVE_INVOICE, { invoice_id })
  });

  if (statusCode === 200) {
    dispatch({
      type: APPROVE_INVOICE_SUCCESS,
      payload: {
        invoice_id
      }
    });
  } else {
    dispatch({
      type: APPROVE_INVOICE_FAIL,
      payload: { error: errorMessage, invoice_id }
    });
    showAlert('Approval Failed', errorMessage || 'Some Internal error has occurred');
  }
};

export const setCurrentInvoice = (index) => async (dispatch) => {
  dispatch({
    type: SET_CURRENT_INVOICE,
    payload: { index }
  });
};

export const addInvoiceFlag = (invoice_id, flagging_reason) => async (dispatch) => {
  dispatch({
    type: ADD_INVOICE_FLAG
  });

  sendMixpanelEvent(MixpanelEvents.INVOICE_FLAGGED, { invoice_id });
  const {
    statusCode
  } = await api({
    method: 'POST',
    url: parseUrl(Urls.ADD_INVOICE_FLAG, { invoice_id }),
    data: { flagging_reason }
  });

  if (statusCode === 200) {
    dispatch({
      type: ADD_INVOICE_FLAG_SUCCESS,
      payload: {
        invoice_id
      }
    });
    dispatch(loadInvoiceDetails(invoice_id));
  }
};

export const resolveInvoiceFlag = (invoice_id, resolution_reason) => async (dispatch) => {
  dispatch({
    type: RESOLVE_INVOICE_FLAG
  });

  sendMixpanelEvent(MixpanelEvents.INVOICE_FLAGGED, { invoice_id });
  const {
    statusCode
  } = await api({
    method: 'POST',
    url: parseUrl(Urls.RESOLVE_INVOICE_FLAG, { invoice_id }),
    data: { resolution_reason }
  });

  if (statusCode === 200) {
    dispatch({
      type: RESOLVE_INVOICE_FLAG_SUCCESS,
      payload: {
        invoice_id
      }
    });
    dispatch(loadInvoiceDetails(invoice_id));
  }
};
