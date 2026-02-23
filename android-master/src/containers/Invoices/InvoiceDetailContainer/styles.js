import Colors from '../../../styles/Colors';

export default {
  container: {
    flex: 1,
    backgroundColor: Colors.dividerColor
  },
  headerTitleStyle: {
    textAlign: 'left',
    flex: 1,
    marginRight: 25,
    fontSize: 16
  },
  headerButtons: {
    flexDirection: 'row',
    alignItems: 'center'
  },
  up: {
    height: 22,
    width: 22,
    marginRight: 20,
  },
  down: {
    height: 22,
    width: 22,
    marginLeft: 10,
    marginRight: 25
  },
  flag: {
    height: 15,
    width: 10,
    marginLeft: 10,
    marginRight: 20,
    alignItems: 'center'
  },
  more_vertical: {
    height: 15,
    width: 10,
    marginLeft: 10,
    marginRight: 20,
    alignItems: 'center'
  },
  moreSheet: {
    container: {
      borderTopLeftRadius: 10,
      borderTopRightRadius: 10,
      marginLeft: 1,
      marginRight: 1
    }
  }
};
