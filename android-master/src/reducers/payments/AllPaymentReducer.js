import {
  LOAD_ALL_PAYMENTS, LOAD_ALL_PAYMENTS_FAIL, LOAD_ALL_PAYMENTS_SUCCESS, LOGOUT, RESET_ALL_PAYMENTS
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
    case LOAD_ALL_PAYMENTS:
      return { ...state, loading: true, firstLoad: payload.firstLoad };
    case LOAD_ALL_PAYMENTS_SUCCESS:
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
    case LOAD_ALL_PAYMENTS_FAIL:
      return {
        ...state, loading: false, error: payload.error, firstLoad: false
      };
    case RESET_ALL_PAYMENTS:
      return { ...state, data: [] };
    case LOGOUT:
      return INITIAL_STATE;
    default:
      return state;
  }
};
