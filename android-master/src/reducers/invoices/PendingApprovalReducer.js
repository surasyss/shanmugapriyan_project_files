import {
  ADD_INVOICE_FLAG_SUCCESS,
  APPROVE_INVOICE_FAIL,
  APPROVE_INVOICE_SUCCESS, LOAD_INVOICE_DETAILS_SUCCESS,
  LOAD_INVOICE_GL_SPLITS_SUCCESS, LOAD_INVOICE_IMAGES_SUCCESS,
  LOAD_INVOICE_LINE_ITEMS_SUCCESS,
  LOAD_PENDING_APPROVAL_INVOICES,
  LOAD_PENDING_APPROVAL_INVOICES_FAIL,
  LOAD_PENDING_APPROVAL_INVOICES_SUCCESS, LOGOUT, RESET_PENDING_APPROVAL_INVOICES, RESOLVE_INVOICE_FLAG_SUCCESS
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
    case LOAD_PENDING_APPROVAL_INVOICES:
      return { ...state, loading: true, firstLoad: payload.firstLoad };
    case LOAD_PENDING_APPROVAL_INVOICES_SUCCESS:
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
    case LOAD_PENDING_APPROVAL_INVOICES_FAIL:
      return {
        ...state, loading: false, error: payload.error, firstLoad: false
      };
    case LOAD_INVOICE_LINE_ITEMS_SUCCESS:
      const oldItems = state.data;
      const newItems = oldItems.map((item) => {
        if (item.id === payload.invoice_id) {
          item.line_items = payload.items;
          item.has_line_items_loaded = true;
        }
        return item;
      });
      return { ...state, data: newItems };
    case LOAD_INVOICE_GL_SPLITS_SUCCESS:
      const newGlItems = state.data.map((item) => {
        if (item.id === payload.invoice_id) item.gl_splits = payload.items;
        return item;
      });
      return { ...state, data: newGlItems };
    case LOAD_INVOICE_IMAGES_SUCCESS:
      const newImageItems = state.data.map((item) => {
        if (item.id === payload.invoice_id) item.images = payload.items;
        return item;
      });
      return { ...state, data: newImageItems };
    case RESET_PENDING_APPROVAL_INVOICES:
      return { ...state, data: [] };
    case APPROVE_INVOICE_SUCCESS:
      const newApproveItems = state.data.map((item) => {
        if (item.id === payload.invoice_id) item.isApproved = true;
        return item;
      });
      return { ...state, data: newApproveItems };
    case APPROVE_INVOICE_FAIL:
      const newApproveFailItems = state.data.map((item) => {
        if (item.id === payload.invoice_id) item.approvalFailed = true;
        return item;
      });
      return { ...state, data: newApproveFailItems };
    case LOAD_INVOICE_DETAILS_SUCCESS:
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
    case ADD_INVOICE_FLAG_SUCCESS:
      return {
        ...state,
        data: state.data.map((item) => {
          if (item.id === payload.invoice_id) item.is_flagged = true;
          return item;
        })
      };
    case RESOLVE_INVOICE_FLAG_SUCCESS:
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
