import Colors from '../../../styles/Colors';

export default {
  mainView: {
    marginLeft: 20,
    marginRight: 20,
    borderBottomWidth: 0.5,
    borderBottomColor: Colors.dividerColor,
    paddingTop: 20,
    paddingBottom: 10,
  },
  container: {
    flexDirection: 'row',
  },
  leftView: {
    flex: 0.6
  },
  rightView: {
    flex: 0.4,
    flexDirection: 'row',
    justifyContent: 'flex-end'
  },
  itemName: {
    color: Colors.darkGray,
    fontSize: 12,
    fontWeight: '600'
  },
  missingValue: {
    fontSize: 14,
    color: Colors.red,
    fontWeight: 'normal',
    fontStyle: 'italic'
  },
  quantity: {
    width: '100%',
    textAlign: 'right',
    color: Colors.darkGray,
    fontWeight: '500',
    fontSize: 12,
  },
};
