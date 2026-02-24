import { LOAD_RESTAURANT_USERS_SUCCESS } from '../../actions';

const INITIAL_STATE = {
  data: {}
};

export default (state = INITIAL_STATE, action) => {
  const { type, payload } = action;
  switch (type) {
    case LOAD_RESTAURANT_USERS_SUCCESS:
      const { restaurant_id, users } = payload;
      const { data } = state;
      data[restaurant_id] = users;
      return { ...state, data };
    default:
      return state;
  }
};
