import rnblob from 'rn-fetch-blob';

const RNFS = require('react-native-fs');

// eslint-disable-next-line import/prefer-default-export
export const deleteFile = async (filepath) => RNFS.exists(filepath)
// eslint-disable-next-line consistent-return
  .then((result) => {
    if (result) {
      return RNFS.unlink(filepath)
        .then(() => {
        })
        .catch(() => {
        });
    }
  })
  .catch(() => {
  });

export const fileInfo = (url) => {
  const path = url.split('///').pop();
  return rnblob.fs.stat(path);
};
