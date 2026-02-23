import React, { Component } from 'react';
import { ActivityIndicator, View } from 'react-native';
import WebView from 'react-native-webview';
import styles from './styles';
import { getQueryParams } from '../../../utils/StringFormatter';

export default class SSOLogin extends Component {
  constructor(props) {
    super(props);
    this.state = {
      loading: true,
    };
  }

  onShouldStartLoadWithRequest(navState) {
    const params = getQueryParams(navState.url);
    if (params && params.access_token) {
      this.props.loginWithToken(params.access_token);
      return false;
    }
    return true;
  }

  hideSpinner() {
    this.setState({ loading: false });
  }

  renderLoader() {
    const { loading } = this.state;
    if (loading) {
      return (
        <ActivityIndicator
          size="large"
          style={styles.loading}
        />
      );
    }
    return null;
  }


  render() {
    const { data } = this.props;

    return (
      <View style={{ flex: 1 }}>
        <WebView
          ref={(ref) => {
            this.webView = ref;
          }}
          onLoad={() => this.hideSpinner()}
          style={{ flex: 1 }}
          onShouldStartLoadWithRequest={this.onShouldStartLoadWithRequest.bind(this)}
          source={{ uri: data.sso_url }}
          cacheEnabled={false}
          incognito
        />
        {this.renderLoader()}
      </View>
    );
  }
}
