import {
  CREATE_CREDIT_REQUEST, CREATE_CREDIT_REQUEST_FAIL,
  CREATE_CREDIT_REQUEST_SUCCESS,
  LOGOUT,
  SET_ADD_CREDIT_REQUEST_DATA
} from '../../actions';

const INITIAL_STATE = {
  data: {},
  loading: false,
};

export default (state = INITIAL_STATE, action) => {
  const { type, payload } = action;
  switch (type) {
    case SET_ADD_CREDIT_REQUEST_DATA:
      const { key, value } = payload;
      const { data } = state;
      data[key] = value;
      return { ...state, data };
    case CREATE_CREDIT_REQUEST:
      return { ...state, loading: true };
    case CREATE_CREDIT_REQUEST_SUCCESS:
      return {
        data: {},
        loading: false
      };
    case CREATE_CREDIT_REQUEST_FAIL:
      return { ...state, loading: false };
    case LOGOUT:
      return INITIAL_STATE;
    default:
      return state;
  }
};
