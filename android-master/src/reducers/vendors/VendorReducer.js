import { LOAD_VENDORS, LOAD_VENDORS_FAIL, LOAD_VENDORS_SUCCESS } from '../../actions';

const INITIAL_STATE = {
  error: null,
  data: [],
  loading: true,
  firstLoad: false
};

export default (state = INITIAL_STATE, action) => {
  const { type, payload } = action;
  switch (type) {
    case LOAD_VENDORS:
      return { ...state, loading: true, firstLoad: payload.firstLoad };
    case LOAD_VENDORS_SUCCESS:
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
    case LOAD_VENDORS_FAIL:
      return {
        ...state, loading: false, error: payload.error, firstLoad: false
      };
    default:
      return state;
  }
};
