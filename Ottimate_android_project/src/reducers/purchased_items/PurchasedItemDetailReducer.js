import { SET_CURRENT_PURCHASED_ITEM } from '../../actions';

const INITIAL_STATE = {
  currentItem: null
};

export default (state = INITIAL_STATE, action) => {
  const { type, payload } = action;
  switch (type) {
    case SET_CURRENT_PURCHASED_ITEM:
      return { ...state, currentItem: payload.index };
    default:
      return state;
  }
};
