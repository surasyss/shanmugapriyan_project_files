import { Dimensions } from 'react-native';
import RNImageToPdf from 'react-native-image-to-pdf';

const converttoPDF = async (pathList) => {
  try {
    const fileName = `${Math.random().toString(36).substring(2, 15) + Math.random().toString(23).substring(2, 5)}.pdf`;
    const heignt = Math.round(Dimensions.get('window').height / Dimensions.get('window').width);
    const options = {
      imagePaths: pathList,
      name: fileName,
      maxSize: { // optional maximum image dimension - larger images will be resized
        width: 900,
        height: heignt * 900,
      },
      quality: 1, // optional compression paramter
    };
    const pdf = await RNImageToPdf.createPDFbyImages(options);
    return pdf.filePath;
  } catch (e) {
    return null;
  }
};

export default converttoPDF;
