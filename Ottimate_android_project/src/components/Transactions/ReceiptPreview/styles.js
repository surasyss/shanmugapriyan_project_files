import { Dimensions } from 'react-native';
import Colors from '../../../styles/Colors';

export default {
  parent: {
    flex: 1,
    backgroundColor: Colors.black,
  },
  container: {
    flex: 1,
    paddingBottom: 20
  },
  containerStyle: {
    flexGrow: 1,
    justifyContent: 'space-between',
    flexDirection: 'column'
  },
  imageContainer: {
    flex: 1,
    justifyContent: 'flex-start',
  },
  image: {
    height: '100%',
    width: '90%',
    marginLeft: '5%',
    marginRight: '5%',
  },
  webview: {
    marginTop: 125,
  },
  bottomContainer: {
    bottom: 15,
    marginBottom: 25,
    flexDirection: 'row',
    justifyContent: 'space-between'
  },
  uploadButton: {
    width: Dimensions.get('window').width / 2,
    justifyContent: 'center',
    marginRight: 10,
    backgroundColor: Colors.primary,
  },
  discardButton: {
    width: Dimensions.get('window').width / 2,
    justifyContent: 'center',
    backgroundColor: Colors.white,
  },
  uploadButtonText: {
    padding: 20,
    fontSize: 16,
    color: Colors.white,
    textAlign: 'center',
  },
  discardButtonText: {
    padding: 20,
    fontSize: 16,
    color: Colors.primary,
    textAlign: 'center',
  },
  topBar: {
    flex: 1,
    justifyContent: 'space-between',
    flexDirection: 'row',
    paddingHorizontal: 10,
    width: '100%',
    position: 'absolute',
    top: 75,
  },
  backButton: {
    resizeMode: 'contain',
    height: 15,
    width: 15,
  },
  title: {
    fontWeight: 'bold',
    fontSize: 16,
    color: Colors.white,
  },
};
