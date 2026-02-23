import axios from 'axios';
import DeviceInfo from 'react-native-device-info';
import api from '../api';
import Urls from '../api/urls';
import Adapter from '../utils/Adapter';
import { MixpanelEvents, sendMixpanelEvent, setMixpanelUser } from '../utils/mixpanel/MixPanelAdapter';
import showAlert from '../utils/QubiqleAlert';
import Constants from '../utils/Constants';
import { parseUrl } from '../utils/StringFormatter';

export const LOGIN_USER = 'login_user';
export const LOGIN_SUCCESS = 'login_success';
export const LOGIN_2FA_SENT = 'login_2fa_sent';
export const LOGIN_FAIL = 'login_fail';

export const SSO_LOGIN_SUBMIT_SUCCESS = 'sso_login_submit_success';
export const SSO_LOGIN_SUBMIT_FAIL = 'sso_login_submit_fail';
export const SSO_RESET_STATE = 'sso_login_reset';

export const LOGIN_2FA_SUBMIT = 'login_2fa_submit';
export const LOGIN_2FA_SUBMIT_SUCCESS = 'login_2fa_submit_success';
export const LOGIN_2FA_SUBMIT_FAIL = 'login_2fa_submit_fail';

export const LOGIN_RESEND_MFA = 'login_resend_mfa';
export const LOGIN_RESEND_MFA_SUCCESS = 'login_resend_mfa_success';
export const LOGIN_RESEND_MFA_FAIL = 'login_resend_mfa_fail';

export const LOGOUT = 'logout';

export const LOAD_RESTAURANTS_SUCCESS = 'load_restaurants_success';
export const LOAD_USER_DETAILS = 'load_user_details';
export const LOAD_USER_SUCCESS = 'load_user_success';

export const LOGIN_WITH_TOKEN = 'login_with_token';
export const LOGIN_WITH_TOKEN_SUCCESS = 'login_with_token_success';
export const LOGIN_WITH_TOKEN_FAIL = 'login_with_token_fail';

export const LOAD_COMPANY_SUCCESS = 'load_company_success';

export const loginUser = ({ username, password }) => async (dispatch) => {
  dispatch({ type: LOGIN_USER });

  const {
    statusCode, errorMessage, data
  } = await api({
    method: 'POST',
    url: Urls.LOGIN,
    data: { username, password }
  });

  if (statusCode === 200) {
    let { token } = data;
    await Adapter.setToken(token);
    token = await Adapter.getToken();

    const userInfo = await api({
      method: 'GET',
      url: Urls.USER_INFO,
    });
    if (userInfo.statusCode === 200) {
      await Adapter.setUser(userInfo.data);
      await setMixpanelUser(data);
      await sendMixpanelEvent(MixpanelEvents.USER_LOGGED_IN, userInfo.data);
      const device_token = await Adapter.get(Constants.PUSHY_TOKEN);
      saveToken(device_token);
      dispatch({ type: LOGIN_SUCCESS, payload: { token } });
    } else {
      dispatch({
        type: LOGIN_FAIL,
        payload: { error: userInfo.errorMessage }
      });
    }
  } else if (statusCode === 202) {
    const { mfa_token } = data;
    dispatch({ type: LOGIN_2FA_SENT, payload: { mfa_token } });
  } else {
    dispatch({
      type: LOGIN_FAIL,
      payload: { error: errorMessage }
    });
  }
};

export const loginMfa = (token, code) => async (dispatch) => {
  dispatch({ type: LOGIN_2FA_SUBMIT });

  try {
    const { data, status } = await axios.post(token, { code });
    if (status === 200) {
      let { token } = data;
      await Adapter.setToken(token);
      token = await Adapter.getToken();
      const userInfo = await api({
        method: 'GET',
        url: Urls.USER_INFO,
      });
      if (userInfo.statusCode === 200) {
        await Adapter.setUser(userInfo.data);
        await setMixpanelUser(data);
        await sendMixpanelEvent(MixpanelEvents.USER_LOGGED_IN, userInfo.data);
        const device_token = await Adapter.get(Constants.PUSHY_TOKEN);
        saveToken(device_token);
        dispatch({ type: LOGIN_2FA_SUBMIT_SUCCESS, payload: { token } });
      } else {
        dispatch({
          type: LOGIN_2FA_SUBMIT_FAIL,
          payload: { error: userInfo.errorMessage }
        });
      }
    } else {
      dispatch({
        type: LOGIN_2FA_SUBMIT_FAIL,
        payload: { error: 'The Confirmation Code is incorrect. please try again' }
      });
    }
  } catch (e) {
    dispatch({
      type: LOGIN_2FA_SUBMIT_FAIL,
      payload: { error: 'The Confirmation Code is incorrect. please try again' }
    });
  }
};

export const resendMfa = ({ username, password }) => async (dispatch) => {
  dispatch({ type: LOGIN_RESEND_MFA });

  const {
    statusCode, errorMessage, data
  } = await api({
    method: 'POST',
    url: Urls.LOGIN,
    data: { username, password }
  });

  if (statusCode === 202) {
    const { mfa_token } = data;
    dispatch({ type: LOGIN_RESEND_MFA_SUCCESS, payload: { mfa_token } });
    showAlert('Confirmation Code Resent', 'Confirmation Code has been resent to your mobile');
  } else {
    dispatch({
      type: LOGIN_RESEND_MFA_FAIL,
      payload: { error: errorMessage }
    });
  }
};

export const loadUserInfo = () => async (dispatch) => {
  const user = await Adapter.getUser();
  dispatch({
    type: LOAD_USER_DETAILS,
    payload: {
      loading: true,
    }
  });

  const {
    statusCode, data
  } = await api({
    method: 'GET',
    url: Urls.USER_INFO,
  });

  if (statusCode === 200) {
    await Adapter.setUser(data);
    await setMixpanelUser(data);
    dispatch({
      type: LOAD_USER_SUCCESS,
      payload: data
    });
    const device_token = await Adapter.get(Constants.PUSHY_TOKEN);
    saveToken(device_token);
  } else {
    dispatch({
      type: LOAD_USER_SUCCESS,
      payload: user
    });
  }
};

export const loadRestaurants = () => async (dispatch) => {
  const restaurants = await Adapter.getRestaurants();
  dispatch({
    type: LOAD_RESTAURANTS_SUCCESS,
    payload: restaurants
  });

  const {
    statusCode, data
  } = await api({
    method: 'GET',
    url: Urls.RESTAURANTS,
  });
  if (statusCode === 200) {
    await Adapter.setRestaurants(data);
    dispatch({
      type: LOAD_RESTAURANTS_SUCCESS,
      payload: data
    });
  }
};

export const loadCompanies = () => async (dispatch) => {
  const companies = await Adapter.getCompanies();
  dispatch({
    type: LOAD_COMPANY_SUCCESS,
    payload: companies
  });

  const {
    statusCode, data
  } = await api({
    method: 'GET',
    url: Urls.COMPANIES,
  });

  if (statusCode === 200) {
    await Adapter.setCompanies(data);
    dispatch({
      type: LOAD_COMPANY_SUCCESS,
      payload: data
    });
  }
};

export const loginWithToken = (token) => async (dispatch) => {
  await Adapter.setUser(null);
  await Adapter.setToken(null);
  await Adapter.setRestaurants(null);
  await Adapter.setCompanies(null);
  await Adapter.setToken(token);

  dispatch({ type: LOGIN_WITH_TOKEN });

  const {
    statusCode, data, errorMessage
  } = await api({
    method: 'GET',
    url: Urls.USER_INFO,
  });

  if (statusCode === 200) {
    await Adapter.setUser(data);
    await setMixpanelUser(data);
    dispatch({
      type: LOGIN_WITH_TOKEN_SUCCESS,
      payload: data
    });
  } else {
    await Adapter.setToken(null);
    dispatch({
      type: LOGIN_WITH_TOKEN_FAIL,
      payload: { error: errorMessage }
    });
  }
};

export const logout = () => async (dispatch) => {
  const device_id = DeviceInfo.getUniqueId();
  await api({
    method: 'DELETE',
    url: parseUrl(Urls.DELETE_PUSH_TOKEN, { device_id }),
  });
  await Adapter.logout();
  dispatch({ type: LOGOUT });
};

export const saveToken = (device_token) => {
  const device_id = DeviceInfo.getUniqueId();
  api({
    method: 'POST',
    url: Urls.PUSH_TOKEN,
    data: { device_token, device_id }
  });
};

export const checkSSOUser = (email) => async (dispatch) => {
  try {
    const { data, statusCode, errorMessage } = await api({
      method: 'GET',
      url: Urls.SSO_LOGIN,
      params: {
        email
      }
    });
    if (statusCode === 200) {
      dispatch({ type: SSO_LOGIN_SUBMIT_SUCCESS, payload: data });
    } else {
      dispatch({
        type: SSO_LOGIN_SUBMIT_FAIL,
        payload: { error: errorMessage }
      });
    }
  } catch (e) {
    dispatch({
      type: SSO_LOGIN_SUBMIT_FAIL,
      payload: { error: 'Something went wrong. Please try again' }
    });
  }
};

export const resetSSOData = () => async (dispatch) => {
  dispatch({
    type: SSO_RESET_STATE,
  });
};
