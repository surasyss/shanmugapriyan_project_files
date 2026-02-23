import React, { Component } from 'react';
import {
  TouchableOpacity, View, TextInput, Text, Image
} from 'react-native';
import Icon from 'react-native-vector-icons/dist/FontAwesome';
import { KeyboardAwareScrollView } from 'react-native-keyboard-aware-scroll-view';
import Pushy from 'pushy-react-native';
import { IS_PROD } from 'react-native-dotenv';
import styles from './styles';
import Images from '../../../styles/Images';
import ParentView from '../../qubiqle/ParentView';
import Adapter from '../../../utils/Adapter';
import Constants from '../../../utils/Constants';
import { strToBool } from '../../../utils/StringFormatter';

export default class Login extends Component {
  constructor(props) {
    super(props);
    this.state = {
      username: '',
      password: '',
    };
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

  setText(key, value) {
    this.setState({
      [key]: value
    });
  }

  renderHeader() {
    return (
      <View style={styles.logoParent}>
        <Image style={styles.logo} source={Images.loginScreenLogo} />
      </View>
    );
  }

  renderForm() {
    const { username, password } = this.state;
    const { login, isSSOLogin, toggleLogin } = this.props;

    return (
      <View style={styles.formParent}>
        <View
          style={styles.inputParent}
        >
          <TextInput
            placeholder={isSSOLogin ? 'Email' : 'User Name'}
            autoCapitalize="none"
            style={styles.input}
            value={username}
            onChangeText={(text) => this.setText('username', text.trim())}
          />
        </View>

        {!isSSOLogin
        && (
          <View
            style={styles.inputParent}
          >
            <TextInput
              secureTextEntry
              placeholder="Password"
              autoCapitalize="none"
              style={styles.input}
              value={password}
              onChangeText={(text) => this.setText('password', text)}
            />
          </View>
        )}

        <View style={styles.signInParent}>
          <Text style={styles.signInText}>{isSSOLogin ? 'Sign in with SSO' : 'Sign In'}</Text>
          <TouchableOpacity style={styles.signInButton} elevation={5} onPress={() => login(username, password)}>
            <Icon
              name="long-arrow-right"
              style={styles.signInButtonIcon}
            />
          </TouchableOpacity>
        </View>
        <TouchableOpacity style={styles.toggleSigninButton} onPress={() => toggleLogin()}>
          <Text style={styles.toggleSigninText}>{isSSOLogin ? 'Back to standard sign in' : 'Sign in with SSO'}</Text>
        </TouchableOpacity>
      </View>
    );
  }

  render() {
    const { hoverLoading } = this.props;
    return (
      <ParentView style={styles.container} hoverLoading={hoverLoading}>
        <KeyboardAwareScrollView>
          {this.renderHeader()}
          {this.renderForm()}
        </KeyboardAwareScrollView>
      </ParentView>
    );
  }
}
