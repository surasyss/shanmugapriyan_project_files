import { SET_CURRENT_INVOICE } from '../../actions';

const INITIAL_STATE = {
  currentInvoice: null
};

export default (state = INITIAL_STATE, action) => {
  const { type, payload } = action;
  switch (type) {
    case SET_CURRENT_INVOICE:
      return { ...state, currentInvoice: payload.index };
    default:
      return state;
  }
};
