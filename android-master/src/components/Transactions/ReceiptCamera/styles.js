import { Dimensions } from 'react-native';
import Colors from '../../../styles/Colors';

export default {
  container: {
    flex: 1,
    flexDirection: 'column',
    backgroundColor: 'black',
  },
  containerCamera: {
    flexDirection: 'column',
    backgroundColor: 'black',
    height: Dimensions.get('window').height - 55
  },
  preview: {
    flex: 1,
    justifyContent: 'flex-end',
    alignItems: 'center',
  },
  captureParent: {
    flex: 0,
    flexDirection: 'row',
    justifyContent: 'center'
  },
  captureButton: {
    flex: 0,
    borderRadius: 5,
    padding: 15,
    position: 'absolute',
    bottom: 50,
    paddingHorizontal: 20,
    alignSelf: 'center',
  },
  closeButton: {
    position: 'absolute',
    right: 5,
    top: 55
  },
  closeIcon: {
    height: 25
  },
  captureIcon: {
    height: 40
  },
  bottomButtons: {
    bottom: 0,
    position: 'absolute',
    flexDirection: 'row',
    backgroundColor: Colors.gray,
  },
  bottomButton: {
    borderTopWidth: 0.3,
    borderColor: Colors.white,
    flex: 0.5,
    padding: 15,
  },
  bottomButtonText: {
    color: Colors.white,
    textAlign: 'center',
    fontSize: 14,
  },
  selectedButton: {
    borderTopWidth: 2,
    borderColor: Colors.white,
  },
  selectedButtonText: {
    color: Colors.white,
    textAlign: 'center',
    fontWeight: 'bold',
  },
  topBar: {
    paddingHorizontal: 10,
    width: '100%',
    position: 'absolute',
    top: 20,
    flex: 1,
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  backButton: {
    resizeMode: 'contain',
    height: 15,
    width: 15,
  },
  uploadButton: {
    color: Colors.white,
    fontSize: 14,
    fontWeight: 'bold',
  },
  unassignedContainer: {
    flex: 1,
    backgroundColor: Colors.white,
    paddingTop: 50,
  }
};
