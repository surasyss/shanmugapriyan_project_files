import React, { Component } from 'react';
import { View, TouchableOpacity, Image } from 'react-native';
import { connect } from 'react-redux';
import { RNCamera } from 'react-native-camera';
import { addInvoiceImages, deleteAllInvoiceImage } from '../../../actions';
import store from '../../../store';
import { withNavigationFocus } from 'react-navigation';
import ImagePicker from 'react-native-image-crop-picker';
import Images from '../../../styles/Images';
import styles from './styles';

class InvoiceCamera extends Component {

  constructor(props) {
    super(props);
  }

    takePicture = async () => {
      if (this.camera) {
        const options = { base64: true };
        try {
          const { uri } = await this.camera.takePictureAsync(options);
          ImagePicker.openCropper({
            path: uri,
            freeStyleCropEnabled: true,
          }).then(image => {
            const { restaurant } = this.props.navigation.state.params;
            this.props.addInvoiceImages(image.path)
            this.props.navigation.navigate('InvoicePreview', { restaurant });
          }).catch(e => null);
        } catch (e) {

        }
      }
    };

    closeButtonIcon = () =>{
      this.props.deleteAllInvoiceImage();
      this.props.navigation.goBack()
    }

    render() {
      const { isFocused } = this.props;

      if (isFocused) {
        return (
          <View style={styles.container}>
            <RNCamera
              ref={(ref) => {
                this.camera = ref;
              }}
              onStatusChange={(status) => {
                if (status && status.cameraStatus !== 'READY') {
                  this.props.navigation.goBack();
                }
              }}
              style={styles.preview}
              type={RNCamera.Constants.Type.back}
              flashMode={RNCamera.Constants.FlashMode.auto}
              captureAudio={false}
              androidCameraPermissionOptions={{
                title: 'Permission to use camera',
                message: 'We need your permission to use your camera',
                buttonPositive: 'Ok',
                buttonNegative: 'Cancel',
              }}
            />
            <View style={styles.captureParent}>
              <TouchableOpacity onPress={this.takePicture.bind(this)} style={styles.captureButton} activeOpacity={1}>
                <Image
                  source={Images.camera_button}
                  style={styles.captureIcon}
                  resizeMode="contain"
                />
              </TouchableOpacity>
            </View>

            <TouchableOpacity style={styles.closeButton} onPress={() => this.closeButtonIcon()}>
              <Image
                source={Images.camera_close}
                style={styles.closeIcon}
                resizeMode="contain"
              />
            </TouchableOpacity>
          </View>
        );
      }
      return <View style={styles.container} />;
    }
}

const mapStateToProps = () => ({
});

export default connect(
  mapStateToProps,
  { addInvoiceImages, deleteAllInvoiceImage }
)(withNavigationFocus(InvoiceCamera));

