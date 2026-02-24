import Colors from '../../../styles/Colors';

export default {
  container: {
    backgroundColor: 'white',
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
    backgroundColor: Colors.white
  },
  bottomContainer: {
    marginLeft: 25,
    marginRight: 25,
    marginBottom: 25,
    flexDirection: 'row',
    justifyContent: 'space-between'
  },
  image: {
    height: '100%',
    width: '90%',
    backgroundColor: '#fff',
    marginLeft: '5%',
    marginRight: '5%',
  },
  buttonText: {
    fontSize: 16,
    color: Colors.primary
  },
  buttonTextDanger: {
    fontSize: 16,
    color: Colors.red
  }
};
