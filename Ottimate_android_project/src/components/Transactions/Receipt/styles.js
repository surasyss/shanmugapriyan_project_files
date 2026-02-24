import Colors from '../../../styles/Colors';

export default {
  mainView: {
    backgroundColor: Colors.white,
    paddingTop: 10,
    paddingBottom: 10,
    borderBottomColor: Colors.dividerColor,
    borderBottomWidth: 0.5,
    flex: 1,
    justifyContent: 'space-between',
    alignItems: 'center',
    flexDirection: 'row',
  },
  container: {
    flex: 1,
    flexDirection: 'row',
    paddingTop: 10,
  },
  loader: {
    position: 'absolute',
    left: 0,
    right: 0,
    top: 0,
    bottom: 0,
  },
  pdf: {
    height: 50,
    width: 50,
    marginRight: 25
  },
  image: {
    height: 50,
    width: 50,
    marginRight: 25
  },
  rightContainer: {
    flexDirection: 'column',
    justifyContent: 'center',
  },
  date: {
    marginTop: 5,
    fontSize: 12,
    color: Colors.lightGray,
  },
  user: {
    fontWeight: '500',
    fontSize: 14,
    color: Colors.gray,
  },
  progress: {
    flex: 1,
    paddingRight: 10,
    alignItems: 'flex-end'
  },
  successImage: {
    flex: 1,
    width: 30,
    height: 30,
    paddingRight: 10,
    alignItems: 'flex-end',
  },
  done: {
    fontSize: 35,
    color: Colors.success
  }
};
