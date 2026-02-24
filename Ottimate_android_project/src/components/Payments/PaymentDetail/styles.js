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
  firstHeaderItem: {
    marginTop: 20,
    borderBottomColor: Colors.dividerColor,
    borderBottomWidth: 1,
    flexDirection: 'row'
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
    color: Colors.fadedBlue,
    flexDirection: 'row'
  },
  headerLeft: {
    flex: 0.65,
  },
  headerRight: {
    flex: 0.35,
  },
  tabView: {
    backgroundColor: '#fff',
    flex: 1
  },
  flag: {
    alignItems: 'center',
    justifyContent: 'center',
    marginLeft: 10,
    flex: 0.3
  },
  vendor: {
    flex: 0.7
  },
  headerValue: {
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
    elevation: 2
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
    alignItems: 'center'
  },
  modalHeading: {
    fontSize: 18,
    fontWeight: 'bold'
  },
  modalInput: {
    borderColor: Colors.secondaryText,
    borderWidth: 1,
    borderRadius: 10,
    width: '90%',
    marginTop: 20,
    padding: 10
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
  pdfModal: {
    justifyContent: 'center',
    alignItems: 'center',
    height: Dimensions.get('window').height - 150,
    width: Dimensions.get('window').width - 10,
    borderRadius: 15,
    backgroundColor: Colors.transparent,
  },
  pdf: {
    marginTop: 20,
    width: Dimensions.get('window').width - 10,
    height: Dimensions.get('window').height - 150,
    backgroundColor: Colors.transparent
  },
  closeIcon: {
    height: 20
  },
  closeButton: {
    position: 'absolute',
    right: 5,
    top: 0
  },
  row: {
    flexDirection: 'row'
  },
  right: {
    textAlign: 'right'
  },
  status: {
    color: '#737373',
    marginTop: 5,
    fontSize: 14,
    marginBottom: 15,
    fontWeight: '500',
    fontStyle: 'italic'
  }
};
