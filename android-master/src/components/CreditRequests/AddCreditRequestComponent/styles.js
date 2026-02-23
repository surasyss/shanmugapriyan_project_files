import { Dimensions } from 'react-native';
import Colors from '../../../styles/Colors';

const width = Dimensions.get('window').width - 50;

export default {
  container: {
    paddingTop: 25,
    paddingBottom: 25,
    backgroundColor: Colors.white,
    alignItems: 'center',
  },
  scrollViewContainer: {
    backgroundColor: Colors.white,
    marginLeft: 10,
    marginRight: 10,
  },
  formHeading: {
    color: Colors.fadedBlue,
    fontSize: 11,
    fontWeight: 'bold',
    marginBottom: 10
  },
  inputBoxContainer: {
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
  inputBox: {
    width,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center'
  },
  inputBoxText: {
    width: '75%',
    paddingLeft: 15,
    paddingTop: 15,
    paddingBottom: 15,
    fontSize: 16,
    color: Colors.black,
  },
  inputBoxPlaceholder: {
    paddingLeft: 15,
    paddingTop: 15,
    paddingBottom: 15,
    fontSize: 16,
    color: Colors.secondaryText,
  },
  rightIcon: {
    height: 10,
    marginRight: 5
  },
  rightCalendar: {
    height: 15,
    paddingTop: 15,
    paddingBottom: 15,
  },
  inputText: {
    width: '75%',
    paddingLeft: 15,
    fontSize: 16,
    color: Colors.black,
    paddingTop: 15,
    paddingBottom: 15,
  },
  inputPlaceHolder: {
    width: '75%',
    paddingLeft: 15,
    fontSize: 16,
    color: Colors.secondaryText,
    paddingTop: 15,
    paddingBottom: 15,
  },
  submitButton: {
    marginTop: 15
  },
};
