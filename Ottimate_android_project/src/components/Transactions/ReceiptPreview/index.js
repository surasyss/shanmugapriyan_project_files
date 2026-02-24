import React, { Component } from 'react';
import {
  Image, Platform, ScrollView, Text, TouchableOpacity, View
} from 'react-native';
import ActionSheet from 'react-native-actionsheet';
import Pdf from 'react-native-pdf';
import WebView from 'react-native-webview';
import styles from './styles';
import Images from '../../../styles/Images';
import Spinner from '../../qubiqle/Spinner';
import Colors from '../../../styles/Colors';

class ReceiptPreview extends Component {
  renderActionSheet() {
    const { discard, upload } = this.props;
    return (
      <View>
        <ActionSheet
          ref={(o) => {
            this.ActionSheet = o;
          }}
          destructiveButtonIndex={1}
          options={['Upload', 'Discard']}
          onPress={(index) => {
            if (index === 0) {
              upload();
              return;
            }
            if (index === 1) {
              discard();
            }
          }}
        />
      </View>
    );
  }

  renderTopbar() {
    return (
      <View style={styles.topBar}>
        <TouchableOpacity
          onPress={() => this.ActionSheet.show()}
        >
          <Image
            style={styles.backButton}
            source={Images.ic_back}
          />
        </TouchableOpacity>

        <Text style={styles.title}>Receipt photo</Text>

        <View />
      </View>
    );
  }

  renderBottomBar() {
    const { discard, upload } = this.props;
    return (
      <View style={styles.bottomContainer}>
        <TouchableOpacity style={styles.uploadButton} onPress={() => upload()}>
          <Text style={styles.uploadButtonText}>Upload</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.discardButton} onPress={() => discard()}>
          <Text style={styles.discardButtonText}>Discard</Text>
        </TouchableOpacity>
      </View>
    );
  }

  renderImage() {
    const { image } = this.props;
    if (image) {
      const extension = image.split('.').reverse()[0].toLowerCase();
      if (extension === 'pdf') {
        return (
          <Pdf
            source={{ uri: image }}
            style={styles.webview}
            onLoadComplete={() => this.setState({ loading: false })}
          />
        );
      }

      if (extension === 'txt' || extension === 'html') {
        return (
          <WebView
            onLoadEnd={() => this.setState({ loading: false })}
            originWhitelist={['*']}
            style={styles.webview}
            source={{ uri: image }}
          />
        );
      }

      return (
        <Image
          source={{ uri: image }}
          style={styles.image}
          resizeMode="contain"
          onLoadStart={() => this.setState({ loading: true })}
          onLoadEnd={() => this.setState({ loading: false })}
        />
      );
    }
    return null;
  }

  renderLoadingDialog() {
    const { isLoading } = this.props;
    return (
      <Spinner
        visible={isLoading}
        color={Platform.OS === 'ios' ? Colors.white : Colors.primary}
      />
    );
  }

  render() {
    return (
      <View style={styles.parent}>
        <ScrollView
          contentContainerStyle={styles.containerStyle}
          style={styles.container}
        >
          <View style={styles.imageContainer}>
            {this.renderImage()}
          </View>
        </ScrollView>
        {this.renderTopbar()}
        {this.renderBottomBar()}
        {this.renderActionSheet()}
        {this.renderLoadingDialog()}
      </View>
    );
  }
}

export default ReceiptPreview;
