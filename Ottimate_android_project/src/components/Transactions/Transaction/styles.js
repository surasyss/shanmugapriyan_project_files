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
    flex: 0.75
  },
  rightView: {
    flex: 0.25,
  },
  vendorName: {
    color: Colors.black,
    fontSize: 16,
    fontWeight: 'bold',
    width: '100%'
  },
  userName: {
    marginTop: 5,
    color: Colors.black,
    fontSize: 14,
    width: '100%'
  },
  date: {
    marginTop: 5,
    color: Colors.description,
    fontSize: 14,
    width: '100%'
  },
  amount: {
    color: Colors.black,
    fontSize: 16,
    fontWeight: 'bold',
    width: '100%',
    textAlign: 'right'
  },
  status: {
    marginTop: 5,
    color: Colors.black,
    fontSize: 14,
    width: '100%',
    textAlign: 'right'
  },
  credit: {
    color: Colors.green,
  },
  secondaryText: {
    color: Colors.fadedBlue,
    fontSize: 13,
  },
  missingSecondaryText: {
    color: Colors.red,
    fontSize: 13,
  },

  email: {
    width: 20,
    height: 20,
    marginLeft: 15
  },
  flag: {
    marginLeft: 2,
    marginRight: 2,
    fontSize: 12,
    color: Colors.white,
    paddingLeft: 5,
    paddingRight: 5,
    paddingTop: 3,
    paddingBottom: 3,
    borderRadius: 2,
    overflow: 'hidden',
    fontWeight: 'bold'
  },
  ach_flag: {
    backgroundColor: Colors.ach,
  },
  vcard: {
    backgroundColor: Colors.vcard,
  },
  newAddress: {
    backgroundColor: Colors.newAddress,
  },
  sent: {
    backgroundColor: Colors.sent,
  },
  missing: {
    color: Colors.red,
  },
  paid: {
    backgroundColor: Colors.paid,
  },
  delivered: {
    backgroundColor: Colors.delivered,
  },
  scheduled: {
    backgroundColor: Colors.white,
    color: Colors.scheduled,
    borderWidth: 1,
    borderColor: Colors.scheduled
  },
  pendingApproval: {
    backgroundColor: Colors.pendingApproval,
    color: Colors.black
  },
  cancelled: {
    backgroundColor: Colors.canceled,
    color: Colors.black
  },
  progressContainer: {
    paddingTop: 10,
  },
  progressStatus: {
    paddingBottom: 5,
  }
};
