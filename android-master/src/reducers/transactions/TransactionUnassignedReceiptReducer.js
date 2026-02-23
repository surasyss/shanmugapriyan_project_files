import {
  LOAD_TRANSACTION_UNASSIGNED_RECEIPTS,
  LOAD_TRANSACTION_UNASSIGNED_RECEIPTS_FAIL,
  LOAD_TRANSACTION_UNASSIGNED_RECEIPTS_SUCCESS, LOGOUT
} from '../../actions';

const INITIAL_STATE = {
  error: null,
  data: [],
  loading: false,
};

export default (state = INITIAL_STATE, action) => {
  const { type, payload } = action;
  switch (type) {
    case LOAD_TRANSACTION_UNASSIGNED_RECEIPTS:
      return INITIAL_STATE;
    case LOAD_TRANSACTION_UNASSIGNED_RECEIPTS_SUCCESS:
      return {
        ...state,
        loading: false,
        error: null,
        data: payload.data ? payload.data.results : [],
      };
    case LOAD_TRANSACTION_UNASSIGNED_RECEIPTS_FAIL:
      return {
        ...state, loading: false, error: payload.error
      };
    case LOGOUT:
      return INITIAL_STATE;
    default:
      return state;
  }
};
