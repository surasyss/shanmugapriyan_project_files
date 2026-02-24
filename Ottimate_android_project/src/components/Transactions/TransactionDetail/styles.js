import Colors from '../../../styles/Colors';

export default {
  container: {
    flex: 1,
    padding: 20,
    backgroundColor: Colors.white
  },
  containerScroll: {
    paddingBottom: 75,
  },
  transactionId: {
    color: Colors.fadedBlue,
    fontSize: 12,
    fontWeight: '500',
    marginBottom: 15,
  },
  transactionHeader: {
    flex: 1,
    flexDirection: 'row',
    justifyContent: 'space-between',
    borderBottomColor: Colors.dividerColor,
    paddingBottom: 20,
    borderBottomWidth: 0.25,
    marginBottom: 10,
  },
  modalHeaderCloseText: {
    textAlign: 'center',
    paddingLeft: 5,
    paddingRight: 5
  },
  transactionHeaderLeft: {
    flex: 0.7
  },
  transactionHeaderRight: {
    flex: 0.3
  },
  merchant: {
    fontWeight: '500',
    fontSize: 16,
    color: Colors.gray,
  },
  transactionDate: {
    fontSize: 12,
    marginTop: 5,
    color: Colors.description,
  },
  amount: {
    fontWeight: 'bold',
    fontSize: 20,
    textAlign: 'right',
    color: Colors.gray,
  },
  transactionDetails: {
    borderBottomColor: Colors.dividerColor,
    paddingBottom: 20,
    borderBottomWidth: 0.25,
    marginBottom: 10,
  },
  transactionDetailRow: {
    marginTop: 15,
    flex: 1,
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  transactionDetailLeft: {
    color: Colors.gray,
    flex: 0.5
  },
  transactionDetailRight: {
    color: Colors.black,
    flex: 0.5,
    fontWeight: '500',
    textAlign: 'right',
  },
  receiptsHeading: {
    color: Colors.fadedBlue,
    fontSize: 12,
    fontWeight: 'bold',
    marginBottom: 15,
  },
  addReceiptButton: {
    marginTop: 15,
    marginBottom: 100,
    width: '80%',
    flex: 1,
    flexDirection: 'row',
    justifyContent: 'flex-start',
  },
  addReceiptIconParent: {
    marginRight: 15,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.lightBlue,
    borderRadius: 5,
  },
  addReceiptIcon: {
    height: 20,
    width: 20,
    margin: 15,
  },
  addReceiptTitle: {
    fontWeight: 'bold',
    fontSize: 14,
    color: Colors.deepSkyBlue,
  },
  addReceiptDescription: {
    fontSize: 12,
    color: Colors.blueDescription,
    marginTop: 5,
  },
  pdfModal: {
    marginTop: 100,
    marginBottom: 100,
  },
  pdfCloseParent: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    marginBottom: 5,
  },
  pdfCloseButton: {
    height: 15,
    width: 15,
    resizeMode: 'contain'
  },
  addMemoRow: {
    marginTop: 15,
    display: 'flex',
    flexDirection: 'row',
    alignItems: 'center',
  },
  addMemoText: {
    marginLeft: 10,
    color: Colors.iconGray,
  },
  tagIcon: {
    color: Colors.iconGray,
  },
  editMemoRow: {
    marginTop: 15,
    flexDirection: 'column',
  },
  textInputTheme: {
    colors: {
      primary: Colors.lightGray,
      background: Colors.white,
    }
  },
  memoButtonContainer: {
    display: 'flex',
    flexDirection: 'row',
    justifyContent: 'flex-end',
    marginTop: 5,
  },
  discardLabel: {
    fontSize: 10,
    color: Colors.black,
  },
  discardButton: {
    borderColor: Colors.black,
  },
  saveButtonLabel: {
    fontSize: 10,
  },
  saveButton: {
    marginLeft: 15,
    borderColor: Colors.black,
  },
  saveButtonTheme: {
    colors: {
      primary: Colors.primary
    }
  },
  memoRow: {
    marginTop: 15,
  },
  memoContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 2,
  },
  memoText: {
    marginRight: 10,
  }
};
