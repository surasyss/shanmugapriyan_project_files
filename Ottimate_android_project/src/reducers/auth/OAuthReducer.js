import {
  LOGIN_WITH_OAUTH_2FA_SENT,
  LOGIN_WITH_OAUTH_CODE,
  LOGIN_WITH_OAUTH_CODE_FAIL,
  LOGIN_WITH_OAUTH_CODE_SUCCESS
} from '../../actions';

const INITIAL_STATE = {
  error: null,
  isLogin: false,
};

export default (state = INITIAL_STATE, action) => {
  const { type, payload } = action;
  switch (type) {
    case LOGIN_WITH_OAUTH_CODE:
      return {
        ...state, loading: true, error: '', isLogin: false
      };
    case LOGIN_WITH_OAUTH_CODE_SUCCESS:
      return {
        ...state, loading: true, error: '', isLogin: true
      };
    case LOGIN_WITH_OAUTH_CODE_FAIL:
      return {
        ...state, loading: true, error: payload.error, isLogin: false
      };
    case LOGIN_WITH_OAUTH_2FA_SENT:
      const { mfa_token } = payload;
      return {
        ...state, loading: false, error: '', isLogin: false, mfa_token
      };
    default:
      return state;
  }
};
