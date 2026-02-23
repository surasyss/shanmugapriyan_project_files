import Urls from '../api/urls';
import spendApi from '../api/spend';
import { parseUrl } from '../utils/StringFormatter';

export const LOAD_PENDING_RECEIPT_TRANSACTION = 'loading_pending_receipt_transaction';
export const LOAD_PENDING_RECEIPT_TRANSACTION_SUCCESS = 'loading_pending_receipt_transaction_success';
export const LOAD_PENDING_RECEIPT_TRANSACTION_FAIL = 'loading_pending_receipt_transaction_fail';
export const ADD_PENDING_RECEIPT_TRANSACTION = 'add_pending_receipt_transaction';
export const UPDATE_PENDING_RECEIPT_PROGRESS = 'update_pending_receipt_progress';

export const RESET_PENDING_RECEIPT_TRANSACTION = 'reset_pending_receipt';
export const SET_CURRENT_TRANSACTION = 'set_current_transaction';
export const SET_MEMO_EDIT = 'set_edit_memo';

export const LOAD_ALL_TRANSACTION = 'loading_all_transaction';
export const LOAD_ALL_TRANSACTION_SUCCESS = 'loading_all_transaction_success';
export const LOAD_ALL_TRANSACTION_FAIL = 'loading_all_transaction_fail';
export const ADD_ALL_RECEIPT_TRANSACTION = 'add_all_receipt_transaction';
export const UPDATE_ALL_RECEIPT_PROGRESS = 'update_all_receipt_progress';

export const RESET_ALL_TRANSACTION = 'reset_all_receipt';
export const DELETE_COMPLETED_TRANSACTIONS_UPLOADS = 'delete_completed_transactions_uploads';

export const LOAD_TRANSACTION_UNASSIGNED_RECEIPTS = 'loading_transaction_unassigned_receipts';
export const LOAD_TRANSACTION_UNASSIGNED_RECEIPTS_SUCCESS = 'loading_transaction_unassigned_receipts_success';
export const LOAD_TRANSACTION_UNASSIGNED_RECEIPTS_FAIL = 'loading_transaction_unassigned_receipts_fail';

export const LOAD_TRANSACTION_REFRESH_SUCCESS = 'load_transaction_refresh_success';

export const loadPendingReceiptTransactions = (filters) => {
  const body = {
    page: 1,
    limit: 20,
    has_receipts: false,
    ordering: '-posting_date,-created_date'
  };
  Object.keys(filters).forEach((key) => {
    body[key] = filters[key];
  });

  return async (dispatch) => {
    dispatch({
      type: LOAD_PENDING_RECEIPT_TRANSACTION,
      payload: { firstLoad: body.page === 1 }
    });

    const {
      statusCode, errorMessage, data
    } = await spendApi({
      method: 'GET',
      url: Urls.TRANSACTIONS,
      params: body
    });

    if (statusCode === 200) {
      // const storedReceiptAddedData = await receiptUploadWorker.addExistingReciptsInQueue(data);
      // dispatch({ type: LOAD_PENDING_RECEIPT_TRANSACTION_SUCCESS, payload: { ...storedReceiptAddedData, page: body.page } });
      dispatch({ type: LOAD_PENDING_RECEIPT_TRANSACTION_SUCCESS, payload: { ...data, page: body.page } });
    } else {
      dispatch({
        type: LOAD_PENDING_RECEIPT_TRANSACTION_FAIL,
        payload: { error: errorMessage }
      });
    }
  };
};

export const resetPendingReceiptTransactions = () => async (dispatch) => {
  dispatch({ type: RESET_PENDING_RECEIPT_TRANSACTION });
};

export const addReceiptInCurrentPendingTransaction = (info) => async (dispatch) => {
  dispatch({
    type: ADD_PENDING_RECEIPT_TRANSACTION,
    payload: { data: info.data, index: info.index }
  });
};

export const updateReceiptProgress = (receipt) => async (dispatch) => {
  dispatch({
    type: UPDATE_ALL_RECEIPT_PROGRESS,
    payload: receipt
  });
};

export const updatePendingReceiptProgress = (receipt) => async (dispatch) => {
  dispatch({
    type: UPDATE_PENDING_RECEIPT_PROGRESS,
    payload: receipt
  });
};

export const setCurrentTransaction = (index) => async (dispatch) => {
  dispatch({
    type: SET_CURRENT_TRANSACTION,
    payload: { index }
  });
};

export const loadAllTransactions = (filters) => {
  const body = {
    page: 1,
    limit: 20,
  };
  Object.keys(filters).forEach((key) => {
    body[key] = filters[key];
  });

  return async (dispatch) => {
    dispatch({
      type: LOAD_ALL_TRANSACTION,
      payload: { firstLoad: body.page === 1 }
    });

    dispatch({
      type: DELETE_COMPLETED_TRANSACTIONS_UPLOADS,
    });

    const {
      statusCode, errorMessage, data
    } = await spendApi({
      method: 'GET',
      url: Urls.TRANSACTIONS,
      params: body
    });

    if (statusCode === 200) {
      // const storedReceiptAddedData = await receiptUploadWorker.addExistingReciptsInQueue(data);
      // dispatch({ type: LOAD_ALL_TRANSACTION_SUCCESS, payload: { ...storedReceiptAddedData, page: body.page } });
      dispatch({ type: LOAD_ALL_TRANSACTION_SUCCESS, payload: { ...data, page: body.page } });
    } else {
      dispatch({
        type: LOAD_ALL_TRANSACTION_FAIL,
        payload: { error: errorMessage }
      });
    }
  };
};

export const resetAllTransactions = () => async (dispatch) => {
  dispatch({ type: RESET_ALL_TRANSACTION });
};

export const addReceiptInCurrentAllTransaction = (info) => async (dispatch) => {
  dispatch({
    type: ADD_ALL_RECEIPT_TRANSACTION,
    payload: { data: info.data, index: info.index }
  });
};

export const loadUnassignedReceipts = (company) => {
  const body = {
    company,
    limit: 100,
    page: 1,
    is_mapped: false,
    ordering: 'is_rejected,created_date',
    is_archived: false,
  };

  return async (dispatch) => {
    dispatch({
      type: LOAD_TRANSACTION_UNASSIGNED_RECEIPTS,
    });

    const {
      statusCode, errorMessage, data
    } = await spendApi({
      method: 'GET',
      url: Urls.UNASSIGNED_RECEIPTS,
      params: body
    });

    if (statusCode === 200) {
      dispatch({ type: LOAD_TRANSACTION_UNASSIGNED_RECEIPTS_SUCCESS, payload: { data } });
    } else {
      dispatch({
        type: LOAD_TRANSACTION_UNASSIGNED_RECEIPTS_FAIL,
        payload: { error: errorMessage }
      });
    }
  };
};

export const refreshTransaction = (transaction_id, company) => async (dispatch) => {
  const {
    statusCode, data
  } = await spendApi({
    method: 'GET',
    url: parseUrl(Urls.TRANSACTION_DETAIL, { transaction_id }),
    params: { company }
  });

  if (statusCode === 200) {
    dispatch({ type: LOAD_TRANSACTION_REFRESH_SUCCESS, payload: { data } });
  }
};

export const addMemo = (transaction_id, company_id, memo) => async (dispatch) => {
  const {
    statusCode, data
  } = await spendApi({
    method: 'PATCH',
    url: parseUrl(Urls.ADD_MEMO, { transaction_id, company_id }),
    data: { memo }
  });

  if (statusCode === 200) {
    dispatch({ type: LOAD_TRANSACTION_REFRESH_SUCCESS, payload: { data } });
    dispatch({ type: SET_MEMO_EDIT, payload: { status: false } });
  }
};

export const setEditMemo = (status) => async (dispatch) => {
  dispatch({ type: SET_MEMO_EDIT, payload: { status } });
};
