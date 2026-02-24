import Colors from '../../../styles/Colors';

export default {
  mainView: {
    flex: 1,
  },
  container: {
    flex: 1,
  },
  loader: {
    position: 'absolute',
    left: 0,
    right: 0,
    top: 0,
    bottom: 0,
  },
  pdf: {
    height: 100,
    width: 100,
  },
  image: {
    height: 100,
    width: 100,
    resizeMode: 'contain'
  },
  galleryParent: {
    alignItems: 'center',
    borderWidth: 1,
    borderColor: Colors.primary,
    borderStyle: 'dotted',
    flex: 1,
    justifyContent: 'center',
    borderRadius: 5,
  },
  galleryIcon: {
    height: 30,
    tintColor: Colors.primary,
  },
  galleryText: {
    marginTop: 5,
    fontSize: 16,
    color: Colors.secondaryText,
  }
};
