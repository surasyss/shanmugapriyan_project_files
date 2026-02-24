import api from '../api';
import Urls from '../api/urls';

export const LOAD_CATEGORIES = 'load_categories';
export const LOAD_CATEGORIES_SUCCESS = 'load_categories_success';
export const LOAD_CATEGORIES_FAIL = 'load_categories_fail';

export const RESET_CATEGORIES = 'reset_categories';

export const loadCategories = (filters) => {
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
      type: LOAD_CATEGORIES,
      payload: { firstLoad: body.page === 1 }
    });

    const {
      statusCode, errorMessage, data
    } = await api({
      method: 'GET',
      url: Urls.CATEGORIES,
      params: body
    });

    if (statusCode === 200) {
      dispatch({ type: LOAD_CATEGORIES_SUCCESS, payload: data });
    } else {
      dispatch({
        type: LOAD_CATEGORIES_FAIL,
        payload: { error: errorMessage }
      });
    }
  };
};

export const resetCategories = () => async (dispatch) => {
  dispatch({ type: RESET_CATEGORIES });
};
