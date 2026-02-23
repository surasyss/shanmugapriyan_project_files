import { ADD_LIST_IMAGES, DELETE_IMAGES, DELETE_ALL_CAPTURE_IMAGES } from "../../actions";

const INITIAL_STATE = {
    ListDataImages: [],
};

export default (state = INITIAL_STATE, action) => {
    const { type, payload } = action;

    switch (type) {
        case ADD_LIST_IMAGES:
            state.ListDataImages.push(payload)
            return { ...state };
        case DELETE_IMAGES:
            state.ListDataImages.splice(payload, 1)
            return {...state};
        case DELETE_ALL_CAPTURE_IMAGES:
            state.ListDataImages = []
            return {...state};
        default:
            return state;
    }
};

---------------------------------- switch ---------------

  InvoicePreview: {
    screen: InvoicePreviewContainer,
    navigationOptions: () => ({
      headerBackTitle: null,
    })
  },
