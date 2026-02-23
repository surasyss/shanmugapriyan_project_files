import {
  LOGIN_WITH_OAUTH_2FA_SUBMIT,
  LOGIN_WITH_OAUTH_2FA_SUBMIT_FAIL,
  LOGIN_WITH_OAUTH_2FA_SUBMIT_SUCCESS
} from '../../actions';

const INITIAL_STATE = {
  error: null,
  isLogin: false
};

export default (state = INITIAL_STATE, action) => {
  const { type, payload } = action;
  switch (type) {
    case LOGIN_WITH_OAUTH_2FA_SUBMIT:
      return {
        ...state, loading: true, error: '', isLogin: false
      };
    case LOGIN_WITH_OAUTH_2FA_SUBMIT_SUCCESS:
      return {
        ...state, loading: false, error: '', isLogin: true, data: payload
      };
    case LOGIN_WITH_OAUTH_2FA_SUBMIT_FAIL:
      return {
        ...state, loading: false, error: payload.error, isLogin: false
      };
    default:
      return state;
  }
};
