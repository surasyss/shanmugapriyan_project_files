import moment from 'moment';
import axios from 'axios';
import PendingTransactionUploadAdapter from '../utils/PendingTransactionUploadAdapter';
import Urls from '../api/urls';
import spendApi from '../api/spend';
import { parseUrl } from '../utils/StringFormatter';

export const LOAD_PENDING_TRANSACTION_UPLOADS = 'load_pending_transaction_uploads';
export const LOAD_PENDING_TRANSACTION_UPLOADS_SUCCESS = 'load_pending_transaction_uploads_success';

export const ADD_PENDING_TRANSACTION_UPLOAD = 'add_pending_transaction_upload';

export const LOAD_TRANSACTION_S3_SIGN_URL = 'load_transaction_s3_sign_url';
export const LOAD_TRANSACTION_S3_SIGN_URL_SUCCESS = 'load_transaction_s3_sign_url_success';

export const UPDATE_TRANSACTION_UPLOAD_PERCENTAGE = 'update_transaction_upload_percentage';
export const UPLOAD_TRANSACTION_PENDING_IMAGE = 'upload_transaction_pending_image';
export const UPLOAD_TRANSACTION_PENDING_IMAGE_SUCCESS = 'upload_transaction_pending_image_success';
export const UPLOAD_TRANSACTION_PENDING_IMAGE_FAIL = 'upload_transaction_pending_image_fail';

export const CREATE_TRANSACTION_RECEIPT = 'create_transaction_receipt';
export const CREATE_TRANSACTION_RECEIPT_SUCCESS = 'create_transaction_receipt_success';
export const CREATE_TRANSACTION_RECEIPT_FAIL = 'create_transaction_receipt_fail';

export const loadTransactionPendingUploads = () => async (dispatch) => {
  dispatch({
    type: LOAD_PENDING_TRANSACTION_UPLOADS
  });

  const pendingUploads = await PendingTransactionUploadAdapter.getPendingTransactionUploadsData();

  dispatch({
    type: LOAD_PENDING_TRANSACTION_UPLOADS_SUCCESS,
    payload: pendingUploads
  });
};

export const addTransactionPendingUpload = (transaction_id, company_id, image) => async (dispatch) => {
  const takenAt = new moment().toDate();

  const transaction = await PendingTransactionUploadAdapter.addPendingTransactionUpload(transaction_id, company_id, image, takenAt);

  dispatch({
    type: ADD_PENDING_TRANSACTION_UPLOAD,
    payload: transaction
  });
  dispatch(handlePendingTransactionUpload(transaction));
};

export const handlePendingTransactionUpload = (transaction) => async (dispatch) => {
  transaction = JSON.parse(JSON.stringify(transaction));
  if (!transaction.loading) {
    if (!transaction.signedUrl) {
      await loadsTransaction3SignUrl(transaction, dispatch);
    } else if (!transaction.isUploaded) {
      uploadTransactionFile(transaction, dispatch);
    } else if (!transaction.isCreated) {
      createTransactionReceipt(transaction, dispatch);
    }
  }
};

export const loadsTransaction3SignUrl = async (transaction, dispatch) => {
  dispatch({
    type: LOAD_TRANSACTION_S3_SIGN_URL,
    payload: { transaction }
  });

  const fileParts = transaction.image.split('/');
  const filename = fileParts[fileParts.length - 1];

  const {
    statusCode, data
  } = await spendApi({
    method: 'POST',
    url: Urls.S3_SIGN_TRANSACTION,
    data: { filename }
  });

  if (statusCode === 200) {
    await PendingTransactionUploadAdapter.updatePendingTransactionUpload(transaction, { signedUrl: data });

    dispatch({
      type: LOAD_TRANSACTION_S3_SIGN_URL_SUCCESS,
      payload: { transaction, signedUrl: data }
    });
    transaction.loading = false;
    transaction.signedUrl = data;
  }
  dispatch(handlePendingTransactionUpload(transaction));
};

export const uploadTransactionFile = async (transaction, dispatch) => {
  const url = transaction.signedUrl.put_request;

  const config = {
    onUploadProgress: (progressEvent) => {
      // eslint-disable-next-line radix
      const uploadPercentage = parseInt(Math.round((progressEvent.loaded / progressEvent.total) * 100));
      dispatch({
        type: UPDATE_TRANSACTION_UPLOAD_PERCENTAGE,
        payload: { transaction, uploadPercentage }
      });
    },
    headers: {
      'Content-Type': 'multipart/form-data',
      'x-amz-acl': 'public-read',
      'avoid-intercept': 'true'
    }
  };

  dispatch({
    type: UPLOAD_TRANSACTION_PENDING_IMAGE,
    payload: { transaction }
  });

  const data = new FormData();
  Object.keys(transaction.signedUrl.fields).forEach((key) => {
    data.append(key, transaction.signedUrl.fields[key]);
  });
  data.append('file', {
    uri: transaction.image,
    type: transaction.signedUrl.headers['Content-type'],
  });

  axios.post(url, data, config)
    .then(() => {
      PendingTransactionUploadAdapter.updatePendingTransactionUpload(transaction, { isUploaded: true });
      transaction.loading = false;
      transaction.isUploaded = true;

      dispatch({
        type: UPLOAD_TRANSACTION_PENDING_IMAGE_SUCCESS,
        payload: { transaction }
      });
      dispatch(handlePendingTransactionUpload(transaction));
    })
    .catch(() => {
      dispatch({
        type: UPLOAD_TRANSACTION_PENDING_IMAGE_FAIL,
        payload: { transaction }
      });
      dispatch(handlePendingTransactionUpload(transaction));
    });
};

export const createTransactionReceipt = async (transaction, dispatch) => {
  const { signedUrl, transaction_id, company_id } = transaction;
  const body = {
    url: signedUrl.url,
    transaction: transaction_id,
  };

  dispatch({
    type: CREATE_TRANSACTION_RECEIPT,
    payload: { transaction }
  });

  const {
    statusCode
  } = await spendApi({
    method: 'POST',
    url: parseUrl(Urls.TRANSACTION_RECEIPT, { company_id }),
    data: body
  });

  if (statusCode < 300) {
    await PendingTransactionUploadAdapter.updatePendingTransactionUpload(transaction, { isCreated: true });
    dispatch({
      type: CREATE_TRANSACTION_RECEIPT_SUCCESS,
      payload: { transaction }
    });
  } else {
    dispatch({
      type: CREATE_TRANSACTION_RECEIPT_FAIL,
      payload: { transaction }
    });
    dispatch(handlePendingTransactionUpload(transaction));
  }
};

export const mapTransactionReceipt = async (transaction, company_id, url) => {
  const body = {
    transaction, url
  };

  const {
    statusCode
  } = await spendApi({
    method: 'POST',
    url: parseUrl(Urls.TRANSACTION_RECEIPT, { company_id }),
    data: body
  });

  return statusCode < 300;
};
