import React, { Component } from 'react';
import {
  TouchableOpacity, View, TextInput, Text, Image
} from 'react-native';
import Icon from 'react-native-vector-icons/dist/FontAwesome';
import { KeyboardAwareScrollView } from 'react-native-keyboard-aware-scroll-view';
import styles from './styles';
import Images from '../../../styles/Images';
import ParentView from '../../qubiqle/ParentView';

export default class OAuthMfa extends Component {
  constructor(props) {
    super(props);
    this.state = {
      code: ''
    };
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
    const { code } = this.state;
    const { login } = this.props;

    return (
      <View style={styles.formParent}>

        <Text style={styles.hint}>We have sent the 6 digit code to your number. Enter the code to the below field.</Text>
        <View
          style={styles.inputParent}
        >
          <TextInput
            placeholder="Confirmation Code"
            style={styles.input}
            value={code}
            onChangeText={(text) => this.setText('code', text)}
          />
        </View>

        <View style={styles.buttonParent}>
          <View />

          <View style={styles.signInParent}>
            <TouchableOpacity style={styles.signInButton} elevation={5} onPress={() => login(code)}>
              <Icon
                name="long-arrow-right"
                style={styles.signInButtonIcon}
              />
            </TouchableOpacity>
          </View>
        </View>
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
