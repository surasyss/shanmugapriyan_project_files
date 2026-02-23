import Colors from '../../../styles/Colors';

export default {
  container: {
    backgroundColor: Colors.white,
    padding: 10,
    flexDirection: 'row',
    justifyContent: 'space-between',
    borderBottomWidth: 1,
    borderBottomColor: Colors.dividerColor
  },
  searchSection: {
    flex: 1,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
  },
  searchIcon: {
    padding: 10,
    height: 20
  },
  input: {
    flex: 1,
    paddingTop: 10,
    paddingRight: 10,
    paddingBottom: 10,
    paddingLeft: 0,
    color: Colors.black,
    fontWeight: '500',
    fontSize: 16
  },
  cancelIcon: {
    height: 20,
    padding: 10,

  },
};
