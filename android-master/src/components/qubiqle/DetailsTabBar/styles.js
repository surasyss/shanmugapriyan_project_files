import { StyleSheet } from 'react-native';

const styles = StyleSheet.create({
  tab: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    borderTopLeftRadius: 15,
    borderTopRightRadius: 15
  },
  tabs: {
    backgroundColor: 'rgb(236,241,247)',
    height: 45,
    flexDirection: 'row',
    borderTopWidth: 0,
    borderLeftWidth: 0,
    borderRightWidth: 0,
    borderTopLeftRadius: 15,
    borderTopRightRadius: 15
  },
  tabTextSelected: {
    width: '100%',
    textAlign: 'center',
    fontSize: 15,
    fontWeight: 'bold',
    color: 'rgb(0,0,0)',
  },
  tabTextUnSelected: {
    width: '100%',
    textAlign: 'center',
    fontSize: 15,
    fontWeight: '500',
    color: 'rgb(143,142,148)'
  }
});

export default styles;
