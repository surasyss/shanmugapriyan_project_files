import { SET_CURRENT_PAYMENT } from '../../actions';

const INITIAL_STATE = {
  currentPayment: null
};

export default (state = INITIAL_STATE, action) => {
  const { type, payload } = action;
  switch (type) {
    case SET_CURRENT_PAYMENT:
      return { ...state, currentPayment: payload.index };
    default:
      return state;
  }
};
