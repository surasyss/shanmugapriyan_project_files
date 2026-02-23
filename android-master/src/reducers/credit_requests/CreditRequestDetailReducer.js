import { SET_CURRENT_CREDIT_REQUEST } from '../../actions';

const INITIAL_STATE = {
  currentCreditRequest: null
};

export default (state = INITIAL_STATE, action) => {
  const { type, payload } = action;
  switch (type) {
    case SET_CURRENT_CREDIT_REQUEST:
      return { ...state, currentCreditRequest: payload.index };
    default:
      return state;
  }
};
