import { Platform, StyleSheet } from 'react-native';

const border = {
  borderColor: '#b9b9b9',
  borderRadius: 1,
  borderWidth: 1
};

const androidStyles = {
  container: {
    zIndex: 1
  },
  inputContainer: {
  },
  list: {
    ...border,
    backgroundColor: 'white',
    borderTopWidth: 0,
    margin: 10,
    marginTop: 0,
    maxHeight: 150
  }
};

const iosStyles = {
  container: {
    zIndex: 1
  },
  inputContainer: {
  },
  input: {
    backgroundColor: 'white',
    height: 40,
    paddingLeft: 3
  },
  list: {
    ...border,
    backgroundColor: 'white',
    borderTopWidth: 0,
    left: 0,
    position: 'absolute',
    right: 0,
    maxHeight: 150
  }
};

const styles = StyleSheet.create({
  input: {
    backgroundColor: 'white',
    height: 40,
    paddingLeft: 3
  },
  ...Platform.select({
    android: { ...androidStyles },
    ios: { ...iosStyles }
  })
});

export default styles;
