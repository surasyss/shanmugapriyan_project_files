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
    flex: 1
  },
  rightView: {
    justifyContent: 'flex-end',
    alignItems: 'flex-end',
    flex: 0.45,
    flexDirection: 'column'
  },
  itemName: {
    color: Colors.black,
    fontSize: 13,
    fontWeight: 'bold'
  },
  secondaryText: {
    marginTop: 10,
    color: Colors.fadedBlue,
    fontSize: 13,
  },
  missingSecondaryText: {
    color: Colors.red,
    fontSize: 13,
  },
  missing: {
    color: Colors.red,
  },
  red: {
    color: Colors.red,
  },
  green: {
    color: Colors.green,
  },
  changeText: {
    marginTop: 15,
    fontSize: 14,
    fontWeight: 'bold'
  },
  starButton: {
    marginBottom: 15,
  },
  starIcon: {
    height: 25
  }

};
