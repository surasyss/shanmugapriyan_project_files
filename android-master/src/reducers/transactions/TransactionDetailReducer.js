import { SET_CURRENT_TRANSACTION, SET_MEMO_EDIT } from '../../actions';

const INITIAL_STATE = {
  currentTransaction: null,
  isEditMemo: false,
};

export default (state = INITIAL_STATE, action) => {
  const { type, payload } = action;
  switch (type) {
    case SET_CURRENT_TRANSACTION:
      return { ...state, currentTransaction: payload.index };
    case SET_MEMO_EDIT:
      return { ...state, isEditMemo: payload.status };
    default:
      return state;
  }
};
