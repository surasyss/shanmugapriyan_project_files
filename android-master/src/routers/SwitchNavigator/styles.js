import Colors from '../../styles/Colors';

export default {
  headerStyle: {
    backgroundColor: Colors.primary,
    elevation: 0, // remove shadow on Android
    shadowOpacity: 0, // remove shadow on iOS,
    shadowColor: 'transparent',
    borderBottomWidth: 0,
  },
  headerTitleStyle: {
    textAlign: 'center',
    flex: 1,
    fontSize: 18
  },
  headerTintColor: Colors.black,
  headerSmallTitleStyle: {
    textAlign: 'center',
    flex: 1,
    fontSize: 14
  },
  headerLeftTitle: {
    textAlign: 'left',
    flex: 1,
    fontSize: 14,
    color: Colors.black,
    marginHorizontal: 0
  },
  subHeaderStyle: {
    backgroundColor: Colors.subHeader,
  },
  selectedIcon: {
    width: 20,
    height: 20,
    resizeMode: 'contain',
    tintColor: Colors.deepSkyBlue,
  },
  unselectedIcon: {
    width: 20,
    height: 20,
    resizeMode: 'contain',
    tintColor: Colors.fadedBlue,
  },
  selectedTabText: {
    marginTop: 5,
    fontSize: 12,
    color: Colors.deepSkyBlue,
    fontWeight: '500',
  },
  unselectedTabText: {
    marginTop: 5,
    fontSize: 12,
    color: Colors.fadedBlue,
    fontWeight: '500',
  },
  listButton: {
    paddingHorizontal: 25,
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10
  },
  listIcon: {
    tintColor: Colors.fadedBlue,
    width: 20,
    height: 20,
    marginRight: 15,
    resizeMode: 'contain',
  },
  listLabel: {
    fontSize: 16,
    color: Colors.fadedBlue,
  },
  logoutIcon: {
    height: 22,
  },
  bottomTabs: {
    borderTopWidth: 1,
    borderTopColor: Colors.border,
    borderTopStyle: 'solid',
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
  },
  bottomTab: {
    paddingTop: 10,
    paddingBottom: 25,
    justifyContent: 'center',
    alignItems: 'center',
    flexDirection: 'column',
  }
};
