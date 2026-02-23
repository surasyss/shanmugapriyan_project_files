import moment from 'moment';
import { Buffer } from 'buffer';
import axios from 'axios';
import api from '../api';
import Urls from '../api/urls';
import store from '../store';
import PendingUploadAdapter from '../utils/PendingUploadAdapter';

export const LOAD_PENDING_UPLOADS = 'load_pending_uploads';
export const LOAD_PENDING_UPLOADS_SUCCESS = 'load_pending_uploads_success';

export const ADD_PENDING_UPLOAD = 'add_pending_upload';
export const DELETE_PENDING_UPLOAD = 'delete_pending_upload';

export const LOAD_S3_SIGN_URL = 'load_s3_sign_url';
export const LOAD_S3_SIGN_URL_SUCCESS = 'load_s3_sign_url_success';
export const LOAD_S3_SIGN_URL_FAIL = 'load_s3_sign_url_fail';

export const UPDATE_UPLOAD_PERCENTAGE = 'update_upload_percentage';
export const UPLOAD_PENDING_IMAGE = 'upload_pending_image';
export const UPLOAD_PENDING_IMAGE_SUCCESS = 'upload_pending_image_success';
export const UPLOAD_PENDING_IMAGE_FAIL = 'upload_pending_image_fail';

export const CREATE_INVOICE = 'create_invoice';
export const CREATE_INVOICE_SUCCESS = 'create_invoice_success';
export const CREATE_INVOICE_FAIL = 'create_invoice_fail';

const RNFS = require('react-native-fs');

export const loadPendingUploads = () => async (dispatch) => {
  dispatch({
    type: LOAD_PENDING_UPLOADS
  });

  const pendingUploads = await PendingUploadAdapter.getPendingUploadsData();

  dispatch({
    type: LOAD_PENDING_UPLOADS_SUCCESS,
    payload: pendingUploads
  });
};

export const addPendingUpload = (restaurant, image, signedUrl, options) => async (dispatch) => {
  const takenAt = new moment().toDate();

  const invoice = await PendingUploadAdapter.addPendingUpload(restaurant, image, takenAt, signedUrl, options);

  dispatch({
    type: ADD_PENDING_UPLOAD,
    payload: invoice
  });
  dispatch(handlePendingUpload(invoice));
};

export const deletePendingUpload = (invoice) => async (dispatch) => {
  dispatch({
    type: DELETE_PENDING_UPLOAD,
    payload: invoice
  });
};

export const handlePendingUpload = (invoice) => async (dispatch) => {
  const { pendingUploads } = store.getState();
  let exists = false;
  if (pendingUploads && pendingUploads.data) {
    pendingUploads.data.forEach((pendingUpload) => {
      exists = exists || (pendingUpload.image === invoice.image);
    });
  }
  if (exists && !invoice.loading) {
    if (!invoice.signedUrl) {
      await loads3SignUrl(invoice, dispatch);
    } else if (!invoice.isUploaded) {
      uploadFile(invoice, dispatch);
    } else if (!invoice.isCreated) {
      createInvoice(invoice, dispatch);
    }
  }
};

export const loads3SignUrl = async (invoice, dispatch) => {
  dispatch({
    type: LOAD_S3_SIGN_URL,
    payload: { invoice }
  });

  const fileParts = invoice.image.split('/');
  const filename = fileParts[fileParts.length - 1];
  const restaurant = invoice.restaurant.id;

  const {
    statusCode, data
  } = await api({
    method: 'GET',
    url: Urls.S3SIGNURL,
    params: { filename, restaurant }
  });

  if (statusCode === 200) {
    await PendingUploadAdapter.updatePendingUploads(invoice, { signedUrl: data });

    dispatch({
      type: LOAD_S3_SIGN_URL_SUCCESS,
      payload: { invoice, s3url: data }
    });
    invoice.loading = false;
    invoice.signedUrl = data;
  }
  dispatch(handlePendingUpload(invoice));
};

export const uploadFile = async (invoice, dispatch) => {
  const file = await RNFS.readFile(invoice.image, 'base64');
  const url = invoice.signedUrl.put_request;

  const config = {
    onUploadProgress: (progressEvent) => {
      // eslint-disable-next-line radix
      const uploadPercentage = parseInt(Math.round((progressEvent.loaded / progressEvent.total) * 100));
      dispatch({
        type: UPDATE_UPLOAD_PERCENTAGE,
        payload: { invoice, uploadPercentage }
      });
    },
    headers: {
      'Content-Type': 'image/jpeg'
    }
  };

  dispatch({
    type: UPLOAD_PENDING_IMAGE,
    payload: { invoice }
  });

  // eslint-disable-next-line no-buffer-constructor
  axios.put(url, new Buffer(file, 'base64'), config)
    .then(() => {
      PendingUploadAdapter.updatePendingUploads(invoice, { isUploaded: true });
      invoice.loading = false;
      invoice.isUploaded = true;

      dispatch({
        type: UPLOAD_PENDING_IMAGE_SUCCESS,
        payload: { invoice }
      });
      dispatch(handlePendingUpload(invoice));
    })
    .catch(() => {
      dispatch({
        type: UPLOAD_PENDING_IMAGE_FAIL,
        payload: { invoice }
      });
      dispatch(handlePendingUpload(invoice));
    });
};

export const createInvoice = async (invoice, dispatch) => {
  const { signedUrl, restaurant, options } = invoice;

  const body = {
    image: signedUrl.url,
    upload_id: signedUrl.upload_id,
    restaurant: restaurant.id
  };
  if (options) {
    Object.keys(options).forEach((key) => {
      body[key] = options[key];
    });
  }

  dispatch({
    type: CREATE_INVOICE,
    payload: { invoice }
  });

  const {
    statusCode
  } = await api({
    method: 'POST',
    url: Urls.INVOICES,
    data: body
  });

  if (statusCode < 300) {
    await PendingUploadAdapter.updatePendingUploads(invoice, { isCreated: true });
    dispatch({
      type: CREATE_INVOICE_SUCCESS,
      payload: { invoice }
    });
  } else {
    dispatch({
      type: CREATE_INVOICE_FAIL,
      payload: { invoice }
    });
    dispatch(handlePendingUpload(invoice));
  }
};
