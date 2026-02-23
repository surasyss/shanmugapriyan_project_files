import api from '../api';
import Urls from '../api/urls';

export const LOAD_VENDORS = 'load_vendors';
export const LOAD_VENDORS_SUCCESS = 'load_vendors_success';
export const LOAD_VENDORS_FAIL = 'load_vendors_fail';

export const loadVendors = (filters) => {
  const body = {
    page: 1,
    limit: 30
  };
  if (!filters) filters = {};
  Object.keys(filters).forEach((key) => {
    body[key] = filters[key];
  });

  return async (dispatch) => {
    dispatch({
      type: LOAD_VENDORS,
      payload: { firstLoad: body.page === 1 }
    });

    const {
      statusCode, errorMessage, data
    } = await api({
      method: 'GET',
      url: Urls.VENDORS,
      params: body
    });

    if (statusCode === 200) {
      dispatch({ type: LOAD_VENDORS_SUCCESS, payload: data });
    } else {
      dispatch({
        type: LOAD_VENDORS_FAIL,
        payload: { error: errorMessage }
      });
    }
  };
};
