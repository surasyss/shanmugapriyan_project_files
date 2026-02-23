import {
  LOGIN_2FA_SENT,
  LOGIN_FAIL,
  LOGIN_RESEND_MFA_SUCCESS,
  LOGIN_SUCCESS,
  LOGIN_USER,
  LOGIN_WITH_TOKEN, LOGIN_WITH_TOKEN_FAIL,
  LOGIN_WITH_TOKEN_SUCCESS,
} from '../../actions';

const INITIAL_STATE = {
  error: null,
  isLogin: false,
  mfa_token: null
};

export default (state = INITIAL_STATE, action) => {
  const { type, payload } = action;
  switch (type) {
    case LOGIN_USER:
      return {
        ...state, loading: true, error: '', isLogin: false, mfa_token: null
      };
    case LOGIN_SUCCESS:
      return {
        ...state, loading: false, error: '', isLogin: true, data: payload, mfa_token: null
      };
    case LOGIN_FAIL:
      return {
        ...state, loading: false, error: payload.error, isLogin: false, mfa_token: null
      };
    case LOGIN_2FA_SENT:
      const { mfa_token } = payload;
      return {
        ...state, loading: false, error: '', isLogin: false, mfa_token
      };
    case LOGIN_RESEND_MFA_SUCCESS:
      return {
        ...state, loading: false, error: '', isLogin: false, mfa_token: payload.mfa_token
      };
    case LOGIN_WITH_TOKEN:
      return {
        ...state, loading: true, error: '', isLogin: false, mfa_token: null
      };
    case LOGIN_WITH_TOKEN_SUCCESS:
      return {
        ...state, loading: false, error: '', isLogin: true, data: payload, mfa_token: null
      };
    case LOGIN_WITH_TOKEN_FAIL:
      return {
        ...state, loading: false, error: payload.error, isLogin: false, mfa_token: null
      };
    default:
      return state;
  }
};
