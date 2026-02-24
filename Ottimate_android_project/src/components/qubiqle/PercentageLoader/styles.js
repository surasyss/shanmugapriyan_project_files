import { StyleSheet } from 'react-native';
import Colors from '../../../styles/Colors';

const styles = StyleSheet.create({
  circle: {
    overflow: 'hidden',
    position: 'relative',
    justifyContent: 'center',
    alignItems: 'center'
  },
  leftWrap: {
    overflow: 'hidden',
    position: 'absolute',
    top: 0,
  },
  rightWrap: {
    position: 'absolute',

  },

  loader: {
    position: 'absolute',
    left: 0,
    top: 0,
    borderRadius: 1000,

  },

  innerCircle: {
    overflow: 'hidden',
    position: 'relative',
    justifyContent: 'center',
    alignItems: 'center',
  },
  text: {
    fontSize: 11,
    color: Colors.secondaryText,
  },
});

export default styles;
