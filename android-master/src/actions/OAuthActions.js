import { OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET, OAUTH_REDIRECT_URI } from 'react-native-dotenv';
import api from '../api';
import Urls from '../api/urls';
import Adapter from '../utils/Adapter';
import { MixpanelEvents, sendMixpanelEvent, setMixpanelUser } from '../utils/mixpanel/MixPanelAdapter';
import Constants from '../utils/Constants';
import { saveToken } from './AuthActions';

export const LOGIN_WITH_OAUTH_CODE = 'login_with_oauth_code';
export const LOGIN_WITH_OAUTH_CODE_SUCCESS = 'login_with_oauth_code_success';
export const LOGIN_WITH_OAUTH_CODE_FAIL = 'login_with_oauth_code_fail';
export const LOGIN_WITH_OAUTH_2FA_SENT = 'login_with_oauth_2fa_sent';

export const LOGIN_WITH_OAUTH_2FA_SUBMIT = 'login_with_oauth_2fa_submit';
export const LOGIN_WITH_OAUTH_2FA_SUBMIT_SUCCESS = 'login_with_oauth_2fa_submit_success';
export const LOGIN_WITH_OAUTH_2FA_SUBMIT_FAIL = 'login_with_oauth_2fa_submit_fail';

export const loginWithOAuthCode = (code, csrftoken) => async (dispatch) => {
  dispatch({ type: LOGIN_WITH_OAUTH_CODE });

  await Adapter.set(Constants.CSRF_TOKEN, csrftoken);
  const formData = new FormData();
  formData.append('code', code);
  formData.append('grant_type', 'authorization_code');
  formData.append('client_id', OAUTH_CLIENT_ID);
  formData.append('client_secret', OAUTH_CLIENT_SECRET);
  formData.append('redirect_uri', OAUTH_REDIRECT_URI);

  const {
    statusCode, errorMessage, data
  } = await api({
    method: 'POST',
    url: Urls.OAUTH_TOKEN,
    data: formData
  });

  if (statusCode === 200) {
    const { access_token, token_type } = data;
    await Adapter.setToken(access_token);
    await Adapter.setTokenType(token_type);

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
      dispatch({ type: LOGIN_WITH_OAUTH_CODE_SUCCESS, payload: null });
    } else {
      dispatch({
        type: LOGIN_WITH_OAUTH_CODE_FAIL,
        payload: { error: errorMessage }
      });
    }
  } else if (statusCode === 202) {
    const { mfa_token } = data;
    dispatch({ type: LOGIN_WITH_OAUTH_2FA_SENT, payload: { mfa_token } });
  } else {
    dispatch({
      type: LOGIN_WITH_OAUTH_CODE_FAIL,
      payload: { error: errorMessage }
    });
  }
};

export const loginWithOAuthMfa = (token, code) => async (dispatch) => {
  dispatch({ type: LOGIN_WITH_OAUTH_2FA_SUBMIT });

  try {
    const {
      statusCode, data
    } = await api({
      method: 'POST',
      url: token,
      data: { code }
    });

    if (statusCode === 200) {
      const { access_token, token_type } = data;
      await Adapter.setToken(access_token);
      await Adapter.setTokenType(token_type);

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
        dispatch({ type: LOGIN_WITH_OAUTH_2FA_SUBMIT_SUCCESS, payload: { token } });
      } else {
        dispatch({
          type: LOGIN_WITH_OAUTH_2FA_SUBMIT_FAIL,
          payload: { error: userInfo.errorMessage }
        });
      }
    } else {
      dispatch({
        type: LOGIN_WITH_OAUTH_2FA_SUBMIT_FAIL,
        payload: { error: 'The Confirmation Code is incorrect. please try again' }
      });
    }
  } catch (e) {
    dispatch({
      type: LOGIN_WITH_OAUTH_2FA_SUBMIT_FAIL,
      payload: { error: 'The Confirmation Code is incorrect. please try again' }
    });
  }
};
