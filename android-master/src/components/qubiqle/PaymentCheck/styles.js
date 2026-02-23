import Colors from '../../../styles/Colors';

export default {
  mainView: {
    marginTop: 10,
    paddingTop: 10,
    paddingBottom: 20,
    flex: 0.5,
    height: 200,
    backgroundColor: Colors.tab
  },
  oddView: {

  },
  evenView: {
    marginLeft: 10,
  },
  image: {
    height: 175,
    width: '100%'
  },
  waterMarkView: {
    position: 'absolute',
    bottom: 10,
    right: 10,
    backgroundColor: Colors.waterMark,
    borderRadius: 10
  },
  waterMark: {
    width: '50%',
    textAlign: 'center',
    fontWeight: '400',
    fontSize: 16,
    color: Colors.white,
    paddingTop: 10,
    paddingBottom: 10,
    marginLeft: 25,
    marginRight: 25,
  }
};
