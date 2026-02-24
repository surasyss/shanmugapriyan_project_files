import Colors from '../../../styles/Colors';

export default {
  mainView: {
    marginLeft: 20,
    marginRight: 20,
    borderBottomWidth: 0.5,
    borderBottomColor: Colors.dividerColor,
    paddingTop: 10,
    paddingBottom: 20,
  },
  container: {
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
  itemName: {
    color: Colors.black,
    fontSize: 12,
    fontWeight: '600'
  },
  missingValue: {
    fontSize: 14,
    color: Colors.red,
    fontWeight: 'normal',
    fontStyle: 'italic'
  },
  categoryName: {
    fontSize: 12,
    marginTop: 10,
    fontWeight: 'bold',
    color: Colors.lightGray
  },
  quantity: {
    width: '100%',
    textAlign: 'right',
    color: Colors.black,
    fontWeight: '500',
    fontSize: 12,
  },
  unit: {
    width: '100%',
    textAlign: 'right',
    fontSize: 12,
    marginTop: 5,
    fontWeight: 'bold',
    color: Colors.fadedBlue
  },
  valueView: {
    flex: 1
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
  }
};
