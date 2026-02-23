import {
  ADD_CREDIT_REQUEST_FLAG_SUCCESS,
  LOAD_ALL_CREDIT_REQUESTS,
  LOAD_ALL_CREDIT_REQUESTS_FAIL,
  LOAD_ALL_CREDIT_REQUESTS_SUCCESS,
  LOAD_CREDIT_REQUEST_DETAILS_SUCCESS,
  RESET_ALL_CREDIT_REQUESTS, RESOLVE_CREDIT_REQUEST_FLAG_SUCCESS
} from '../../actions/CreditRequestActions';
import { LOGOUT } from '../../actions';

const INITIAL_STATE = {
  error: null,
  data: [],
  loading: true,
  firstLoad: false
};

export default (state = INITIAL_STATE, action) => {
  const { type, payload } = action;
  switch (type) {
    case LOAD_ALL_CREDIT_REQUESTS:
      return { ...state, loading: true, firstLoad: payload.firstLoad };
    case LOAD_ALL_CREDIT_REQUESTS_SUCCESS:
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
    case LOAD_ALL_CREDIT_REQUESTS_FAIL:
      return {
        ...state, loading: false, error: payload.error, firstLoad: false
      };
    case RESET_ALL_CREDIT_REQUESTS:
      return { ...state, data: [] };
    case LOAD_CREDIT_REQUEST_DETAILS_SUCCESS:
      const newInvoiceDetailItems = state.data.map((item) => {
        if (item.id === payload.invoice_id) {
          item.line_items = payload.line_items;
          item.gl_splits = payload.gl_splits;
          item.images = payload.images;
          item.links = payload.links;
          item.history = payload.history;
          item.has_line_items_loaded = true;
          item.has_gl_splits_loaded = true;
          item.has_images_loaded = true;
          item.has_history_loaded = true;
        }
        return item;
      });
      return { ...state, data: newInvoiceDetailItems };
    case ADD_CREDIT_REQUEST_FLAG_SUCCESS:
      return {
        ...state,
        data: state.data.map((item) => {
          if (item.id === payload.invoice_id) item.is_flagged = true;
          return item;
        })
      };
    case RESOLVE_CREDIT_REQUEST_FLAG_SUCCESS:
      return {
        ...state,
        data: state.data.map((item) => {
          if (item.id === payload.invoice_id) item.is_flagged = false;
          return item;
        })
      };
    case LOGOUT:
      return INITIAL_STATE;
    default:
      return state;
  }
};
