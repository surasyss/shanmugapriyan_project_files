import Colors from '../../../styles/Colors';

export default {
  container: {
    alignItems: 'center',
    backgroundColor: Colors.white,
    padding: 20,
    flexDirection: 'row',
    justifyContent: 'space-between',
    borderBottomWidth: 1,
    borderBottomColor: Colors.dividerColor
  },
  filter: {
    height: 20
  },
  title: {
    fontSize: 14,
    fontWeight: 'bold',
    color: Colors.gray,
    width: '100%',
    textAlign: 'center',
    flex: 1
  },
  filterCountParent: {
    alignItems: 'center',
    justifyContent: 'center',
    width: 30,
    height: 30,
    backgroundColor: Colors.primary,
    borderRadius: 30,
  },
  filterCount: {
    fontSize: 16,
    fontWeight: 'bold',
    color: Colors.white,
  },
  search: {
    height: 20
  },

};
