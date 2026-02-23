import React, { Component } from 'react';
import { ActivityIndicator, View } from 'react-native';
import { WebView } from 'react-native-webview';
import {
  IS_PROD, OAUTH_CLIENT_ID, OAUTH_REDIRECT_URI, PIQ_AUTH_SERVER_URL
} from 'react-native-dotenv';
import Pushy from 'pushy-react-native';
import styles from './styles';
import { encodeUrl, getQueryParams, strToBool } from '../../../utils/StringFormatter';
import Urls from '../../../api/urls';
import Adapter from '../../../utils/Adapter';
import Constants from '../../../utils/Constants';

class OAuthLogin extends Component {
  constructor(props) {
    super(props);
    const query_params = {
      response_type: 'code',
      client_id: OAUTH_CLIENT_ID,
      redirect_uri: OAUTH_REDIRECT_URI
    };
    const url = PIQ_AUTH_SERVER_URL + Urls.OAUTH_LOGIN;
    this.state = { loading: true, url: encodeUrl(url, query_params) };
  }

  componentDidMount() {
    if (strToBool(IS_PROD)) {
      Pushy.listen();

      Pushy.register().then(async (deviceToken) => {
        await Adapter.set(Constants.PUSHY_TOKEN, deviceToken);
      }).catch(() => {
      });

      Pushy.setNotificationListener(async (data) => {
        const notificationTitle = data.title ? data.title : 'Plate IQ';
        const notificationText = data.message;
        Pushy.notify(notificationTitle, notificationText, data);
      });

      // Pushy.setNotificationClickListener(async (data) => {
      //   // Display basic alert
      //   alert(`Clicked notification: ${data.message}`);
      // });
    }
  }

  onShouldStartLoadWithRequest(navState) {
    const { loginWithOAuthCode } = this.props;
    const params = getQueryParams(navState.url);
    if (params && params.code) {
      loginWithOAuthCode(params.code, null);
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
    const { url } = this.state;

    return (
      <View style={{ flex: 1 }}>
        <WebView
          ref={(ref) => {
            this.webView = ref;
          }}
          onLoad={() => this.hideSpinner()}
          style={{ flex: 1 }}
          onShouldStartLoadWithRequest={this.onShouldStartLoadWithRequest.bind(this)}
          source={{ uri: url }}
          cacheEnabled={false}
          incognito
        />
        {this.renderLoader()}
      </View>
    );
  }
}

export default OAuthLogin;
