import { Dimensions } from 'react-native';
import Colors from '../../../styles/Colors';

export default {
  container: {
    flex: 1
  },
  blankContainer: {
    justifyContent: 'center',
    alignItems: 'center',
    flex: 1
  },
  blankImage: {
    width: (Dimensions.get('window').width * 2) / 3,
    height: Dimensions.get('window').height / 2
  },
  blankText: {
    width: '100%',
    textAlign: 'center',
    color: Colors.secondaryText,
    fontSize: 16,
    fontWeight: 'bold',
    marginTop: -25
  },
  blankButton: {
    marginTop: 25,
    width: Dimensions.get('window').width - 50,
  },
  blankReceiptButton: {
    marginTop: 10,
    width: Dimensions.get('window').width - 50,
  },

  pendingUploads: {
    marginBottom: 90
  },
  bottomView: {
    width: '100%',
    marginBottom: 5,
    justifyContent: 'center',
    alignItems: 'center',
    position: 'absolute', // Here is the trick
    bottom: 0, // Here is the trick
  },
};
