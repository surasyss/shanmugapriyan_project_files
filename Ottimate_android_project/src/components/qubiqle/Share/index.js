import RNFetchBlob from 'rn-fetch-blob';
import {
  PermissionsAndroid,
  Alert,
  Platform
} from 'react-native';

import converttoPDF from '../../../utils/Converter';

const share = async (data) => {
  try {
    const {
      title, subject, message
    } = data;
    let { files } = data;
    const pathList = [];
    if (!files) files = [];
    const checkVersion = Platform.Version > 22;
    const granted = await PermissionsAndroid.request(
      PermissionsAndroid.PERMISSIONS.WRITE_EXTERNAL_STORAGE
    );

    // cannot progress without permission || sdk < 23 bypass
    if (granted !== PermissionsAndroid.RESULTS.GRANTED && checkVersion) {
      return null;
    }
    let type;
    const Pictures = files.map((item) => RNFetchBlob.config({
      fileCache: true
    })
      .fetch('GET', item)
      .then((resp) => {
        type = resp.respInfo.headers['content-type'] ? resp.respInfo.headers['content-type'] : resp.respInfo.headers['Content-Type'];
        if (!type.includes('image')) {
          const base64s = RNFetchBlob.fs
            .readFile(resp.data, 'base64')
            .then((data) => `data:${type};base64,${data}`);
          return base64s;
        }
        pathList.push(resp.path());
        return null;
      }));

    const completed = await Promise.all(Pictures);
    const pdfCompleted = [];
    if (completed[0] == null) {
      const pdf = await converttoPDF(pathList);
      type = 'application/pdf';
      pdfCompleted.push(await RNFetchBlob.fs
        .readFile(pdf, 'base64')
        .then((data) => `data:${type};base64,${data}`)
        .catch(() => {}));
    }
    const options = {
      title,
      message,
      subject,
      urls: completed[0] ? completed : pdfCompleted,
      failOnCancel: false
    };
    return options;
    // Share.open(options);
  } catch (err) {
    Alert.alert('Error, Permission denied', err);
  }
  return null;
};
export default share;
