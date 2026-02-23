import {
  ADD_PENDING_TRANSACTION_UPLOAD,
  CREATE_TRANSACTION_RECEIPT,
  CREATE_TRANSACTION_RECEIPT_FAIL,
  CREATE_TRANSACTION_RECEIPT_SUCCESS, DELETE_COMPLETED_TRANSACTIONS_UPLOADS,
  LOAD_TRANSACTION_S3_SIGN_URL,
  LOAD_TRANSACTION_S3_SIGN_URL_SUCCESS,
  UPDATE_TRANSACTION_UPLOAD_PERCENTAGE,
  UPLOAD_TRANSACTION_PENDING_IMAGE,
  UPLOAD_TRANSACTION_PENDING_IMAGE_FAIL,
  UPLOAD_TRANSACTION_PENDING_IMAGE_SUCCESS
} from '../../actions';

const INITIAL_STATE = {
  error: null,
  data: [],
  loading: true,
};

export default (state = INITIAL_STATE, action) => {
  const { type, payload } = action;
  switch (type) {
    case ADD_PENDING_TRANSACTION_UPLOAD:
      return { ...state, data: [...state.data, payload] };
    case LOAD_TRANSACTION_S3_SIGN_URL:
      return {
        ...state,
        data: state.data.map((transaction) => {
          if (transaction.image === payload.transaction.image) {
            return { ...transaction, loading: true, signedUrl: null };
          }
          return transaction;
        })
      };
    case LOAD_TRANSACTION_S3_SIGN_URL_SUCCESS:
      return {
        ...state,
        data: state.data.map((transaction) => {
          if (transaction.image === payload.transaction.image) {
            return { ...transaction, loading: false, signedUrl: payload.s3url };
          }
          return transaction;
        })
      };
    case UPDATE_TRANSACTION_UPLOAD_PERCENTAGE:
      return {
        ...state,
        data: state.data.map((transaction) => {
          if (transaction.image === payload.transaction.image) {
            return { ...transaction, loading: false, uploadPercentage: payload.uploadPercentage };
          }
          return transaction;
        })
      };
    case UPLOAD_TRANSACTION_PENDING_IMAGE:
      return {
        ...state,
        data: state.data.map((transaction) => {
          if (transaction.image === payload.transaction.image) {
            return { ...transaction, loading: true };
          }
          return transaction;
        })
      };
    case UPLOAD_TRANSACTION_PENDING_IMAGE_SUCCESS:
      return {
        ...state,
        data: state.data.map((transaction) => {
          if (transaction.image === payload.transaction.image) {
            return { ...transaction, loading: false, isUploaded: true };
          }
          return transaction;
        })
      };
    case UPLOAD_TRANSACTION_PENDING_IMAGE_FAIL:
      return {
        ...state,
        data: state.data.map((transaction) => {
          if (transaction.image === payload.transaction.image) {
            return { ...transaction, loading: false };
          }
          return transaction;
        })
      };
    case CREATE_TRANSACTION_RECEIPT:
      return {
        ...state,
        data: state.data.map((transaction) => {
          if (transaction.image === payload.transaction.image) {
            return { ...transaction, loading: true };
          }
          return transaction;
        })
      };
    case CREATE_TRANSACTION_RECEIPT_SUCCESS:
      return {
        ...state,
        data: state.data.map((transaction) => {
          if (transaction.image === payload.transaction.image) {
            return { ...transaction, loading: false, isCreated: true };
          }
          return transaction;
        })
      };
    case CREATE_TRANSACTION_RECEIPT_FAIL:
      return {
        ...state,
        data: state.data.map((transaction) => {
          if (transaction.image === payload.transaction.image) {
            return { ...transaction, loading: false };
          }
          return transaction;
        })
      };
    case DELETE_COMPLETED_TRANSACTIONS_UPLOADS:
      const resetTransactions = [];
      state.data.forEach((transaction) => {
        const { isCreated } = transaction;
        if (!isCreated) {
          resetTransactions.push(transaction);
        }
      });
      return { ...state, data: resetTransactions };
    default:
      return state;
  }
};
