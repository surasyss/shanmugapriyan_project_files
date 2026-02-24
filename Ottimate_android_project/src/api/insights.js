import axios from 'axios';
import { INSIGHTS_BASE_URL } from 'react-native-dotenv';
import UserAgent from 'react-native-user-agent';
import Adapter from '../utils/Adapter';
import Constants from '../utils/Constants';

/**
 * Create an Axios Client with defaults
 */
const client = axios.create({
  baseURL: INSIGHTS_BASE_URL
});

/**
 * Request Wrapper with default success/error actions
 */
/* eslint-disable no-console */

const insightsApi = async (options) => {
  const onSuccess = (response) => {
    console.log('Request Successful!', response);
    const responseData = response.data;

    const data = {};
    if (responseData && responseData.data) {
      data.data = responseData.data;
    } else {
      data.data = response.data;
    }

    if (!data.statusCode) data.statusCode = response.status;
    return data;
  };

  const onError = (error) => {
    console.log('Request Failed:', error.config);
    let message = null;

    if (error.response) {
      // Request was made but server responded with something
      // other than 2xx
      console.log('Status:', error.response.status);
      console.log('Data:', error.response.data);
      console.log('Headers:', error.response.headers);

      if (error.response.status === Constants.UNAUTH_STATUS_CODE && options.url && options.url.indexOf('push_token/') === -1) {
        if (global.logoutMethod) {
          global.logoutMethod();
        }
      }

      if (typeof (error.response.data) === 'string') message = error.response.data;
      if (!message) message = error.response.data.detail;
      if (!message) message = error.response.data.error;
    } else if (error.message !== 'Network Error') message = error.message;
    if (!message) message = 'Some Internal error has occurred';

    return {
      statusCode: 500,
      errorMessage: message
    };
  };

  const headers = await Adapter.getAuthHeader();
  if (headers) {
    headers['User-Agent'] = UserAgent.getUserAgent();
    options = { ...options, headers };
  }

  return client(options)
    .then(onSuccess)
    .catch(onError);
};

export default insightsApi;
