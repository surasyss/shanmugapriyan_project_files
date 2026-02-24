import Colors from '../../../styles/Colors';

export default {
  container: {
    paddingTop: 15,
    paddingBottom: 15,
    paddingLeft: 25,
    paddingRight: 25,
    borderRadius: 10,
    backgroundColor: Colors.white,
    marginTop: 40
  },
  row: {
    flexDirection: 'row'
  },
  nameIconParent: {
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.primary,
    width: 50,
    height: 50,
    borderRadius: 25
  },
  nameIcon: {
    color: Colors.white,
    fontSize: 20
  },
  nameParent: {
    justifyContent: 'center',
    marginLeft: 15,
  },
  name: {
    fontSize: 16,
    color: Colors.gray
  },
  email: {
    marginTop: 8,
    fontSize: 14,
    color: Colors.gray
  },
  logoutButton: {
    marginTop: 25,
    alignItems: 'flex-end'
  },
  logoutButtonText: {
    color: Colors.primary,
    fontWeight: 'bold'
  }
};
