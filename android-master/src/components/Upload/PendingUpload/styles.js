import Colors from '../../../styles/Colors';

export default {
  container: {
    backgroundColor: Colors.white,
    borderBottomWidth: 0.8,
    borderBottomColor: Colors.dividerColor,
    paddingTop: 15,
    paddingBottom: 15,
    paddingLeft: 20,
    paddingRight: 20,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between'
  },
  leftView: {
    flexDirection: 'row',
  },
  image: {
    width: 50,
    height: 50,
    borderRadius: 25,
    marginRight: 15,
    overflow: 'hidden',
  },
  primaryText: {
    color: Colors.black,
    fontSize: 16,
    marginBottom: 10
  },
  secondaryText: {
    color: Colors.secondaryText,
    fontSize: 15,
  },
  done: {
    fontSize: 35,
    color: Colors.success
  }
};
