import Colors from '../../../styles/Colors';

export default {
  datePickerContainer: {
    borderWidth: 1,
    borderColor: Colors.dividerColor,
    backgroundColor: Colors.white,
    marginLeft: 0,
    marginRight: 0,
    marginTop: 50,
    marginBottom: 0
  },
  datePickerButtons: {
    marginTop: 25,
    marginLeft: 25,
    marginRight: 25,
    marginBottom: 25,
    flexDirection: 'row',
    justifyContent: 'space-between'
  },
  datePickerCancel: {
    color: Colors.primary,
    fontSize: 16,
    fontWeight: 'bold',
    width: '100%',
    textAlign: 'left'
  },
  datePickerSave: {
    color: Colors.primary,
    fontSize: 16,
    fontWeight: 'bold',
    width: '100%',
    textAlign: 'right'
  },
  flex_1: {
    flex: 1
  },
  disabled: {
    color: Colors.secondaryText,
  },
};
