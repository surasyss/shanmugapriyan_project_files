import Colors from '../../../styles/Colors';

export default {
  container: {
    flexDirection: 'row',
    paddingTop: 15,
    paddingBottom: 15,
    paddingLeft: 20,
    paddingRight: 20,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  leftView: {
    flex: 0.6
  },
  rightView: {
    flex: 0.4,
    flexDirection: 'column',
    justifyContent: 'flex-end',
    alignItems: 'flex-end'
  },
  itemName: {
    color: Colors.darkGray,
    fontSize: 14,
    fontWeight: 'bold'
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
    fontWeight: 'bold',
    fontSize: 14,
  },
  item: {
    flexDirection: 'row',
    paddingTop: 10,
    marginTop: 5,
    marginBottom: 5
  },
  leftItemView: {
    flex: 0.45,
    paddingLeft: 20,
  },
  rightItemView: {
    paddingRight: 20,
    position: 'relative',
    flex: 0.55,
    flexDirection: 'row',
    justifyContent: 'space-between'
  },
  itemItemName: {
    color: Colors.black,
    fontSize: 12,
    width: '100%',
    flex: 1
  },
  categoryName: {
    fontSize: 12,
    marginTop: 10,
    fontWeight: 'bold',
    color: Colors.lightGray
  },
  itemQuantity: {
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
  bold: {
    fontWeight: 'bold'
  },
  heading: {
    color: Colors.fadedBlue,
    fontSize: 11,
    fontWeight: '600',
    width: '100%',
  },
  up_down: {
    height: 22,
    width: 22,
    justifyContent: 'flex-end',
    alignItems: 'flex-end',
    marginTop: 5
  }
};
