import Colors from '../../../styles/Colors';

export default {
  mainView: {
    marginLeft: 20,
    marginRight: 20,
    borderBottomWidth: 0.5,
    borderBottomColor: Colors.dividerColor,
    paddingTop: 20,
    paddingBottom: 10,
  },
  container: {
    flexDirection: 'row',
  },
  view: {
    flex: 0.24
  },
  gap: {
    flex: 0.01,
  },
  item: {
    color: Colors.darkGray,
    fontSize: 12,
    fontWeight: '600',
    width: '100%'
  },
  left: {
    textAlign: 'left'
  },
  right: {
    textAlign: 'right',
  },
  heading: {
    color: Colors.fadedBlue,
    fontSize: 11
  }
};
