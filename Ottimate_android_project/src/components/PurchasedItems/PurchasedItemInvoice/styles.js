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
    flex: 0.4
  },
  rightView: {
    position: 'relative',
    flex: 0.6,
    flexDirection: 'row',
    justifyContent: 'space-between'
  },
  valueView: {
    flex: 1
  },
  flexHalf: {
    flex: 0.5
  },
  restaurant: {
    color: Colors.black,
    fontSize: 14,
  },
  quantity: {
    width: '100%',
    textAlign: 'right',
    color: Colors.black,
    fontWeight: '500',
    fontSize: 12,
  },
  left: {
    textAlign: 'left'
  },
  right: {
    textAlign: 'right',
  },
  heading: {
    color: Colors.fadedBlue,
    fontSize: 11,
    fontWeight: '600',
    width: '100%',
  },
  secondaryText: {
    width: '100%',
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
  starIcon: {
    height: 25
  },

};
