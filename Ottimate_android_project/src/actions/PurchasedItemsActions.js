import insightsApi from '../api/insights';
import Urls from '../api/urls';
import { parseUrl } from '../utils/StringFormatter';
import { MixpanelEvents, sendMixpanelEvent } from '../utils/mixpanel/MixPanelAdapter';
import api from '../api';

export const LOAD_STARRED_PURCHASED_ITEMS = 'load_starred_purchased_items';
export const LOAD_STARRED_PURCHASED_ITEMS_SUCCESS = 'load_starred_purchased_items_success';
export const LOAD_STARRED_PURCHASED_ITEMS_FAIL = 'load_starred_purchased_items_fail';
export const RESET_STARRED_PURCHASED_ITEMS = 'reset_starred_purchased_items';

export const LOAD_ALL_PURCHASED_ITEMS = 'load_all_purchased_items';
export const LOAD_ALL_PURCHASED_ITEMS_SUCCESS = 'load_all_purchased_items_success';
export const LOAD_ALL_PURCHASED_ITEMS_FAIL = 'load_all_purchased_items_fail';
export const RESET_ALL_PURCHASED_ITEMS = 'reset_all_purchased_items';

export const LOAD_PURCHASED_ITEM_DETAILS = 'load_purchased_item_details';
export const LOAD_PURCHASED_ITEM_DETAILS_SUCCESS = 'load_purchased_item_details_success';
export const LOAD_PURCHASED_ITEM_DETAILS_FAIL = 'load_purchased_item_details_fail';

export const SET_CURRENT_PURCHASED_ITEM = 'set_current_purchased_item';
export const MARK_ITEM_STAR_LOCAL = 'mark_item_star_local';

export const loadStarredPurchasedItems = (filters) => {
  const body = {
    page: 1,
    sort_order: 'desc',
    sort_by: 'last_purchased',
    limit: 20,
    starred: true
  };

  Object.keys(filters).forEach((key) => {
    body[key] = filters[key];
  });

  return async (dispatch) => {
    dispatch({
      type: LOAD_STARRED_PURCHASED_ITEMS,
      payload: { firstLoad: body.page === 1 }
    });

    const {
      statusCode, errorMessage, data
    } = await insightsApi({
      method: 'GET',
      url: Urls.PURCHASED_ITEMS,
      params: body
    });

    if (statusCode === 200) {
      dispatch({ type: LOAD_STARRED_PURCHASED_ITEMS_SUCCESS, payload: data });
    } else {
      dispatch({
        type: LOAD_STARRED_PURCHASED_ITEMS_FAIL,
        payload: { error: errorMessage }
      });
    }
  };
};

export const resetStarredPurchasedItems = () => async (dispatch) => {
  dispatch({ type: RESET_STARRED_PURCHASED_ITEMS });
};

export const loadAllPurchasedItems = (filters) => {
  const body = {
    page: 1,
    limit: 20
  };

  Object.keys(filters).forEach((key) => {
    body[key] = filters[key];
  });

  return async (dispatch) => {
    dispatch({
      type: LOAD_ALL_PURCHASED_ITEMS,
      payload: { firstLoad: body.page === 1 }
    });

    const {
      statusCode, errorMessage, data
    } = await api({
      method: 'GET',
      url: Urls.PURCHASED_ITEMS,
      params: body
    });

    if (statusCode === 200) {
      dispatch({ type: LOAD_ALL_PURCHASED_ITEMS_SUCCESS, payload: data });
    } else {
      dispatch({
        type: LOAD_ALL_PURCHASED_ITEMS_FAIL,
        payload: { error: errorMessage }
      });
    }
  };
};

export const resetAllPurchasedItems = () => async (dispatch) => {
  dispatch({ type: RESET_ALL_PURCHASED_ITEMS });
};

export const loadPurchasedItemDetails = (item_id, start_date, end_date) => async (dispatch) => {
  const body = {
    grouped: true
  };
  if (start_date) body.start_date = start_date;
  if (end_date) body.end_date = end_date;

  dispatch({
    type: LOAD_PURCHASED_ITEM_DETAILS,
    payload: { item_id }
  });

  const itemDetailResponse = await api({
    method: 'GET',
    url: parseUrl(Urls.PURCHASED_ITEM_DETAIL, { item_id }),
  });

  const itemTrendResponse = await api({
    method: 'GET',
    url: parseUrl(Urls.PURCHASED_ITEM_TREND, { item_id }),
    params: body
  });

  if (itemDetailResponse.statusCode !== 200 || itemTrendResponse.statusCode !== 200) {
    dispatch({
      type: LOAD_PURCHASED_ITEM_DETAILS_FAIL,
      payload: {
        error: itemDetailResponse.errorMessage ? itemDetailResponse.errorMessage : itemTrendResponse.errorMessage,
        item_id
      }
    });
    return;
  }

  dispatch({
    type: LOAD_PURCHASED_ITEM_DETAILS_SUCCESS,
    payload: {
      item_detail: itemDetailResponse.data,
      trend: itemTrendResponse.data,
      item_id
    }
  });
};

export const setCurrentPurchasedItem = (index) => async (dispatch) => {
  dispatch({
    type: SET_CURRENT_PURCHASED_ITEM,
    payload: { index }
  });
};

export const markStar = async (item) => {
  const item_id = item.id;
  sendMixpanelEvent(MixpanelEvents.ITEM_STARRED, { item_id });
  const {
    statusCode,
    errorMessage
  } = await insightsApi({
    method: 'POST',
    url: parseUrl(Urls.STAR_PURCHASED_ITEM, { item_id }),
  });

  if (statusCode === 200) {
    return null;
  }
  return errorMessage;
};

export const deleteStar = async (item) => {
  const item_id = item.id;
  sendMixpanelEvent(MixpanelEvents.ITEM_STAR_DELETED, { item_id });
  const {
    statusCode,
    errorMessage
  } = await insightsApi({
    method: 'DELETE',
    url: parseUrl(Urls.STAR_PURCHASED_ITEM, { item_id }),
  });

  if (statusCode === 200) {
    return null;
  }
  return errorMessage;
};

export const markStarLocal = (item, starred) => async (dispatch) => {
  dispatch({
    type: MARK_ITEM_STAR_LOCAL,
    payload: { item_id: item.id, starred }
  });
};
