import {
  LOAD_ALL_PURCHASED_ITEMS,
  LOAD_ALL_PURCHASED_ITEMS_FAIL,
  LOAD_ALL_PURCHASED_ITEMS_SUCCESS,
  LOAD_PURCHASED_ITEM_DETAILS,
  LOAD_PURCHASED_ITEM_DETAILS_FAIL,
  LOAD_PURCHASED_ITEM_DETAILS_SUCCESS,
  LOGOUT, MARK_ITEM_STAR_LOCAL,
  RESET_ALL_PURCHASED_ITEMS
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
    case LOAD_ALL_PURCHASED_ITEMS:
      return { ...state, loading: true, firstLoad: payload.firstLoad };
    case LOAD_ALL_PURCHASED_ITEMS_SUCCESS:
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
    case LOAD_ALL_PURCHASED_ITEMS_FAIL:
      return {
        ...state, loading: false, error: payload.error, firstLoad: false
      };
    case RESET_ALL_PURCHASED_ITEMS:
      return { ...state, data: [] };
    case LOAD_PURCHASED_ITEM_DETAILS:
      return {
        ...state,
        data: state.data.map((item) => {
          if (item.id === payload.item_id) item.loading = true;
          return item;
        })
      };
    case LOAD_PURCHASED_ITEM_DETAILS_SUCCESS:
      return {
        ...state,
        data: state.data.map((item) => {
          if (item.id === payload.item_id) {
            item.loading = false;
            item.item_detail = payload.item_detail;
            item.trend = payload.trend;
            item.loaded = true;
          }
          return item;
        })
      };
    case LOAD_PURCHASED_ITEM_DETAILS_FAIL:
      return {
        ...state,
        data: state.data.map((item) => {
          if (item.id === payload.item_id) item.loading = false;
          return item;
        })
      };
    case MARK_ITEM_STAR_LOCAL:
      return {
        ...state,
        data: state.data.map((item) => {
          if (item.id === payload.item_id) {
            item.starred = payload.starred;
          }
          return item;
        })
      };
    case LOGOUT:
      return INITIAL_STATE;
    default:
      return state;
  }
};
