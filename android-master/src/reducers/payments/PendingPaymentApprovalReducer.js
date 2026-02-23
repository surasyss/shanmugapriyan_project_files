import {
  APPROVE_PAYMENT_FAIL,
  APPROVE_PAYMENT_SUCCESS,
  LOAD_PENDING_APPROVAL_PAYMENTS,
  LOAD_PENDING_APPROVAL_PAYMENTS_FAIL,
  LOAD_PENDING_APPROVAL_PAYMENTS_SUCCESS, LOGOUT, RESET_PENDING_APPROVAL_PAYMENTS
} from '../../actions';

const INITIAL_STATE = {
  error: null,
  data: [],
  loading: true,
  firstLoad: false
};

export default (state = INITIAL_STATE, action) => {
  const { type, payload } = action;
  switch (type) {
    case LOAD_PENDING_APPROVAL_PAYMENTS:
      return { ...state, loading: true, firstLoad: payload.firstLoad };
    case LOAD_PENDING_APPROVAL_PAYMENTS_SUCCESS:
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
    case LOAD_PENDING_APPROVAL_PAYMENTS_FAIL:
      return {
        ...state, loading: false, error: payload.error, firstLoad: false
      };
    case RESET_PENDING_APPROVAL_PAYMENTS:
      return { ...state, data: [] };
    case APPROVE_PAYMENT_SUCCESS:
      return {
        ...state,
        data: state.data.map((item) => {
          if (item.id === payload.payment_id) item.isApproved = true;
          return item;
        })
      };
    case APPROVE_PAYMENT_FAIL:
      return {
        ...state,
        data: state.data.map((item) => {
          if (item.id === payload.payment_id) item.approvalFailed = true;
          return item;
        })
      };
    case LOGOUT:
      return INITIAL_STATE;
    default:
      return state;
  }
};
