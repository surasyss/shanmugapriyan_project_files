import Colors from '../../../styles/Colors';

export default {
  container: {
    backgroundColor: Colors.black,
    flex: 1
  },
  image: {
    height: '100%',
    width: '100%',
    backgroundColor: Colors.black,
  },
  topBar: {
    marginTop: 25,
    backgroundColor: Colors.black,
    paddingRight: 5,
    paddingLeft: 20,
    paddingTop: 15,
    paddingBottom: 15,
    alignItems: 'flex-end',
    flexDirection: 'row',
    justifyContent: 'flex-end'
  },
  deleteText: {
    color: Colors.white,
    fontSize: 16,
    marginRight: 25
  },
  closeIcon: {
    height: 20
  },
};
