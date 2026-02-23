import {
  SSO_LOGIN_SUBMIT_FAIL,
  SSO_LOGIN_SUBMIT_SUCCESS,
  SSO_RESET_STATE
} from '../../actions';

const INITIAL_STATE = {
  error: null,
};

export default (state = INITIAL_STATE, action) => {
  const { type, payload } = action;
  switch (type) {
    case SSO_LOGIN_SUBMIT_SUCCESS:
      return {
        ...state, data: payload
      };
    case SSO_LOGIN_SUBMIT_FAIL:
      return {
        ...state, error: payload.error,
      };
    case SSO_RESET_STATE:
      return INITIAL_STATE;
    default:
      return state;
  }
};
