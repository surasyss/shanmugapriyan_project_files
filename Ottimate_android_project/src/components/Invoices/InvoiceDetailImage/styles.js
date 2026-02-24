import { Dimensions } from 'react-native';
import Colors from '../../../styles/Colors';

export default {
  container: {
    backgroundColor: 'white', paddingBottom: 20
  },
  containerStyle: {
    flexGrow: 1, justifyContent: 'space-between', flexDirection: 'column'
  },
  imageContainer: {
    flex: 1,
    width: Dimensions.get('window').width,
    backgroundColor: Colors.white
  },
  bottomContainer: {
    justifyContent: 'flex-end'
  },
  image: {
    height: '100%', width: '100%', backgroundColor: '#fff'
  },
  header: {
    borderTopWidth: 1,
    borderTopColor: Colors.dividerColor,
    backgroundColor: Colors.white,
    paddingLeft: 20,
    paddingRight: 20
  },
  headerVendorName: {
    flexDirection: 'row'
  },
  headerItem: {
    marginTop: 20,
    borderBottomColor: Colors.dividerColor,
    borderBottomWidth: 1
  },
  headerLeft: {
    flex: 0.8
  },
  headerRight: {
    flex: 0.2,
    alignItems: 'flex-end',
    flexDirection: 'row',
    justifyContent: 'flex-end',
  },
  email: {
    width: 20,
    height: 20,
    alignItems: 'flex-end',
    marginLeft: 15
  },
  flag: {
    width: 15,
    height: 20,
    tintColor: Colors.red,
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
  headerHeading: {
    width: '100%',
    fontSize: 10,
    fontWeight: 'bold',
    color: Colors.fadedBlue
  },
  headerValue: {
    width: '100%',
    marginTop: 5,
    fontSize: 16,
    color: Colors.verLightBlack,
    marginBottom: 15,
    fontWeight: '500'
  },
  waterMarkView: {
    position: 'absolute',
    bottom: 10,
    right: 10,
    backgroundColor: Colors.waterMark,
    borderRadius: 10
  },
  waterMark: {
    width: '50%',
    textAlign: 'center',
    fontWeight: '400',
    fontSize: 16,
    color: Colors.white,
    paddingTop: 10,
    paddingBottom: 10,
    marginLeft: 25,
    marginRight: 25
  },
  centerText: {
    textAlign: 'center'
  },
  rightText: {
    textAlign: 'right'
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
};
