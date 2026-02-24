import Colors from '../../../styles/Colors';

export default {
  mainView: {
    backgroundColor: Colors.white,
    borderBottomWidth: 0.8,
    borderBottomColor: Colors.dividerColor,
    paddingTop: 10,
    paddingBottom: 20,
    paddingLeft: 20,
    paddingRight: 20
  },
  container: {
    flex: 1,
    flexDirection: 'row',
    paddingTop: 10,
  },
  leftView: {
    flex: 0.7
  },
  rightView: {
    justifyContent: 'flex-end',
    alignItems: 'flex-end',
    flex: 0.3,
    flexDirection: 'row'
  },
  vendorName: {
    color: Colors.black,
    fontSize: 13,
    fontWeight: 'bold'
  },
  secondaryText: {
    color: Colors.fadedBlue,
    fontSize: 13,
  },
  missingSecondaryText: {
    color: Colors.red,
    fontSize: 13,
  },
  amount: {
    color: Colors.black,
    fontSize: 14,
    fontWeight: 'bold',
    width: '100%',
    textAlign: 'right'
  },
  email: {
    width: 20,
    height: 20,
    marginLeft: 15
  },
  flag: {
    width: 15,
    height: 20,
    tintColor: Colors.red
  },
  missing: {
    color: Colors.red,
  }
};
