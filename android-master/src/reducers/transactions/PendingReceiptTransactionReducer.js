import {
  ADD_PENDING_RECEIPT_TRANSACTION,
  LOAD_PENDING_RECEIPT_TRANSACTION,
  LOAD_PENDING_RECEIPT_TRANSACTION_FAIL,
  LOAD_PENDING_RECEIPT_TRANSACTION_SUCCESS, LOGOUT, RESET_PENDING_RECEIPT_TRANSACTION, UPDATE_PENDING_RECEIPT_PROGRESS
} from '../../actions';

const INITIAL_STATE = {
  error: null,
  data: [],
  loading: false,
  firstLoad: false
};

export default (state = INITIAL_STATE, action) => {
  const { type, payload } = action;
  switch (type) {
    case LOAD_PENDING_RECEIPT_TRANSACTION:
      return { ...state, loading: true, firstLoad: payload.firstLoad };
    case LOAD_PENDING_RECEIPT_TRANSACTION_SUCCESS:
      let items = state.data;
      if (state.firstLoad || !items) items = [];
      payload.results.forEach((item) => {
        items.push(item);
      });
      return {
        ...state,
        loading: false,
        error: '',
        data: items,
        next: payload.next,
        page: payload.page,
        firstLoad: false
      };
    case LOAD_PENDING_RECEIPT_TRANSACTION_FAIL:
      return {
        ...state, loading: false, error: payload.error, firstLoad: false
      };
    case RESET_PENDING_RECEIPT_TRANSACTION:
      return { ...state, data: [] };
    case ADD_PENDING_RECEIPT_TRANSACTION:
      const item = state.data;
      item[payload.index] = { ...item[payload.index], receipts: item[payload.index].receipts.concat(payload.data) };
      return { ...state, data: item };
    case UPDATE_PENDING_RECEIPT_PROGRESS:
      const trans = state.data;
      if (trans[payload.index]) {
        trans[payload.index] = { ...trans[payload.index], receipts: trans[payload.index].receipts.map((receipt) => (receipt.id === payload.receipt.id ? { ...receipt, progress: payload.receipt.progress, uploadState: payload.receipt.uploadState } : receipt)) };
      }
      return { ...state, data: trans };
    case LOGOUT:
      return INITIAL_STATE;
    default:
      return state;
  }
};
