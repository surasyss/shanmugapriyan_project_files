import {
  ADD_PENDING_UPLOAD, CREATE_INVOICE, CREATE_INVOICE_FAIL, CREATE_INVOICE_SUCCESS, DELETE_PENDING_UPLOAD,
  LOAD_PENDING_UPLOADS,
  LOAD_PENDING_UPLOADS_SUCCESS,
  LOAD_S3_SIGN_URL,
  LOAD_S3_SIGN_URL_SUCCESS,
  UPDATE_UPLOAD_PERCENTAGE,
  UPLOAD_PENDING_IMAGE,
  UPLOAD_PENDING_IMAGE_FAIL,
  UPLOAD_PENDING_IMAGE_SUCCESS
} from '../../actions';

const INITIAL_STATE = {
  error: null,
  data: [],
  loading: true,
};

export default (state = INITIAL_STATE, action) => {
  const { type, payload } = action;
  switch (type) {
    case LOAD_PENDING_UPLOADS:
      return { ...state, loading: true };
    case LOAD_PENDING_UPLOADS_SUCCESS:
      return { ...state, loading: false, data: payload };
    case ADD_PENDING_UPLOAD:
      return { ...state, data: [...state.data, payload] };
    case DELETE_PENDING_UPLOAD:
      const pendingInvoices = [];
      state.data.forEach((invoice) => {
        if (invoice.image !== payload.image) {
          pendingInvoices.push(invoice);
        }
      });
      return { ...state, data: pendingInvoices };
    case LOAD_S3_SIGN_URL:
      return {
        ...state,
        data: state.data.map((invoice) => {
          if (invoice.image === payload.invoice.image) {
            return { ...invoice, loading: true, signedUrl: null };
          }
          return invoice;
        })
      };
    case LOAD_S3_SIGN_URL_SUCCESS:
      return {
        ...state,
        data: state.data.map((invoice) => {
          if (invoice.image === payload.invoice.image) {
            return { ...invoice, loading: false, signedUrl: payload.s3url };
          }
          return invoice;
        })
      };
    case UPDATE_UPLOAD_PERCENTAGE:
      return {
        ...state,
        data: state.data.map((invoice) => {
          if (invoice.image === payload.invoice.image) {
            return { ...invoice, loading: false, uploadPercentage: payload.uploadPercentage };
          }
          return invoice;
        })
      };
    case UPLOAD_PENDING_IMAGE:
      return {
        ...state,
        data: state.data.map((invoice) => {
          if (invoice.image === payload.invoice.image) {
            return { ...invoice, loading: true };
          }
          return invoice;
        })
      };
    case UPLOAD_PENDING_IMAGE_SUCCESS:
      return {
        ...state,
        data: state.data.map((invoice) => {
          if (invoice.image === payload.invoice.image) {
            return { ...invoice, loading: false, isUploaded: true };
          }
          return invoice;
        })
      };
    case UPLOAD_PENDING_IMAGE_FAIL:
      return {
        ...state,
        data: state.data.map((invoice) => {
          if (invoice.image === payload.invoice.image) {
            return { ...invoice, loading: false };
          }
          return invoice;
        })
      };
    case CREATE_INVOICE:
      return {
        ...state,
        data: state.data.map((invoice) => {
          if (invoice.image === payload.invoice.image) {
            return { ...invoice, loading: true };
          }
          return invoice;
        })
      };
    case CREATE_INVOICE_SUCCESS:
      return {
        ...state,
        data: state.data.map((invoice) => {
          if (invoice.image === payload.invoice.image) {
            return { ...invoice, loading: false, isCreated: true };
          }
          return invoice;
        })
      };
    case CREATE_INVOICE_FAIL:
      return {
        ...state,
        data: state.data.map((invoice) => {
          if (invoice.image === payload.invoice.image) {
            return { ...invoice, loading: false };
          }
          return invoice;
        })
      };
    default:
      return state;
  }
};
