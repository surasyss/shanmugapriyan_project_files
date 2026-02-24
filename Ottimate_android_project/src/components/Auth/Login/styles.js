import { Dimensions } from 'react-native';
import Colors from '../../../styles/Colors';

const WINDOW_HEIGHT = Dimensions.get('window').height;
const WINDOW_WIDTH = Dimensions.get('window').width;


export default {
  container: {
    position: 'relative',
    height: WINDOW_HEIGHT
  },
  logoParent: {
    width: WINDOW_WIDTH,
    height: WINDOW_HEIGHT / 3,
    backgroundColor: Colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  logo: {
    justifyContent: 'center',
    height: WINDOW_HEIGHT / 5,
    resizeMode: 'contain'
  },
  formParent: {
    marginTop: 40,
    marginLeft: 40,
    marginRight: 40,
    height: WINDOW_HEIGHT - WINDOW_HEIGHT / 2.2,
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
    marginTop: 50,
    alignItems: 'flex-end',
    justifyContent: 'flex-end'
  },
  signInText: {
    color: Colors.primary,
    fontSize: 22,
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
  toggleSigninButton: {
    alignSelf: 'center',
    position: 'absolute',
    top: '90%'
  },
  toggleSigninText: {
    color: Colors.primary,
    fontSize: 18,
    textAlign: 'center'
  }
};
