import React, { Component } from 'react';
import {
  View, TouchableOpacity, Image, Text
} from 'react-native';
import { FlatGrid } from 'react-native-super-grid';
import { RNCamera } from 'react-native-camera';
import { withNavigationFocus } from 'react-navigation';
import Images from '../../../styles/Images';
import styles from './styles';
import UnassignedReceipt from '../UnassignedReceipt';

class ReceiptCamera extends Component {
  renderCamera() {
    const { goBack, takePicture } = this.props;
    return (
      <View style={styles.containerCamera}>
        <RNCamera
          ref={(ref) => {
            this.camera = ref;
          }}
          onStatusChange={(status) => {
            if (status && status.cameraStatus !== 'READY') {
              goBack();
            }
          }}
          style={styles.preview}
          type={RNCamera.Constants.Type.back}
          flashMode={RNCamera.Constants.FlashMode.auto}
          androidCameraPermissionOptions={{
            title: 'Permission to use camera',
            message: 'We need your permission to use your camera',
            buttonPositive: 'Ok',
            buttonNegative: 'Cancel',
          }}
        />
        <View style={styles.captureParent}>
          <TouchableOpacity onPress={() => takePicture(this.camera)} style={styles.captureButton} activeOpacity={1}>
            <Image
              source={Images.camera_button}
              style={styles.captureIcon}
              resizeMode="contain"
            />
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  renderUnassigned() {
    const { receipts } = this.props;
    if (receipts) {
      return (
        <View style={styles.unassignedContainer}>
          <FlatGrid
            data={[null, ...receipts]}
            renderItem={({ item }) => this.renderUnassignedReceipt(item)}
          />
        </View>
      );
    }
    return null;
  }

  renderUnassignedReceipt(receipt) {
    const { openGallery, openUnassigned } = this.props;
    return (
      <UnassignedReceipt
        onPress={openUnassigned}
        openGallery={openGallery}
        receipt={receipt}
      />
    );
  }

  renderScene() {
    const { index } = this.props;
    if (index === 0) {
      return this.renderCamera();
    }
    return this.renderUnassigned();
  }

  renderTopbar() {
    const { goBack, index } = this.props;
    return (
      <View style={styles.topBar}>
        <TouchableOpacity onPress={goBack}>
          <Image
            style={[styles.backButton, { tintColor: index === 0 ? 'white' : 'black' }]}
            source={Images.ic_back}
          />
        </TouchableOpacity>
        {this.renderTopbarUploadButton()}
      </View>
    );
  }

  renderTopbarUploadButton() {
    const { index, openGallery } = this.props;
    if (index === 0) {
      return (
        <TouchableOpacity onPress={openGallery}>
          <Text style={styles.uploadButton}>
            Upload
          </Text>
        </TouchableOpacity>
      );
    }
    return null;
  }

  render() {
    const { index, selectScene } = this.props;
    return (
      <View style={styles.container}>
        {this.renderScene()}
        {this.renderTopbar()}
        <View style={styles.bottomButtons}>
          <TouchableOpacity
            style={[styles.bottomButton, index === 0 ? styles.selectedButton : {}]}
            onPress={() => selectScene(0)}
          >
            <Text style={[styles.bottomButtonText, index === 0 ? styles.selectedButtonText : {}]}>Take photo</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.bottomButton, index === 1 ? styles.selectedButton : {}]}
            onPress={() => selectScene(1)}
          >
            <Text style={[styles.bottomButtonText, index === 1 ? styles.selectedButtonText : {}]}>Unassigned</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  }
}

export default withNavigationFocus(ReceiptCamera);
