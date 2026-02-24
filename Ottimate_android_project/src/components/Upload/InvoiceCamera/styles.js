export default {
  container: {
    flex: 1,
    flexDirection: 'column',
    backgroundColor: 'black',
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
    paddingHorizontal: 20,
    alignSelf: 'center',
    margin: 20,
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
  }
};
