import { Dimensions } from 'react-native';
import Colors from '../../../styles/Colors';

const width = Dimensions.get('window').width - 50;

export default {
  container: {
    backgroundColor: Colors.white,
    marginLeft: 0,
    marginRight: 0,
    marginTop: 0,
    marginBottom: 0
  },
  scrollContainer: {
    backgroundColor: Colors.white,
    marginLeft: 20,
    marginRight: 20
  },
  flex_1: {
    flex: 1
  },
  header: {
    marginTop: 50,
    marginLeft: 15,
    marginRight: 15,
    flexDirection: 'row',
    justifyContent: 'space-between'
  },
  headerCancelButtonText: {
    color: Colors.primary,
    fontSize: 16,
    fontWeight: 'bold',
    width: '100%',
    textAlign: 'left'
  },
  headerTitle: {
    color: Colors.black,
    fontSize: 18,
    fontWeight: 'bold',
    width: '100%',
    textAlign: 'center'
  },
  headerClearButtonText: {
    color: Colors.primary,
    fontSize: 16,
    fontWeight: 'bold',
    width: '100%',
    textAlign: 'right'
  },

  formContainer: {
    marginTop: 50,
    marginBottom: 50
  },
  formHeading: {
    color: Colors.fadedBlue,
    fontSize: 11,
    fontWeight: 'bold'
  },

  dropDown: {
    alignItems: 'center',
    flexDirection: 'row',
    width,
    marginTop: 5,
    borderWidth: 1,
    borderColor: Colors.dividerColor,
    borderRadius: 3,
    backgroundColor: Colors.white,
    marginBottom: 20,
    justifyContent: 'space-between'
  },
  dropDownText: {
    width: '75%',
    paddingLeft: 15,
    paddingTop: 15,
    paddingBottom: 15,
    fontSize: 16,
    fontWeight: 'bold',
    color: Colors.black,
  },
  dropDownPlaceholder: {
    paddingLeft: 15,
    paddingTop: 15,
    paddingBottom: 15,
    fontSize: 16,
    color: Colors.secondaryText,
  },
  dropDownList: {
    width,
    borderColor: Colors.dividerColor,
    borderWidth: 1,
    borderRadius: 3,
    shadowColor: '#000000',
    shadowOpacity: 0.5,
    shadowRadius: 2,
    shadowOffset: {
      height: 1,
      width: 1
    }
  },
  dropDownRow: {
    paddingTop: 10,
    paddingBottom: 10,
    paddingLeft: 15,
    paddingRight: 15
  },
  dropDownRowText: {
    fontSize: 16,
    color: Colors.black,
    width: '100%'
  },
  dropDownDivider: {
    height: 0
  },
  dropDownButton: {
    width,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center'
  },
  applyButton: {
    marginTop: 30
  },
  datePickerContainer: {
    borderWidth: 1,
    borderColor: Colors.dividerColor,
    backgroundColor: Colors.white,
    marginLeft: 0,
    marginRight: 0,
    marginTop: 50,
    marginBottom: 0
  },
  datePicker: {
    paddingTop: 50,
    paddingBottom: 50,
    paddingLeft: 25,
    paddingRight: 25
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
  filterRightCalendar: {
    height: 15,
    paddingTop: 15,
    paddingBottom: 15,
    marginRight: 5
  },
  filterRightIcon: {
    height: 10,
    marginRight: 5
  },
  dropDownAutoComplete: {
    width,
    marginTop: 5,
    backgroundColor: Colors.white,
    marginBottom: 20,
    borderColor: Colors.dividerColor,
    borderWidth: 1,
    borderRadius: 3,
  },
  dropDownAutoCompleteText: {
    width: '75%',
    paddingLeft: 15,
    fontSize: 16,
    fontWeight: 'bold',
    color: Colors.black,
  },
  dropDownPlaceholderAutoCompleteText: {
    width: '75%',
    paddingLeft: 15,
    fontSize: 16,
    color: Colors.secondaryText,
  },
  disabled: {
    color: Colors.secondaryText,
  },
};
