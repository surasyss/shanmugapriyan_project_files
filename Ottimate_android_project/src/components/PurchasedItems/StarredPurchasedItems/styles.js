import { Dimensions } from 'react-native';
import Colors from '../../../styles/Colors';

export default {
  itemsList: {
    marginBottom: 125
  },
  blankContainer: {
    marginTop: 125,
    justifyContent: 'center',
    alignItems: 'center',
    flex: 1
  },
  blankImage: {
    width: (Dimensions.get('window').width) / 4,
    height: Dimensions.get('window').height / 4
  },
  blankText: {
    width: '100%',
    textAlign: 'center',
    color: Colors.secondaryText,
    fontSize: 16,
    fontWeight: 'bold',
    marginTop: -25
  },
};
