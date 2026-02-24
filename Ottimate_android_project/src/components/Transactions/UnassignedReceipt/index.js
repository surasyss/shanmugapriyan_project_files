import React from 'react';
import {
  TouchableOpacity, View, Image, ActivityIndicator, Text
} from 'react-native';
import Pdf from 'react-native-pdf';
import WebView from 'react-native-webview';
import styles from './styles';
import Images from '../../../styles/Images';

export default class UnassignedReceipt extends React.PureComponent {
  constructor() {
    super();
    this.state = {
      loading: true
    };
  }

  renderFile() {
    const { receipt } = this.props;
    const { file_url } = receipt;
    const extension = file_url.split('.').reverse()[0].toLowerCase();
    if (extension === 'pdf') {
      return (
        <Pdf
          source={{ uri: file_url }}
          style={styles.pdf}
          onLoadComplete={() => this.setState({ loading: false })}
        />
      );
    }

    if (extension === 'txt' || extension === 'html') {
      return (
        <WebView
          onLoadEnd={() => this.setState({ loading: false })}
          originWhitelist={['*']}
          style={styles.pdf}
          source={{ uri: file_url }}
        />
      );
    }

    return (
      <Image
        source={{ uri: file_url }}
        style={styles.image}
        resizeMode="contain"
        onLoadStart={() => this.setState({ loading: true })}
        onLoadEnd={() => this.setState({ loading: false })}
      />
    );
  }

  renderGalleryPicker() {
    const { openGallery } = this.props;
    return (
      <TouchableOpacity style={styles.galleryParent} onPress={openGallery}>
        <Image
          source={Images.camera_button}
          style={styles.galleryIcon}
          resizeMode="contain"
        />
        <Text style={styles.galleryText}>Gallery</Text>
      </TouchableOpacity>
    );
  }

  render() {
    const {
      receipt, onPress
    } = this.props;

    if (receipt) {
      const {
        file_url
      } = receipt;
      return (
        <TouchableOpacity
          style={styles.mainView}
          onPress={() => {
            if (onPress) {
              onPress(file_url);
            }
          }}
        >
          <View style={styles.container}>
            <View>
              {this.renderFile(file_url)}
              <ActivityIndicator animating={this.state.loading} style={styles.loader} />
            </View>
          </View>

        </TouchableOpacity>
      );
    }
    return this.renderGalleryPicker();
  }
}
