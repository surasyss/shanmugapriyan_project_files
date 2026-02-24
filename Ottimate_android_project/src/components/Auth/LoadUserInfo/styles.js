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
  loadingText: {
    marginTop: 0,
    color: Colors.description,
    fontSize: 14
  }
};
