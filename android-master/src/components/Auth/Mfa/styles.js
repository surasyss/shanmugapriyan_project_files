import { Dimensions } from 'react-native';
import Colors from '../../../styles/Colors';

export default {
  container: {
    position: 'relative',
    height: Dimensions.get('window').height
  },
  logoParent: {
    width: Dimensions.get('window').width,
    height: Dimensions.get('window').height / 3,
    backgroundColor: Colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  logo: {
    justifyContent: 'center',
    height: Dimensions.get('window').height / 5,
    resizeMode: 'contain'
  },
  formParent: {
    marginTop: 40,
    marginLeft: 40,
    marginRight: 40
  },
  inputParent: {
    width: '100%',
    marginTop: 20,
    paddingVertical: 10,
    borderBottomColor: Colors.secondaryText,
    borderBottomWidth: 1
  },
  input: {
    fontSize: 16,
    color: Colors.gray,
    paddingBottom: 10
  },
  signInParent: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    justifyContent: 'flex-end'
  },
  goBackText: {
    textAlign: 'left',
    color: Colors.red,
    fontSize: 20,
    marginRight: 25,
    marginBottom: 20
  },
  signInButton: {
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.primary,
    width: 70,
    height: 70,
    borderRadius: 35,
    shadowColor: Colors.primary,
    shadowOffset: {
      width: 0,
      height: 3
    },
    shadowRadius: 5,
    shadowOpacity: 1.0
  },
  signInButtonIcon: {
    color: Colors.white,
    fontSize: 35
  },
  hint: {
    color: Colors.gray,
    fontSize: 14
  },
  buttonParent: {
    flexDirection: 'row',
    marginTop: 50,
    justifyContent: 'space-between'
  },
  resendText: {
    textAlign: 'left',
    color: Colors.deepSkyBlue,
    fontSize: 14,
    marginRight: 25,
    marginBottom: 20,
    marginTop: 25,
    textDecorationLine: 'underline'
  },
};
