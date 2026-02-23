import { Dimensions } from 'react-native';
import Colors from '../../../styles/Colors';

export default {
  container: {
    flex: 1,
    backgroundColor: Colors.dividerColor
  },
  header: {
    backgroundColor: Colors.white,
    paddingLeft: 20,
    paddingRight: 20
  },
  headerItem: {
    marginTop: 20,
    borderBottomColor: Colors.dividerColor,
    borderBottomWidth: 1
  },
  lastHeaderItem: {
    marginTop: 20,
    flexDirection: 'row',
    justifyContent: 'space-between'
  },
  headerInvoiceNumber: {
    flex: 1,
    alignItems: 'flex-start'
  },
  headerInvoiceDate: {
    flex: 1,
    alignItems: 'center'
  },
  headerInvoiceTotal: {
    flex: 1,
    alignItems: 'flex-end',
    textAlign: 'right'
  },
  headerVendorName: {
    flexDirection: 'row'
  },
  headerHeading: {
    width: '100%',
    fontSize: 10,
    fontWeight: 'bold',
    color: Colors.fadedBlue
  },
  headerLeft: {
    flex: 0.8
  },
  headerRight: {
    flex: 0.2,
    justifyContent: 'flex-end',
    alignItems: 'flex-end',
    flexDirection: 'row'
  },
  tabView: {
    backgroundColor: '#fff',
    flex: 1
  },
  email: {
    width: 20,
    height: 20,
    marginLeft: 15
  },
  flag: {
    width: 15,
    height: 20,
    tintColor: Colors.red,
  },
  headerValue: {
    width: '100%',
    marginTop: 5,
    fontSize: 16,
    color: Colors.verLightBlack,
    marginBottom: 15,
    fontWeight: '500'
  },
  card: {
    borderWidth: 1,
    backgroundColor: '#fff',
    borderColor: 'rgba(0,0,0,0.1)',
    margin: 5,
    height: 150,
    padding: 15,
    shadowColor: '#ccc',
    shadowOffset: { width: 2, height: 2, },
    shadowOpacity: 0.5,
    shadowRadius: 3,
  },
  centerText: {
    textAlign: 'center'
  },
  rightText: {
    textAlign: 'right'
  },
  approveButtonParent: {
    paddingTop: 15,
    paddingLeft: 20,
    paddingBottom: 30,
    paddingRight: 20,
    backgroundColor: Colors.white,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 15 },
    shadowOpacity: 0.8,
    shadowRadius: 1,
  },
  sliderSuccess: {
    fontSize: 25,
    color: Colors.success
  },
  sliderButton: {
    height: 50,
    width: 50
  },
  modalContainer: {
    paddingTop: 20,
    paddingBottom: 20,
    paddingLeft: 10,
    paddingRight: 10,
    backgroundColor: Colors.white,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
    width: Dimensions.get('window').width - 30,
  },
  modalHeading: {
    fontSize: 18,
    fontWeight: 'bold'
  },
  modalInput: {
    borderColor: Colors.secondaryText,
    borderWidth: 1,
    borderRadius: 10,
    width: Dimensions.get('window').width - 50,
    marginTop: 20,
    padding: 10,
  },
  modalButtons: {
    marginTop: 20,
    flexDirection: 'row'
  },
  modalButton: {
    flex: 1
  },
  modalButtonText: {
    textAlign: 'center',
    fontSize: 16
  },
  missing: {
    color: Colors.red
  },
  missingValue: {
    width: '100%',
    marginTop: 5,
    fontSize: 16,
    color: Colors.missing,
    marginBottom: 15,
    fontWeight: 'normal',
    fontStyle: 'italic'
  },
  loading: {
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#fff',
    flex: 1
  },
  timeContainerStyle: {
    minWidth: 85
  },
  suggestionsRowContainer: {
    flexDirection: 'row',
  },
  userAvatarBox: {
    width: 35,
    paddingTop: 2
  },
  userIconBox: {
    height: 45,
    width: 45,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.mention
  },
  usernameInitials: {
    color: '#fff',
    fontWeight: '800',
    fontSize: 14
  },
  userDetailsBox: {
    flex: 1,
    justifyContent: 'center',
    paddingLeft: 10,
    paddingRight: 15
  },
  displayNameText: {
    fontSize: 13,
    fontWeight: '500'
  },
  usernameText: {
    fontSize: 12,
    color: 'rgba(0,0,0,0.6)'
  }
};
