import { Dimensions } from 'react-native';
import Colors from '../../../styles/Colors';

export default {
  container: {
    paddingTop: 15
  },
  textParent: {
    marginTop: Dimensions.get('window').height / 10,
    justifyContent: 'center',
    alignItems: 'center'
  },
  text: {
    color: Colors.secondaryText,
    fontSize: 20,
    fontWeight: 'bold',
    width: '100%',
    textAlign: 'center'
  }
};
