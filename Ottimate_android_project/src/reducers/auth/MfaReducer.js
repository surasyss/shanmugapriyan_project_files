import {
  LOGIN_2FA_SUBMIT,
  LOGIN_2FA_SUBMIT_FAIL,
  LOGIN_2FA_SUBMIT_SUCCESS,
  LOGIN_RESEND_MFA, LOGIN_RESEND_MFA_FAIL,
  LOGIN_RESEND_MFA_SUCCESS
} from '../../actions';

const INITIAL_STATE = {
  error: null,
  isLogin: false
};

export default (state = INITIAL_STATE, action) => {
  const { type, payload } = action;
  switch (type) {
    case LOGIN_2FA_SUBMIT:
      return {
        ...state, loading: true, error: '', isLogin: false
      };
    case LOGIN_2FA_SUBMIT_SUCCESS:
      return {
        ...state, loading: false, error: '', isLogin: true, data: payload
      };
    case LOGIN_2FA_SUBMIT_FAIL:
      return {
        ...state, loading: false, error: payload.error, isLogin: false
      };
    case LOGIN_RESEND_MFA:
      return {
        ...state, loading: true, error: '', isLogin: false
      };
    case LOGIN_RESEND_MFA_SUCCESS:
      return {
        ...state, loading: false, error: '', isLogin: false
      };
    case LOGIN_RESEND_MFA_FAIL:
      return {
        ...state, loading: false, error: payload.error, isLogin: false
      };
    default:
      return state;
  }
};
