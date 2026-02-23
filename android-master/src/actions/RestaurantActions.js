import api from '../api';
import Urls from '../api/urls';
import { parseUrl } from '../utils/StringFormatter';

export const LOAD_RESTAURANT_USERS = 'load_restaurant_users';
export const LOAD_RESTAURANT_USERS_SUCCESS = 'load_restaurant_users_success';

export const loadRestaurantUsers = (restaurant_id) => async (dispatch) => {
  dispatch({
    type: LOAD_RESTAURANT_USERS,
  });

  const {
    statusCode, data
  } = await api({
    method: 'GET',
    url: parseUrl(Urls.RESTAURANT_USERS, { restaurant_id }),
  });

  if (statusCode === 200) {
    dispatch({
      type: LOAD_RESTAURANT_USERS_SUCCESS,
      payload: {
        restaurant_id,
        users: data
      }
    });
  }
};
